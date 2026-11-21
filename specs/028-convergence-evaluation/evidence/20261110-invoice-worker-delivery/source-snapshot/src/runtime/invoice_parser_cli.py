"""Credentialless one-shot parser protocol; no URLs, cloud calls or model work."""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from invoice_document import PdfDocument,DocumentError

if __name__=='__main__':
    try:
        raw=sys.stdin.buffer.read(10000001)
        document=PdfDocument().extract(raw,hashlib.sha256(raw).hexdigest())
        sys.stdout.write(json.dumps({'status':'ok','document':document},ensure_ascii=False))
    except DocumentError as error:
        sys.stdout.write(json.dumps({'status':'rejected','reason':error.code}));sys.exit(2)
    except Exception:
        sys.stdout.write(json.dumps({'status':'rejected','reason':'extraction_unavailable'}));sys.exit(2)
