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
        for payload in [item(b'not an image','x.png','image/png'),item(b'a'*(4*1024*1024+1)),{'name':'bad','mime':'text/plain','data':'%%%'}]:
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
