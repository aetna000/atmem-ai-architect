"""Byte-only CLI used by the isolated document parser image."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from enterprise_document import CompanyDocument, ExtractionError, MAX_INPUT
from invoice_document import PdfDocument


def installed_parser():
    return CompanyDocument(java='/opt/java/bin/java',
        classpath=['/app/tika-app.jar', '/app/document-bridge'], pdf=PdfDocument())


if __name__ == '__main__':
    try:
        if len(sys.argv) > 2:
            raise ExtractionError('invalid_document')
        raw = sys.stdin.buffer.read(MAX_INPUT + 1)
        document = installed_parser().extract(raw, sys.argv[1] if len(sys.argv) == 2 else 'application/octet-stream')
        value, code = {'status': 'ok', 'document': document}, 0
    except ExtractionError as failure:
        value, code = {'status': 'rejected', 'reason': failure.code}, 2
    except Exception:
        value, code = {'status': 'rejected', 'reason': 'extraction_unavailable'}, 2
    print(json.dumps(value, ensure_ascii=False, allow_nan=False))
    raise SystemExit(code)
