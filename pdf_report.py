"""PDF paginado sin servicios externos; Helvetica y codificación WinAnsi."""
import textwrap


def make_pdf(title, lines):
    wrapped = [title, 'Fundación Deportistas por un Sueño | Uso interno', '']
    for line in lines:
        wrapped.extend(textwrap.wrap(str(line), 92) or [''])
    pages = [wrapped[i:i+48] for i in range(0, len(wrapped), 48)]
    objects = [b'', b'', b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>']
    kids = []
    for n, page in enumerate(pages):
        page_id, stream_id = len(objects)+1, len(objects)+2
        kids.append(f'{page_id} 0 R')
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {stream_id} 0 R >>'.encode())
        commands = ['BT /F1 11 Tf 44 796 Td 15 TL']
        for line in page + ['', f'Página {n+1} de {len(pages)}']:
            clean = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)').replace('\r', ' ').replace('\n', ' ')
            commands.extend([f'({clean}) Tj', 'T*'])
        stream = ('\n'.join(commands) + '\nET').encode('cp1252', 'replace')
        objects.append(f'<< /Length {len(stream)} >>\nstream\n'.encode() + stream + b'\nendstream')
    objects[0] = b'<< /Type /Catalog /Pages 2 0 R >>'
    objects[1] = f'<< /Type /Pages /Kids [{" ".join(kids)}] /Count {len(kids)} >>'.encode()
    out, offsets = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n'), [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(out)); out.extend(f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n')
    pos = len(out)
    out.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:
        out.extend(f'{offset:010} 00000 n \n'.encode())
    out.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{pos}\n%%EOF'.encode())
    return bytes(out)
