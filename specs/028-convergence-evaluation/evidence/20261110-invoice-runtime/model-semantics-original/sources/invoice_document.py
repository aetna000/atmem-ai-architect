"""Bounded native-text and OCR extraction, without model or cloud credentials.

Run this parser in a dedicated, resource-limited, credentialless container. A child
deadline is not a sandbox. No links, attachments, scripts or PDF instructions are
executed by application code. Every admitted page is processed; overflow fails
explicitly rather than returning a truncated invoice.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import tempfile
import time

class DocumentError(ValueError):
    def __init__(self,code):
        if code not in {'invalid_pdf','document_too_large','encrypted_pdf','page_limit','text_limit','unreadable_pdf','extraction_unavailable','extraction_timeout'}:raise ValueError('Unknown document failure')
        self.code=code;super().__init__(code)

class PdfDocument:
    def __init__(self,*,tools=None,max_pages=100,deadline_seconds=110):
        names=['pdfinfo','pdftotext','pdftoppm','tesseract'];tools=tools or {name:'/usr/bin/'+name for name in names}
        if set(tools)!=set(names)or any(not isinstance(path,str)or not Path(path).is_absolute()or not Path(path).is_file()for path in tools.values()):raise ValueError('Install the reviewed native parser tools')
        if type(max_pages)is not int or not 1<=max_pages<=100 or type(deadline_seconds)is not int or not 10<=deadline_seconds<=110:raise ValueError('Invalid parser limits')
        self.tools=dict(tools);self.max_pages=max_pages;self.deadline_seconds=deadline_seconds

    def _run(self,name,args,*,folder,deadline,limit):
        remaining=min(30,deadline-time.monotonic())
        if remaining<=0:raise DocumentError('extraction_timeout')
        process=None
        try:
            # Inherit the credentialless parser's process group. An outer parser
            # termination therefore also terminates every active native tool.
            process=subprocess.Popen([self.tools[name],*args],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,cwd=folder,env={'PATH':'/usr/bin:/bin','HOME':str(folder),'TMPDIR':str(folder),'LANG':'C','LC_ALL':'C','OMP_THREAD_LIMIT':'1'})
            started=time.monotonic();data=bytearray()
            with selectors.DefaultSelector()as selector:
                os.set_blocking(process.stdout.fileno(),False);selector.register(process.stdout,selectors.EVENT_READ)
                while selector.get_map():
                    wait=remaining-(time.monotonic()-started)
                    if wait<=0:raise DocumentError('extraction_timeout')
                    for key,_ in selector.select(min(wait,.1)):
                        chunk=os.read(key.fd,8192)
                        if not chunk:selector.unregister(key.fileobj);continue
                        data.extend(chunk)
                        if len(data)>limit:raise DocumentError('text_limit'if name in {'pdftotext','tesseract'}else'invalid_pdf')
            try:code=process.wait(timeout=max(.01,remaining-(time.monotonic()-started)))
            except subprocess.TimeoutExpired:raise DocumentError('extraction_timeout')from None
            if code!=0:raise DocumentError('invalid_pdf')
            return bytes(data)
        except DocumentError:raise
        except Exception:raise DocumentError('extraction_unavailable')from None
        finally:
            if process is not None:
                if process.poll()is None:process.kill()
                process.wait()
                if process.stdout:process.stdout.close()

    def extract(self,pdf,expected_sha256):
        if not isinstance(pdf,bytes)or not pdf.startswith(b'%PDF-'):raise DocumentError('invalid_pdf')
        if len(pdf)>10000000:raise DocumentError('document_too_large')
        if not isinstance(expected_sha256,str)or not re.fullmatch(r'[0-9a-f]{64}',expected_sha256)or hashlib.sha256(pdf).hexdigest()!=expected_sha256:raise DocumentError('invalid_pdf')
        deadline=time.monotonic()+self.deadline_seconds
        with tempfile.TemporaryDirectory(prefix='atmem-document-')as temporary:
            folder=Path(temporary);source=folder/'invoice.pdf';source.write_bytes(pdf);source.chmod(0o600)
            info=self._run('pdfinfo',[str(source)],folder=folder,deadline=deadline,limit=8192).decode('utf-8',errors='replace')
            if re.search(r'^Encrypted:\s+yes',info,re.M):raise DocumentError('encrypted_pdf')
            match=re.search(r'^Pages:\s+(\d+)\s*$',info,re.M)
            if not match:raise DocumentError('invalid_pdf')
            count=int(match[1])
            if not 1<=count<=self.max_pages:raise DocumentError('page_limit')
            result={'format':'invoice-document-v1','sha256':expected_sha256,'pages':[]};total=0
            for number in range(1,count+1):
                native=self._run('pdftotext',['-f',str(number),'-l',str(number),'-layout','-enc','UTF-8',str(source),'-'],folder=folder,deadline=deadline,limit=60000).decode('utf-8').strip()
                image=self._run('pdftoppm',['-f',str(number),'-l',str(number),'-scale-to','2400','-singlefile','-gray','-png',str(source)],folder=folder,deadline=deadline,limit=10000000)
                raster=folder/'page.png';raster.write_bytes(image);raster.chmod(0o600)
                ocr=self._run('tesseract',[str(raster),'stdout','-l','eng','--psm','3'],folder=folder,deadline=deadline,limit=60000).decode('utf-8').strip();raster.unlink()
                total+=len(native.encode('utf-8'))+len(ocr.encode('utf-8'))
                if total>110000:raise DocumentError('text_limit')
                result['pages'].append({'number':number,'text':native,'ocr':ocr})
            if not any(page['text'].strip()or page['ocr'].strip()for page in result['pages']):raise DocumentError('unreadable_pdf')
            if len(json.dumps(result,ensure_ascii=False).encode('utf-8'))>120000:raise DocumentError('text_limit')
            return result
