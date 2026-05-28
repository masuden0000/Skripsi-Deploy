"""
Fungsi: Membentuk potongan teks (chunk) dari hasil ekstraksi halaman untuk keperluan RAG.

Digunakan oleh: model_ai/loader/pdf_extractor.py

Tujuan: Menghasilkan unit konteks yang stabil agar retrieval lebih relevan.
"""
import re

from langchain_text_splitters import MarkdownTextSplitter

# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `PREFACE_LABEL` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
PREFACE_LABEL = "PREFACE"
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `HEADING_PATTERN` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `DOC_PAGE_PATTERN` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
DOC_PAGE_PATTERN = re.compile(r"^\s*(\d{1,3})\s*$")
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `STRIKETHROUGH_PATTERN` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
STRIKETHROUGH_PATTERN = re.compile(r"~~[^~]*~~")


# Menormalkan judul heading agar `chunk_parent` bersih dan konsisten.
# Fungsi ini dipakai saat section/BAB baru terdeteksi di markdown.
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `normalize_heading` sebagai bagian alur `chunk_builder`.
# ---------------------------------------------------------------------------
def normalize_heading(raw_heading: str) -> str:
    heading = re.sub(r"\*\*(.*?)\*\*", r"\1", raw_heading)
    heading = re.sub(r"__(.*?)__", r"\1", heading)
    return " ".join(heading.split()).strip() or PREFACE_LABEL


# Mendeteksi heading OCR artifact berdasarkan pola karakter, bukan string literal.
# Heading dianggap noise jika memenuhi salah satu dari tiga kondisi:
#   1. Mengandung backslash atau tanda seru (jelas dari logo/watermark)
#   2. Semua kata (huruf saja) berukuran ≤ 3 karakter (header halaman singkat)
#   3. Semua huruf uppercase AND panjang ≤ 10 karakter (inisial/kode OCR)
# Bold markers (**text**) tidak diperiksa di sini karena sudah
# distripping oleh normalize_heading — fungsi ini menerima raw_heading.
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `is_noise_heading` sebagai bagian alur `chunk_builder`.
# ---------------------------------------------------------------------------
def is_noise_heading(raw_heading: str) -> bool:
    text = raw_heading.strip()
    if not text:
        return True
    if "\\" in text or "!" in text:
        return True
    # Lepaskan bold/italic markers sebelum cek kata
    plain = re.sub(r"[*_`]", "", text).strip()
    words = re.findall(r"[a-zA-Z]+", plain)
    if words and all(len(w) <= 3 for w in words):
        return True
    if len(plain) <= 10 and plain.replace(" ", "").isupper():
        return True
    return False


# Memecah hasil markdown per halaman menjadi daftar baris yang masih
# menyimpan informasi page asal. Struktur ini menjadi fondasi untuk
# pembentukan section sekaligus page range tiap chunk.
#
# Nomor halaman yang dipakai adalah nomor halaman *dokumen* (yang tercetak),
# bukan indeks halaman fisik PDF. Baris yang hanya berisi angka (misal "1",
# "12") dianggap penanda halaman dokumen, dipakai untuk memperbarui tracker
# `current_doc_page`, lalu dibuang dari konten. Sebelum penanda pertama
# ditemukan, fallback ke nomor halaman fisik (1-indexed).
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `iter_page_lines` sebagai bagian alur `chunk_builder`.
# ---------------------------------------------------------------------------
def iter_page_lines(page_chunks: list[dict]) -> list[dict]:
    lines: list[dict] = []
    current_doc_page: int | None = None
    for page in page_chunks:
        physical_page: int = page["metadata"]["page_number"] + 1
        text = page.get("text", "")

        # Pass 1: kumpulkan baris bersih dan temukan penanda halaman pada scan
        # page ini. Penanda halaman dicetak di bagian bawah halaman, sehingga
        # seluruh baris pada scan page yang sama merujuk ke halaman tersebut.
        page_lines: list[str] = []
        found_doc_page: int | None = None
        for line in text.splitlines():
            doc_page_match = DOC_PAGE_PATTERN.match(line)
            if doc_page_match:
                found_doc_page = int(doc_page_match.group(1))
                continue
            cleaned = STRIKETHROUGH_PATTERN.sub("", line).rstrip()
            if line.strip() and not cleaned.strip():
                continue
            page_lines.append(cleaned)

        # Tentukan nomor halaman dokumen untuk seluruh scan page ini secara
        # retrospektif: jika ditemukan penanda, pakai nilainya; jika tidak,
        # auto-increment dari halaman sebelumnya (OCR mungkin melewatkan
        # penanda); jika belum ada referensi sama sekali, gunakan physical page.
        if found_doc_page is not None:
            doc_page = found_doc_page
            current_doc_page = found_doc_page
        elif current_doc_page is not None:
            current_doc_page += 1
            doc_page = current_doc_page
        else:
            doc_page = physical_page

        # Pass 2: emit semua baris dengan nomor halaman yang sudah ditentukan
        for line_text in page_lines:
            lines.append({"text": line_text, "page": doc_page})
    return lines


# Mengelompokkan baris markdown menjadi section/BAB berdasarkan heading.
# Output fungsi ini dipakai langsung oleh proses chunking agar chunk tidak
# menyeberang antar BAB dan setiap chunk punya `chunk_parent`.
# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/loader/pdf_extractor.py
# Menjalankan fungsi `build_sections` sebagai bagian alur `chunk_builder`.
# ---------------------------------------------------------------------------
def build_sections(page_chunks: list[dict]) -> list[dict]:
    sections: list[dict] = []
    current_heading = PREFACE_LABEL
    current_lines: list[dict] = []
    in_noise_section = False

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
            raw_heading = heading_match.group(2)
            if is_noise_heading(raw_heading):
                in_noise_section = True
                continue
            flush_section()
            in_noise_section = False
            current_heading = normalize_heading(raw_heading)
            current_lines = [line]
            continue

        if in_noise_section:
            continue

        current_lines.append(line)

    flush_section()
    return sections


# Mencari posisi chunk hasil splitter di dalam text section aslinya.
# Posisi ini dibutuhkan agar chunk bisa dihubungkan kembali ke fragmen
# halaman yang menyusunnya.
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `locate_chunk` sebagai bagian alur `chunk_builder`.
# ---------------------------------------------------------------------------
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
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `resolve_page_range` sebagai bagian alur `chunk_builder`.
# ---------------------------------------------------------------------------
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
# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/loader/pdf_extractor.py
# Menjalankan fungsi `build_payload` sebagai bagian alur `chunk_builder`.
# ---------------------------------------------------------------------------
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
