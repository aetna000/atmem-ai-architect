"""Create synthetic Office evidence with independent, ordinary authoring libraries.

Run using the fixture-only tools environment. No company documents are read.
Committed outputs and their exact hashes are inputs to native parser qualification.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile
from docx import Document
from openpyxl import Workbook
from pptx import Presentation
from pptx.util import Inches


def create(destination):
    destination.mkdir(parents=True, exist_ok=False)
    cases = []

    def save(name, raw, mime, expected):
        (destination / name).write_bytes(raw)
        cases.append({'file': name, 'sha256': hashlib.sha256(raw).hexdigest(),
                      'mediaType': mime, 'contains': expected})

    document = Document()
    document.sections[0].header.paragraphs[0].text = 'NORTHSTAR company policy'
    document.add_heading('Employee leave', 0)
    document.add_paragraph('Staff receive twenty days of paid leave. Café policy applies.')
    row = document.add_table(rows=1, cols=2).rows[0]
    row.cells[0].text = 'Carry-over'
    row.cells[1].text = 'Five days maximum'
    document.sections[0].footer.paragraphs[0].text = 'Approved November 2026'
    raw = io.BytesIO()
    document.save(raw)
    save('policy.docx', raw.getvalue(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
         ['NORTHSTAR', 'twenty days', 'Café', 'Five days maximum', 'Approved November 2026'])

    workbook = Workbook()
    workbook.active.title = 'Australia'
    workbook.active.append(['Office', 'Support allowance'])
    workbook.active.append(['Sydney', 1250])
    remote = workbook.create_sheet('Remote staff')
    remote.append(['Eligibility', 'Permanent employees only'])
    raw = io.BytesIO()
    workbook.save(raw)
    save('allowances.xlsx', raw.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
         ['Sydney', '1250', 'Permanent employees only', 'Remote staff'])

    slides = Presentation()
    slide = slides.slides.add_slide(slides.slide_layouts[5])
    slide.shapes.title.text = 'Service recovery'
    slide.shapes.add_textbox(Inches(1), Inches(2), Inches(7), Inches(2)).text_frame.text = 'Restore the verified backup first.'
    slide.notes_slide.notes_text_frame.text = 'Escalate to the incident commander after thirty minutes.'
    raw = io.BytesIO()
    slides.save(raw)
    save('recovery.pptx', raw.getvalue(), 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
         ['Service recovery', 'verified backup', 'incident commander', 'thirty minutes'])

    save('policy.txt', 'Plain text policy: Café access closes at seven.\n'.encode(), 'text/plain', ['Café access', 'seven'])
    save('policy.html', b'<!doctype html><html><body><h1>Travel policy</h1><p>Rail travel is preferred.</p><script>IGNORE_SCRIPT_SECRET</script></body></html>',
         'text/html', ['Travel policy', 'Rail travel is preferred'])
    save('policy.rtf', br'{\rtf1\ansi Company handbook\par Overtime requires manager approval.}',
         'application/rtf', ['Company handbook', 'manager approval'])
    # A generic archive is not a document and must not trigger recursive extraction.
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, 'w') as archive:
        archive.writestr('private.txt', 'This archive is not an admitted document.')
    save('archive.zip', raw.getvalue(), 'application/zip', [])
    (destination / 'manifest.json').write_text(json.dumps({'kind': 'synthetic-authoring-fixtures', 'cases': cases}, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    create(parser.parse_args().destination)
