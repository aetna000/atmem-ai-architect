import base64
import hashlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from server.attachments import extract, prepare
from server.engineering_sessions import ProjectScope, SessionError
from server.source_evidence import SourceEvidence

MIME='application/vnd.openxmlformats-officedocument.wordprocessingml.document'


def document():
    image=io.BytesIO();Image.new('RGB',(80,40),'white').save(image,format='PNG')
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as doc:
        doc.writestr('word/document.xml','''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
            <w:body><w:p><w:r><w:t>Reservations</w:t><a:blip r:embed="image"/></w:r></w:p>
            <w:p><w:r><a:blip r:link="outside"/></w:r></w:p></w:body></w:document>''')
        doc.writestr('word/_rels/document.xml.rels','''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
            <Relationship Id="image" Target="media/diagram.png"/>
            <Relationship Id="outside" Target="https://127.0.0.1/private" TargetMode="External"/></Relationships>''')
        doc.writestr('word/media/diagram.png',image.getvalue())
        doc.writestr('word/media/unsupported.emf',b'Not a raster image')
    return {'name':'scope.docx','mime':MIME,'data':base64.b64encode(out.getvalue()).decode()},out.getvalue()


class SourceFigureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'sources.sqlite'
        self.store=SourceEvidence(self.path);self.scope=ProjectScope('tenant-one','project-one')
        self.item,self.raw=document();self.sha=hashlib.sha256(self.raw).hexdigest()
        self.parsed,=prepare([self.item],design=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_figures_are_decoded_and_bound_to_relationships_without_remote_fetches(self):
        figures=self.parsed['_figures'];self.assertEqual(len(figures),2)
        self.assertEqual(figures[0]['locations'],['paragraph:1'])
        self.assertEqual(figures[0]['status'],'available');self.assertEqual(figures[0]['mime'],'image/png')
        self.assertEqual(figures[1]['status'],'unavailable')
        self.assertIn('figure-1',self.parsed['text'])
        self.assertNotIn('https://127.0.0.1',self.parsed['text'])
        self.assertEqual(hashlib.sha256(base64.b64decode(figures[0]['data'])).hexdigest(),figures[0]['sha256'])

    def test_image_only_specification_preserves_pixels_without_claiming_ocr(self):
        image=io.BytesIO();Image.new('RGB',(80,40),'white').save(image,format='JPEG')
        raw=image.getvalue();entry={'name':'clinic.jpg','mime':'image/jpeg','data':base64.b64encode(raw).decode()}
        parsed,=prepare([entry],design=True)
        self.assertIn('no OCR',parsed['text']);self.assertNotIn('data',parsed)
        figure,=parsed['_figures'];self.assertEqual(figure['status'],'available')
        self.assertEqual(figure['originalSha256'],hashlib.sha256(raw).hexdigest())
        self.assertNotEqual(figure['originalSha256'],figure['sha256'])
        with Image.open(io.BytesIO(base64.b64decode(figure['data']))) as rendered:
            self.assertEqual(rendered.size,(80,40));self.assertEqual(rendered.getpixel((0,0)),(255,255,255))

    def test_retention_replay_restart_isolation_and_integrity(self):
        receipt=self.store.retain(self.scope,self.sha,self.parsed['_figures'])
        self.assertNotIn('data',receipt['figures'][0])
        self.assertEqual(self.store.retain(self.scope,self.sha,self.parsed['_figures']),receipt)
        restarted=SourceEvidence(self.path)
        image=restarted.image(self.scope,self.sha,'figure-1',receipt['manifestSha256'])
        self.assertEqual(hashlib.sha256(image.content).hexdigest(),receipt['figures'][0]['sha256'])
        for scope in [ProjectScope('other-tenant','project-one'),ProjectScope('tenant-one','other-project')]:
            with self.assertRaises(SessionError):restarted.catalog(scope,self.sha)
        for ident in ['figure-2','figure-99','../../private']:
            with self.assertRaises(SessionError):restarted.image(self.scope,self.sha,ident,receipt['manifestSha256'])
        with self.assertRaises(SessionError):restarted.image(self.scope,self.sha,'figure-1','0'*64)
        with restarted._db() as db:db.execute('UPDATE source_figures SET content=?',(b'corrupted',))
        with self.assertRaisesRegex(SessionError,'integrity'):restarted.image(self.scope,self.sha,'figure-1',receipt['manifestSha256'])

    def test_quota_failure_retains_existing_evidence_and_manifest_conflicts_fail(self):
        receipt=self.store.retain(self.scope,self.sha,self.parsed['_figures'])
        with patch('server.source_evidence.MAX_SOURCES',1):
            with self.assertRaisesRegex(ValueError,'storage limit'):self.store.retain(self.scope,'1'*64,self.parsed['_figures'])
        changed=[dict(row) for row in self.parsed['_figures']];changed[0]['name']='different'
        with self.assertRaisesRegex(SessionError,'different figure'):self.store.retain(self.scope,self.sha,changed)
        self.assertEqual(self.store.catalog(self.scope,self.sha),receipt)

    def test_scoped_intake_returns_only_receipts_and_legacy_intake_does_not_claim_retention(self):
        from fastapi.testclient import TestClient
        from server.app import app,TOKEN
        client=TestClient(app);headers={'Authorization':'Bearer '+TOKEN}
        with patch('server.app.product_home',return_value=Path(self.temp.name)),patch('server.engineering_routes.local_scope',return_value=(self.scope,Path(self.temp.name)/'saved.json')) as scope:
            result=client.post('/api/design-sources',json={'projectId':'project-one','attachments':[self.item]},headers=headers)
            self.assertEqual(result.status_code,200,result.text)
            scope.assert_called_once_with('project-one')
            source,=result.json()['sources'];self.assertEqual(source['sha256'],self.sha)
            self.assertNotIn('_figures',source);self.assertNotIn('data',source['figureEvidence']['figures'][0])
            retained=SourceEvidence(Path(self.temp.name)/'source-evidence'/'figures.sqlite')
            self.assertEqual(retained.catalog(self.scope,self.sha),source['figureEvidence'])
        legacy=client.post('/api/design-sources',json={'attachments':[self.item]},headers=headers).json()['sources'][0]
        self.assertEqual(legacy['figureEvidence']['status'],'not_retained_without_project')
        self.assertNotIn('manifestSha256',legacy['figureEvidence'])
        self.assertNotIn('data',legacy['figureEvidence']['figures'][0])


    def test_authenticated_figure_download_pins_project_manifest_and_bytes(self):
        from fastapi.testclient import TestClient
        from server.app import app, TOKEN
        store=SourceEvidence(Path(self.temp.name)/'source-evidence'/'figures.sqlite')
        receipt=store.retain(self.scope,self.sha,self.parsed['_figures'])
        payload={'projectId':'project-one','sourceSha256':self.sha,'manifestSha256':receipt['manifestSha256'],'figureId':'figure-1'}
        client=TestClient(app);headers={'Authorization':'Bearer '+TOKEN}
        self.assertEqual(client.post('/api/design-sources/figure',json=payload).status_code,401)
        with patch('server.app.product_home',return_value=Path(self.temp.name)),patch('server.engineering_routes.local_scope',return_value=(self.scope,Path(self.temp.name)/'saved.json')) as scope:
            response=client.post('/api/design-sources/figure',json=payload,headers=headers)
            self.assertEqual(response.status_code,200,response.text)
            scope.assert_called_once_with('project-one')
            self.assertEqual(response.headers['content-type'],'image/png')
            self.assertEqual(response.headers['cache-control'],'no-store')
            self.assertEqual(response.headers['x-source-sha256'],self.sha)
            self.assertEqual(response.headers['x-manifest-sha256'],receipt['manifestSha256'])
            self.assertEqual(hashlib.sha256(response.content).hexdigest(),response.headers['x-figure-sha256'])
            self.assertEqual(response.content,base64.b64decode(self.parsed['_figures'][0]['data']))
            for change in [{'manifestSha256':'0'*64},{'sourceSha256':'0'*64},{'figureId':'figure-2'}]:
                self.assertEqual(client.post('/api/design-sources/figure',json={**payload,**change},headers=headers).status_code,409)
            for change in [{'figureId':'../../private'},{'path':'/tmp/private'}]:
                self.assertEqual(client.post('/api/design-sources/figure',json={**payload,**change},headers=headers).status_code,422)
        with patch('server.app.product_home',return_value=Path(self.temp.name)),patch('server.engineering_routes.local_scope',return_value=(ProjectScope('other','project-one'),Path(self.temp.name)/'saved.json')):
            self.assertEqual(client.post('/api/design-sources/figure',json=payload,headers=headers).status_code,409)
