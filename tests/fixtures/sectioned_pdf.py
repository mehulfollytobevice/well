"""Build a tiny ruled-table PDF for parser tests (no GDR downloads)."""

from __future__ import annotations

from pathlib import Path


def write_sectioned_fixture_pdf(path: Path) -> Path:
    """Write a one-page PDF with two headings and a 2-column table."""
    content = """
BT
/F1 16 Tf
1 0 0 1 72 720 Tm
(Current Operations) Tj
/F1 11 Tf
1 0 0 1 72 692 Tm
(Continue pumping at 10 bpm.) Tj
ET
72 640 m 408 640 l S
72 610 m 408 610 l S
72 580 m 408 580 l S
72 640 m 72 580 l S
240 640 m 240 580 l S
408 640 m 408 580 l S
BT
/F1 11 Tf
1 0 0 1 86 618 Tm
(From) Tj
1 0 0 1 256 618 Tm
(Description) Tj
1 0 0 1 86 588 Tm
(6:00) Tj
1 0 0 1 256 588 Tm
(RIGU) Tj
/F1 16 Tf
1 0 0 1 72 520 Tm
(Safety Summary) Tj
/F1 11 Tf
1 0 0 1 72 492 Tm
(No incidents or events reported.) Tj
ET
""".strip()
    path.write_bytes(_assemble_pdf(content.encode("latin-1")))
    return path


def _assemble_pdf(stream: bytes) -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    header = b"%PDF-1.4\n"
    chunks = [header]
    offsets: list[int] = []
    cursor = len(header)
    for index, payload in enumerate(objects, start=1):
        obj = f"{index} 0 obj\n".encode() + payload + b"\nendobj\n"
        offsets.append(cursor)
        chunks.append(obj)
        cursor += len(obj)
    xref_entries = [b"0000000000 65535 f \n"]
    xref_entries.extend(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    xref = (
        b"xref\n"
        + f"0 {len(objects) + 1}\n".encode()
        + b"".join(xref_entries)
        + b"trailer\n"
        + f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode()
        + b"startxref\n"
        + f"{cursor}\n".encode()
        + b"%%EOF\n"
    )
    chunks.append(xref)
    return b"".join(chunks)
