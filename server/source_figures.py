"""Extract bounded, non-executable figure evidence; never resolve external links."""
import base64
import hashlib
import io
import posixpath
import warnings
from xml.etree import ElementTree as ET

MAX_FIGURES = 64
MAX_IMAGE_BYTES = 3 * 1024 * 1024
MAX_FIGURE_BYTES = 24 * 1024 * 1024
MAX_PIXELS = 20_000_000
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'


def docx_figures(archive, root):
    members = [name for name in archive.namelist() if name.startswith('word/media/') and not name.endswith('/')]
    if len(members) > MAX_FIGURES or len(members) != len(set(members)):
        raise ValueError('Document figure count or duplicate members exceed the supported evidence contract.')
    relationships = {}
    try:
        xml = archive.read('word/_rels/document.xml.rels')
    except KeyError:
        xml = None
    if xml:
        if b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper():
            raise ValueError('Unsupported figure relationship declarations.')
        for rel in ET.fromstring(xml):
            if rel.get('TargetMode', '').lower() == 'external':
                continue
            target = posixpath.normpath(posixpath.join('word', rel.get('Target', '')))
            if target in members:
                relationships[rel.get('Id')] = target
    locations = {name: [] for name in members}
    for number, paragraph in enumerate(root.iter(W + 'p'), 1):
        for child in paragraph.iter():
            target = relationships.get(child.get(R + 'embed') or child.get(R + 'id'))
            if target and f'paragraph:{number}' not in locations[target]:
                locations[target].append(f'paragraph:{number}')
    result = [raster_figure(archive.read(name), f'figure-{index}', name.removeprefix('word/media/'), locations[name])
              for index, name in enumerate(members, 1)]
    if sum(row.get('bytes', 0) for row in result) > MAX_FIGURE_BYTES:
        raise ValueError('Document figures exceed the 24 MB normalized evidence bound.')
    return result


def raster_figure(original, ident, name, locations):
    from PIL import Image
    row = {'id': ident, 'name': name, 'originalSha256': hashlib.sha256(original).hexdigest(),
           'locations': locations, 'status': 'unavailable', 'reason': 'unsupported_or_invalid_image'}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(original)) as image:
                if image.width * image.height > MAX_PIXELS:
                    row['reason'] = 'image_pixel_limit'
                elif image.format not in {'PNG', 'JPEG', 'WEBP', 'GIF', 'TIFF', 'BMP'}:
                    row['reason'] = 'unsupported_image_format'
                elif getattr(image, 'n_frames', 1) != 1:
                    row['reason'] = 'multiple_frames_require_explicit_review'
                else:
                    image.load()
                    converted = image.convert('RGBA' if 'A' in image.getbands() or 'transparency' in image.info else 'RGB')
                    output = io.BytesIO()
                    converted.save(output, format='PNG')
                    content = output.getvalue()
                    if len(content) > MAX_IMAGE_BYTES:
                        row['reason'] = 'image_byte_limit'
                    else:
                        row.update(status='available', mime='image/png', bytes=len(content), width=image.width, height=image.height,
                                   sha256=hashlib.sha256(content).hexdigest(), data=base64.b64encode(content).decode('ascii'))
                        row.pop('reason')
    except (OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        pass
    return row
