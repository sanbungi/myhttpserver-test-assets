from __future__ import annotations

import argparse
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = REPO_ROOT / "html" / "test-document.pdf"
DEFAULT_TITLE = "Generated PDF fixture"
DEFAULT_PAGES = 3
PAGE_WIDTH = 595
PAGE_HEIGHT = 842
PAGE_MARGIN = 72
PDF_TIMESTAMP = "D:20260305000000Z"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a deterministic multi-page PDF fixture for HTTP asset tests."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output PDF path. Default: {DEFAULT_OUTPUT_PATH}",
    )
    parser.add_argument(
        "--title",
        type=str,
        default=DEFAULT_TITLE,
        help=f"Document title rendered in the header. Default: {DEFAULT_TITLE!r}",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=DEFAULT_PAGES,
        help=f"Number of pages to generate. Default: {DEFAULT_PAGES}",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the output file if it already exists.",
    )
    return parser.parse_args()


def pdf_text_literal(text: str) -> str:
    ascii_text = text.encode("ascii", "replace").decode("ascii")
    escaped = ascii_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return f"({escaped})"


def pdf_hex_string(text: str) -> str:
    encoded = text.encode("utf-16-be")
    return f"<FEFF{encoded.hex().upper()}>"


def text_block(x: int, y: int, size: int, lines: list[str], *, leading: int | None = None) -> str:
    if not lines:
        return ""

    line_leading = leading if leading is not None else max(size + 4, int(size * 1.35))
    commands = [
        "BT",
        f"/F1 {size} Tf",
        f"{line_leading} TL",
        f"1 0 0 1 {x} {y} Tm",
        f"{pdf_text_literal(lines[0])} Tj",
    ]
    for line in lines[1:]:
        commands.append("T*")
        commands.append(f"{pdf_text_literal(line)} Tj")
    commands.append("ET")
    return "\n".join(commands)


def build_page_stream(*, page_number: int, total_pages: int, title: str) -> bytes:
    accent_red = 0.16 + ((page_number - 1) % 3) * 0.10
    accent_green = 0.30 + ((page_number - 1) % 2) * 0.10
    accent_blue = 0.56 + ((page_number - 1) % 4) * 0.06

    commands = [
        "q",
        "0.96 0.97 0.99 rg",
        f"0 0 {PAGE_WIDTH} {PAGE_HEIGHT} re f",
        f"{accent_red:.3f} {accent_green:.3f} {accent_blue:.3f} rg",
        f"0 {PAGE_HEIGHT - 116} {PAGE_WIDTH} 116 re f",
        "Q",
        "0.82 0.88 0.96 RG",
        "2 w",
        f"{PAGE_MARGIN} {PAGE_HEIGHT - 190} {PAGE_WIDTH - PAGE_MARGIN * 2} 94 re S",
    ]

    for band_index in range(3):
        band_y = PAGE_HEIGHT - 252 - band_index * 56
        band_width = PAGE_WIDTH - PAGE_MARGIN * 2 - band_index * 34
        band_red = min(0.92, accent_red + band_index * 0.08)
        band_green = min(0.92, accent_green + 0.06)
        band_blue = min(0.96, accent_blue + band_index * 0.04)
        commands.extend(
            [
                f"{band_red:.3f} {band_green:.3f} {band_blue:.3f} rg",
                f"{PAGE_MARGIN} {band_y} {band_width} 24 re f",
            ]
        )

    commands.extend(
        [
            "0.88 0.92 0.97 RG",
            "1.5 w",
        ]
    )
    for line_index in range(6):
        start_x = PAGE_MARGIN + line_index * 58
        end_x = start_x + 162
        commands.append(f"{start_x} 128 m {end_x} 336 l S")

    commands.extend(
        [
            "0.98 0.99 1 rg",
            text_block(
                PAGE_MARGIN,
                PAGE_HEIGHT - 74,
                26,
                [title, "Deterministic PDF asset for HTTP server tests"],
                leading=30,
            ),
            "0.18 0.22 0.30 rg",
            text_block(
                PAGE_MARGIN + 18,
                PAGE_HEIGHT - 150,
                12,
                [
                    f"Page {page_number} of {total_pages}",
                    "Use this fixture for content-type, cache, range, and download checks.",
                    "Generated without external PDF dependencies.",
                ],
            ),
            "0.12 0.15 0.22 rg",
            text_block(
                PAGE_MARGIN,
                420,
                14,
                [
                    "Fixture notes",
                    f"- Header title: {title}",
                    f"- Page count: {total_pages}",
                    "- Layout uses vector rectangles, strokes, and text blocks.",
                    "- Metadata is deterministic for reproducible output bytes.",
                ],
                leading=22,
            ),
            "0.26 0.32 0.42 rg",
            text_block(
                PAGE_MARGIN,
                94,
                11,
                [
                    "Path suggestion: /test-document.pdf",
                    "Script: scripts/generate_test_pdf.py",
                ],
                leading=16,
            ),
        ]
    )

    return ("\n".join(commands) + "\n").encode("ascii")


