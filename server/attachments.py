"""Bounded, ephemeral attachment parsing. Content is evidence, never instructions."""
import base64,io,json,subprocess,sys,zipfile,zlib
from urllib.parse import unquote_to_bytes
from pathlib import Path
from xml.etree import ElementTree
MAX_FILE=4*1024*1024
MAX_TOTAL=8*1024*1024

def decode(item):
    try:data=base64.b64decode(item['data'],validate=True)
    except Exception:raise ValueError('Attachment encoding is invalid.')
    if not data or len(data)>MAX_FILE:raise ValueError('Each attachment must be between 1 byte and 4 MB.')
    return data

def diagram_text(data):
    """Decode draw.io XML locally; never fetch external resources or execute markup."""
    def parse(raw):
        if len(raw)>100000:raise ValueError('Diagram text exceeds 100,000 bytes. Use a smaller diagram.')
        if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():raise ValueError('Unsupported diagram XML declarations.')
        try:return ElementTree.fromstring(raw)
        except ElementTree.ParseError:raise ValueError('Cannot read diagram XML. Export a standard draw.io file or image.')
    root=parse(data)
    if root.tag=='mxGraphModel':return ElementTree.tostring(root,encoding='unicode')
    if root.tag!='mxfile':raise ValueError('Use a draw.io mxfile or mxGraphModel diagram.')
    pages=root.findall('diagram')
    if not pages or len(pages)>20:raise ValueError('Use a diagram with between 1 and 20 pages.')
    result=[]
    for page in pages:
        model=page.find('mxGraphModel')
        if model is None:
            try:
                encoded=base64.b64decode((page.text or '').strip(),validate=True)
                decoder=zlib.decompressobj(-15)
                raw=decoder.decompress(encoded,100001)
                if len(raw)>100000 or not decoder.eof or decoder.unused_data:raise ValueError('Diagram expansion exceeds the limit or is invalid.')
                model=parse(unquote_to_bytes(raw.decode('utf-8')))
            except (UnicodeError,zlib.error,ValueError) as exc:raise ValueError('Cannot decode this draw.io page within the supported text limit.') from exc
        if model.tag!='mxGraphModel':raise ValueError('A draw.io page must contain an mxGraphModel.')
        result.append('[Diagram: '+page.get('name','Untitled')+']\n'+ElementTree.tostring(model,encoding='unicode'))
    text='\n\n'.join(result)
    if len(text)>100000:raise ValueError('Combined diagram text exceeds 100,000 characters.')
    return text

def extract(items):
    if len(items)>4:raise ValueError('Attach up to four files per message.')
    decoded=[(item,decode(item)) for item in items]
    if sum(len(data) for _,data in decoded)>MAX_TOTAL:raise ValueError('Attachments exceed the 8 MB total limit.')
    result=[]
    for item,data in decoded:
        mime=item['mime'];name=item['name']
        if mime.startswith('image/'):
            from PIL import Image
            Image.MAX_IMAGE_PIXELS=20_000_000
            with Image.open(io.BytesIO(data)) as im:
                if im.width*im.height>20_000_000:raise ValueError('Image exceeds 20 megapixels.')
                if im.format not in {'PNG','JPEG','WEBP'} or Image.MIME[im.format]!=mime:raise ValueError('Image format does not match its content.')
                im.verify()
            result.append({'name':name,'mime':mime,'data':item['data']});continue
        if mime=='application/pdf':
            from pypdf import PdfReader,overwrite_configuration
            overwrite_configuration(maximum_declared_stream_length=8_000_000,zlib_maximum_output_length=8_000_000,lzw_maximum_output_length=8_000_000,run_length_maximum_output_length=8_000_000)
            reader=PdfReader(io.BytesIO(data))
            if reader.is_encrypted:raise ValueError('Unlock the PDF before attaching it.')
            if len(reader.pages)>50:raise ValueError('Use a PDF with at most 50 pages.')
            pages=[page.extract_text() or '' for page in reader.pages]
            text='\n\n'.join(f'[Page {i+1}]\n{value}' for i,value in enumerate(pages))
            if not any(value.strip() for value in pages):raise ValueError('This PDF has no readable text. Attach screenshots of the relevant pages instead.')
        elif mime=='application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if sum(i.file_size for i in archive.infolist())>16*1024*1024:raise ValueError('The expanded document exceeds 16 MB.')
                xml=archive.read('word/document.xml')
                if b'<!DOCTYPE' in xml or b'<!ENTITY' in xml:raise ValueError('Unsupported document XML.')
                root=ElementTree.fromstring(xml)
                text='\n'.join(''.join(p.itertext()) for p in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'))
        elif mime=='text/plain' and name.lower().endswith(('.drawio','.xml')):text=diagram_text(data)
        elif mime in {'text/plain','text/markdown','text/csv','application/json'}:text=data.decode('utf-8-sig')
        else:raise ValueError('Use PNG, JPEG, WebP, PDF, DOCX, TXT, Markdown, CSV or JSON.')
        if not text.strip():raise ValueError('The document has no readable text.')
        if len(text)>100000:raise ValueError('Document text exceeds 100,000 characters. Attach a shorter excerpt.')
        result.append({'name':name,'mime':mime,'text':text,'mode':'extracted text; embedded images and layout are not included'})
    if sum(len(i.get('text','')) for i in result)>150000:raise ValueError('Combined document text exceeds 150,000 characters.')
    return result

def prepare(items):
    if not items:return []
    try:
        run=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker'],input=json.dumps(items),text=True,capture_output=True,timeout=20)
        response=json.loads(run.stdout)
        if 'error' in response:raise RuntimeError(response['error'])
        return response['attachments']
    except (subprocess.TimeoutExpired,json.JSONDecodeError):raise RuntimeError('Attachment processing stopped. Try a smaller or simpler file.')

if __name__=='__main__':
    try:
        if sys.platform!='win32':
            import resource
            resource.setrlimit(resource.RLIMIT_CPU,(12,12))
            if sys.platform!='darwin':resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
        print(json.dumps({'attachments':extract(json.load(sys.stdin))}))
    except (ValueError,UnicodeError,zipfile.BadZipFile,KeyError) as exc:print(json.dumps({'error':str(exc)[:250]}))
    except Exception:print(json.dumps({'error':'Cannot read this attachment. Export a standard PDF, DOCX, text file or image and try again.'}))
