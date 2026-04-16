import json
from pathlib import Path

from pdftext.extraction import plain_text_output, dictionary_output

# Path ke PDF di project root (dua level di atas folder ini)
PDF_PATH = Path(__file__).parent.parent.parent / "file.pdf"
OUTPUT_DIR = Path(__file__).parent / "output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def extract_plain_text(pdf_path: Path) -> str:
    """Ekstrak teks polos dari PDF menggunakan pdftext."""
    return plain_text_output(str(pdf_path), sort=False)


def extract_dictionary(pdf_path: Path) -> list:
    """Ekstrak teks dalam format dictionary (per karakter/word) dari PDF."""
    return dictionary_output(str(pdf_path), sort=False)


def save_plain_text(text: str, output_path: Path) -> None:
    output_path.write_text(text, encoding="utf-8")
    print(f"Plain text saved to: {output_path}")


class _PdftextEncoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, "__dict__"):
            return o.__dict__
        return super().default(o)


def _get_block_dominant_size(block: dict) -> float:
    """Kembalikan font size terbesar yang muncul pada span berteks dalam block."""
    sizes = []
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            text = span.get("text", "").strip()
            size = span.get("font", {}).get("size", 0.0)
            # Abaikan span tanpa teks atau size <= 1 (invisible/whitespace artifact)
            if text and size > 1.0:
                sizes.append(round(size, 1))
    if not sizes:
        return 0.0
    return max(sizes)


def _line_to_cell_texts(line: dict) -> list[str]:
    """Kembalikan list teks per span dalam satu line (untuk kolom tabel)."""
    cells = []
    for span in line.get("spans", []):
        text = span.get("text", "").strip()
        if text:
            cells.append(text)
    return cells


def _line_to_text(line: dict) -> str:
    """Gabungkan semua span text dalam satu line menjadi satu string."""
    return " ".join(
        span.get("text", "").strip()
        for span in line.get("spans", [])
        if span.get("text", "").strip()
    )


def convert_dict_to_markdown(data: list) -> str:
    """
    Konversi list page dari dictionary_output ke string Markdown.

    Font size mapping:
    - >= 22.0  -> # Heading (H1)
    - 12.0     -> paragraf biasa
    - 10.0     -> tabel Markdown (line 0 = header, line 1+ = rows)
    - lainnya  -> teks biasa
    """
    md_parts: list[str] = []

    for page in data:
        for block in page.get("blocks", []):
            lines = block.get("lines", [])
            if not lines:
                continue

            dominant_size = _get_block_dominant_size(block)

            if dominant_size >= 22.0:
                for line in lines:
                    text = _line_to_text(line)
                    if text:
                        md_parts.append(f"# {text}")

            elif dominant_size == 10.0:
                header_cells = _line_to_cell_texts(lines[0])
                if not header_cells:
                    continue
                col_count = len(header_cells)
                md_parts.append("| " + " | ".join(header_cells) + " |")
                md_parts.append("| " + " | ".join(["---"] * col_count) + " |")
                for line in lines[1:]:
                    cells = _line_to_cell_texts(line)
                    while len(cells) < col_count:
                        cells.append("")
                    cells = cells[:col_count]
                    md_parts.append("| " + " | ".join(cells) + " |")

            else:
                para_lines = []
                for line in lines:
                    text = _line_to_text(line)
                    if text:
                        para_lines.append(text)
                if para_lines:
                    md_parts.append(" ".join(para_lines))

        md_parts.append("")

    return "\n\n".join(part for part in md_parts if part)


def save_markdown(text: str, output_path: Path) -> None:
    output_path.write_text(text, encoding="utf-8")
    print(f"Markdown saved to: {output_path}")


def save_dictionary(data: list, output_path: Path) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, cls=_PdftextEncoder)
    print(f"Dictionary output saved to: {output_path}")


def main():
    if not PDF_PATH.exists():
        print(f"ERROR: PDF not found at {PDF_PATH}")
        return

    print(f"Processing: {PDF_PATH}")
    print(f"Output dir: {OUTPUT_DIR}")
    print("-" * 40)

    # Ekstrak plain text
    print("Extracting plain text...")
    text = extract_plain_text(PDF_PATH)
    save_plain_text(text, OUTPUT_DIR / "output_plain.txt")
    print(f"Total characters: {len(text)}")

    # Ekstrak dictionary format
    print("\nExtracting dictionary format...")
    data = extract_dictionary(PDF_PATH)
    save_dictionary(data, OUTPUT_DIR / "output_dict.json")
    print(f"Total pages: {len(data)}")

    # Konversi dictionary ke Markdown
    print("\nConverting to Markdown...")
    md_text = convert_dict_to_markdown(data)
    save_markdown(md_text, OUTPUT_DIR / "output.md")
    print(f"Markdown characters: {len(md_text)}")

    print("\nDone!")


if __name__ == "__main__":
    main()