def build_stream_object(stream: bytes) -> bytes:
    return b"".join(
        [
            f"<< /Length {len(stream)} >>\n".encode("ascii"),
            b"stream\n",
            stream,
            b"endstream",
        ]
    )


def build_pdf(title: str, page_count: int) -> bytes:
    if page_count <= 0:
        raise ValueError("--pages must be greater than zero")

    objects: dict[int, bytes] = {}
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    page_refs: list[str] = []
    next_object_number = 4

    for page_number in range(1, page_count + 1):
        page_object_number = next_object_number
        content_object_number = next_object_number + 1
        next_object_number += 2

        page_refs.append(f"{page_object_number} 0 R")
        stream = build_page_stream(page_number=page_number, total_pages=page_count, title=title)
        objects[content_object_number] = build_stream_object(stream)
        objects[page_object_number] = (
            "<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            "/Resources << /Font << /F1 3 0 R >> >> "
            f"/Contents {content_object_number} 0 R >>"
        ).encode("ascii")

    objects[2] = f"<< /Type /Pages /Kids [{' '.join(page_refs)}] /Count {page_count} >>".encode("ascii")

    info_object_number = next_object_number
    objects[info_object_number] = (
        "<< "
        f"/Title {pdf_hex_string(title)} "
        "/Author (Codex) "
        "/Subject (HTTP server PDF fixture) "
        "/Creator (scripts/generate_test_pdf.py) "
        "/Producer (scripts/generate_test_pdf.py) "
        f"/CreationDate ({PDF_TIMESTAMP}) "
        f"/ModDate ({PDF_TIMESTAMP}) "
        ">>"
    ).encode("ascii")

    buffer = bytearray()
    buffer.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

    offsets = [0]
    for object_number in range(1, info_object_number + 1):
        offsets.append(len(buffer))
        buffer.extend(f"{object_number} 0 obj\n".encode("ascii"))
        buffer.extend(objects[object_number])
        buffer.extend(b"\nendobj\n")

    xref_offset = len(buffer)
    buffer.extend(f"xref\n0 {info_object_number + 1}\n".encode("ascii"))
    buffer.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buffer.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    buffer.extend(
        (
            "trailer\n"
            f"<< /Size {info_object_number + 1} /Root 1 0 R /Info {info_object_number} 0 R >>\n"
            "startxref\n"
            f"{xref_offset}\n"
            "%%EOF\n"
        ).encode("ascii")
    )
    return bytes(buffer)


def main() -> None:
    args = parse_args()
    output_path = args.output.resolve()

    if output_path.exists() and not args.force:
        print(f"skip {output_path.name}: already exists (use --force to overwrite)")
        return

    pdf_bytes = build_pdf(args.title, args.pages)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(pdf_bytes)
    print(f"wrote {output_path} ({len(pdf_bytes)} bytes, {args.pages} pages)")


if __name__ == "__main__":
    main()
