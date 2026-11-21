import asyncio,base64,io,json,unittest,zipfile
from unittest.mock import AsyncMock,patch
from PIL import Image
from pydantic import ValidationError
from server.attachments import extract,prepare
from server.contracts import ChatRequest,Attachment
from server.architect import AtMemArchitect
from server.local_providers import call_cli

def item(data,name='notes.txt',mime='text/plain'):
    return {'name':name,'mime':mime,'data':base64.b64encode(data).decode()}
def png():
    out=io.BytesIO();Image.new('RGB',(20,20),'pink').save(out,format='PNG');return out.getvalue()
def request(attachments,provider='codex'):
    return ChatRequest(message='Inspect the evidence',provider=provider,model='default',project={'revision':1,'name':'Attachment test','nodes':[],'edges':[]},attachments=attachments)

class AttachmentTests(unittest.TestCase):
    def test_text_docx_and_image_are_real_content(self):
        archive=io.BytesIO()
        with zipfile.ZipFile(archive,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>Inventory remains in Australia.</w:t></w:r></w:p></w:document>')
        result=prepare([item(b'Budget AUD 200 monthly'),item(archive.getvalue(),'scope.docx','application/vnd.openxmlformats-officedocument.wordprocessingml.document'),item(png(),'diagram.png','image/png')])
        self.assertIn('AUD 200',result[0]['text']);self.assertIn('Inventory remains',result[1]['text']);self.assertEqual(base64.b64decode(result[2]['data']),png())
    def test_corrupt_spoofed_oversized_and_path_inputs_rejected(self):
        for payload in [item(b'not an image','x.png','image/png'),item(b'a'*(8*1024*1024+1)),{'name':'bad','mime':'text/plain','data':'%%%'}]:
            with self.assertRaises((ValueError,Exception)):extract([payload])
        with self.assertRaises(ValidationError):Attachment(**item(b'hi','../../secret'))
        with self.assertRaises(ValueError):extract([item(b'hi')]*5)
    def test_scanned_pdf_does_not_claim_text(self):
        from pypdf import PdfWriter
        out=io.BytesIO();writer=PdfWriter();writer.add_blank_page(width=100,height=100);writer.write(out)
        with self.assertRaisesRegex(RuntimeError,'no readable text'):prepare([item(out.getvalue(),'scan.pdf','application/pdf')])
    def test_context_has_extracted_evidence_without_base64(self):
        async def run():
            with patch('server.local_providers.call_cli',new_callable=AsyncMock,return_value={'message':'Reviewed'}) as native:
                await AtMemArchitect().call(request([item(b'Bounded scope')]),lambda:False)
                args=native.call_args.args
                self.assertIn('Bounded scope',args[2]);self.assertNotIn(base64.b64encode(b'Bounded scope').decode(),args[2]);self.assertEqual(args[-1],[])
        asyncio.run(run())
    def test_cli_images_use_native_blocks_and_ephemeral_files(self):
        async def run():
            async def claude_capture(args,body,cwd,*rest,timeout=150):
                self.assertEqual(timeout,150)
                self.assertIn('--input-format',args);content=json.loads(body)['message']['content'];self.assertEqual(content[1]['type'],'image');return json.dumps({'structured_output':{'message':'Saw image'}})
            async def codex_capture(args,body,cwd,*rest,timeout=150):
                self.assertEqual(timeout,150)
                from pathlib import Path
                path=Path(args[args.index('--image')+1]);self.assertEqual(path.read_bytes(),png());self.assertEqual(path.stat().st_mode&0o777,0o600);self.image_path=path;return '{"message":"Saw image"}'
            for provider,handler in [('claude-code',claude_capture),('codex',codex_capture)]:
                with patch('server.local_providers.shutil.which',return_value='/mock/cli'),patch('server.local_providers.communicate',side_effect=handler):
                    await call_cli(provider,'default','inspect','system',{'type':'object'},lambda:False,images=[item(png(),'diagram.png','image/png')])
            self.assertFalse(self.image_path.exists())
        asyncio.run(run())
    def test_unsupported_connector_explains_without_sending(self):
        with self.assertRaisesRegex(RuntimeError,'cannot send images'):
            asyncio.run(AtMemArchitect().call(request([item(png(),'diagram.png','image/png')],'gemini-cli'),lambda:False))

class DiagramInputTests(unittest.TestCase):
    def test_plain_and_compressed_diagrams_keep_nodes_edges_and_page(self):
        import base64,zlib
        from urllib.parse import quote
        from server.attachments import diagram_text
        model='<mxGraphModel><root><mxCell id="a" value="API"/><mxCell id="b" value="Database"/><mxCell id="e" source="a" target="b" value="Writes"/></root></mxGraphModel>'
        for text in [model,'<mxfile><diagram name="System">'+model+'</diagram></mxfile>']:
            result=diagram_text(text.encode());self.assertIn('source="a"',result);self.assertIn('Database',result)
        compressor=zlib.compressobj(wbits=-15);encoded=base64.b64encode(compressor.compress(quote(model,safe='').encode())+compressor.flush()).decode()
        self.assertIn('Writes',diagram_text(('<mxfile><diagram name="System">'+encoded+'</diagram></mxfile>').encode()))
    def test_external_entities_and_expansion_are_rejected(self):
        import base64,zlib
        from server.attachments import diagram_text
        with self.assertRaises(ValueError):diagram_text(b'<!DOCTYPE x [<!ENTITY x SYSTEM "file:///etc/passwd">]><mxGraphModel/>')
        with self.assertRaises(ValueError):diagram_text(b'<html/>')
        compressor=zlib.compressobj(wbits=-15);encoded=base64.b64encode(compressor.compress(b'x'*200000)+compressor.flush()).decode()
        with self.assertRaises(ValueError):diagram_text(('<mxfile><diagram>'+encoded+'</diagram></mxfile>').encode())


class DesignSourceTests(unittest.TestCase):
    def test_design_source_receipt_uses_original_bytes_and_keeps_readable_text(self):
        import base64
        import hashlib
        from fastapi.testclient import TestClient
        from server.app import app, TOKEN
        raw = b'Section 1\nAllocate a single seat hold.'
        client = TestClient(app)
        result = client.post('/api/design-sources', json={'attachments': [{
            'name': 'brief.txt', 'mime': 'text/plain', 'data': base64.b64encode(raw).decode(),
        }]}, headers={'Authorization': f'Bearer {TOKEN}'})
        self.assertEqual(result.status_code, 200)
        row, = result.json()['sources']
        self.assertEqual(row['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(row['text'], raw.decode())
        self.assertNotIn('data', row)

    def test_large_word_source_preserves_sections_and_table_cells(self):
        import base64
        import io
        from zipfile import ZipFile
        from fastapi.testclient import TestClient
        from server.app import app, TOKEN
        archive = io.BytesIO()
        with ZipFile(archive, 'w') as doc:
            doc.writestr('word/document.xml', '''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:body><w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Rules</w:t></w:r></w:p>
              <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Input</w:t></w:r></w:p></w:tc>
              <w:tc><w:p><w:r><w:t>Outcome</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>''')
            doc.writestr('word/media/image1.png', b'x' * (5 * 1024 * 1024))
        result = TestClient(app).post('/api/design-sources', json={'attachments': [{
            'name': 'large.docx', 'mime': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'data': base64.b64encode(archive.getvalue()).decode(),
        }]}, headers={'Authorization': f'Bearer {TOKEN}'})
        self.assertEqual(result.status_code, 200)
        row, = result.json()['sources']
        self.assertIn('[Heading1] Rules', row['text'])
        self.assertIn('Input | Outcome', row['text'])
        self.assertEqual(row['graphics'], ['image1.png'])
        chat = request([item(archive.getvalue(), 'large.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')])
        parsed, = prepare([entry.model_dump() for entry in chat.attachments])
        self.assertIn('Input', parsed['text'])
        self.assertIn('Outcome', parsed['text'])
