import re

from langchain_text_splitters import MarkdownTextSplitter

PREFACE_LABEL = "PREFACE"
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


# Menormalkan judul heading agar `chunk_parent` bersih dan konsisten.
# Fungsi ini dipakai saat section/BAB baru terdeteksi di markdown.
def normalize_heading(raw_heading: str) -> str:
    heading = re.sub(r"\*\*(.*?)\*\*", r"\1", raw_heading)
    heading = re.sub(r"__(.*?)__", r"\1", heading)
    return " ".join(heading.split()).strip() or PREFACE_LABEL


# Memecah hasil markdown per halaman menjadi daftar baris yang masih
# menyimpan informasi page asal. Struktur ini menjadi fondasi untuk
# pembentukan section sekaligus page range tiap chunk.
def iter_page_lines(page_chunks: list[dict]) -> list[dict]:
    lines: list[dict] = []
    for page in page_chunks:
        page_number = page["metadata"]["page_number"]
        text = page.get("text", "")
        for line in text.splitlines():
            lines.append({"text": line, "page": page_number})
    return lines


# Mengelompokkan baris markdown menjadi section/BAB berdasarkan heading.
# Output fungsi ini dipakai langsung oleh proses chunking agar chunk tidak
# menyeberang antar BAB dan setiap chunk punya `chunk_parent`.
def build_sections(page_chunks: list[dict]) -> list[dict]:
    sections: list[dict] = []
    current_heading = PREFACE_LABEL
    current_lines: list[dict] = []

    # Menyimpan section yang sedang aktif beserta peta posisi karakter
    # ke halaman asal. Peta ini nanti dipakai untuk menghitung page range
    # ketika sebuah section dipecah menjadi beberapa chunk.
    def flush_section() -> None:
        if not current_lines:
            return

        content_lines = [line["text"] for line in current_lines]
        section_text = "\n".join(content_lines).strip()
        if not section_text:
            return

        fragment_spans = []
        cursor = 0
        for index, line in enumerate(current_lines):
            line_text = line["text"]
            start = cursor
            end = start + len(line_text)
            fragment_spans.append(
                {"page": line["page"], "start": start, "end": end}
            )
            cursor = end
            if index < len(current_lines) - 1:
                cursor += 1

        sections.append(
            {
                "heading": current_heading,
                "text": section_text,
                "fragments": fragment_spans,
            }
        )

    for line in iter_page_lines(page_chunks):
        stripped_line = line["text"].strip()
        heading_match = HEADING_PATTERN.match(stripped_line)

        if heading_match:
            flush_section()
            current_heading = normalize_heading(heading_match.group(2))
            current_lines = [line]
            continue

        current_lines.append(line)

    flush_section()
    return sections


# Mencari posisi chunk hasil splitter di dalam text section aslinya.
# Posisi ini dibutuhkan agar chunk bisa dihubungkan kembali ke fragmen
# halaman yang menyusunnya.
def locate_chunk(section_text: str, chunk_text: str, search_start: int) -> tuple[int, int]:
    start = section_text.find(chunk_text, search_start)
    if start == -1 and search_start > 0:
        start = section_text.find(chunk_text)
    if start == -1:
        raise ValueError("Chunk tidak bisa dipetakan kembali ke section asal.")
    return start, start + len(chunk_text)


# Mengubah rentang karakter chunk menjadi rentang halaman.
# Fungsi ini memakai `fragments` dari `build_sections`, jadi hubungan
# antar fungsi di sini adalah: section -> posisi chunk -> page range.
def resolve_page_range(fragments: list[dict], chunk_start: int, chunk_end: int) -> dict:
    touched_pages = [
        fragment["page"]
        for fragment in fragments
        if fragment["end"] > chunk_start and fragment["start"] < chunk_end
    ]
    if not touched_pages:
        raise ValueError("Chunk tidak memiliki halaman asal.")
    return {"start": min(touched_pages), "end": max(touched_pages)}


# Membentuk payload final chunk dari daftar section.
# Fungsi ini adalah pusat proses chunking: memecah section, memberi parent,
# menghitung page range, lalu mengisi `chunk_prev` dan `chunk_next`
# khusus di dalam BAB yang sama.
def build_payload(sections: list[dict], splitter: MarkdownTextSplitter) -> list[dict]:
    payload: list[dict] = []

    for section in sections:
        section_text = section["text"]
        chunk_texts = splitter.split_text(section_text)
        section_chunk_indexes: list[int] = []
        search_start = 0

        for chunk_text in chunk_texts:
            content = chunk_text.strip()
            if not content:
                continue

            chunk_start, chunk_end = locate_chunk(section_text, chunk_text, search_start)
            search_start = max(chunk_start, chunk_end - 150)
            page_range = resolve_page_range(section["fragments"], chunk_start, chunk_end)

            payload.append(
                {
                    "chunk_index": len(payload) + 1,
                    "content": content,
                    "chunk_parent": section["heading"],
                    "chunk_prev": None,
                    "chunk_next": None,
                    "page": page_range,
                }
            )
            section_chunk_indexes.append(len(payload) - 1)

        # Linking dilakukan setelah semua chunk dalam satu section selesai dibuat.
        # Dengan begitu `chunk_prev` dan `chunk_next` hanya menghubungkan chunk
        # tetangga dalam BAB yang sama.
        for offset, payload_index in enumerate(section_chunk_indexes):
            if offset > 0:
                payload[payload_index]["chunk_prev"] = payload[
                    section_chunk_indexes[offset - 1]
                ]["chunk_index"]
            if offset < len(section_chunk_indexes) - 1:
                payload[payload_index]["chunk_next"] = payload[
                    section_chunk_indexes[offset + 1]
                ]["chunk_index"]

    return payload
