"""Membentuk potongan teks (chunk) dari hasil ekstraksi halaman untuk keperluan RAG. Posisi pipeline: pdf_extractor → chunk_builder → supabase_ingest."""
import re

from langchain_text_splitters import MarkdownTextSplitter

PREFACE_LABEL = "PREFACE"
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
DOC_PAGE_PATTERN = re.compile(r"^\s*(\d{1,3})\s*$")
STRIKETHROUGH_PATTERN = re.compile(r"~~[^~]*~~")
PICTURE_ARTIFACT_PATTERN = re.compile(
    r"^\*\*\s*==>.*?<==\s*\*\*$"
    r"|^\*\*-{4,}\s*(?:Start|End) of picture text\s*-{4,}\*\*"
    r"|^-{4,}\s*(?:Start|End) of picture text\s*-{4,}$"
)
TABLE_SEPARATOR_PATTERN = re.compile(r"^\|[\s\-:|]+\|?$")
TABLE_EMPTY_PATTERN = re.compile(r"^\|+$")
TABLE_CONTENT_PATTERN = re.compile(r"^\|(.+)\|$")


def normalize_heading(raw_heading: str) -> str:
    heading = re.sub(r"\*\*(.*?)\*\*", r"\1", raw_heading)
    heading = re.sub(r"__(.*?)__", r"\1", heading)
    return " ".join(heading.split()).strip() or PREFACE_LABEL


def is_noise_heading(raw_heading: str) -> bool:
    text = raw_heading.strip()
    if not text:
        return True
    if "\\" in text or "!" in text:
        return True
    plain = re.sub(r"[*_`]", "", text).strip()
    words = re.findall(r"[a-zA-Z]+", plain)
    if words and all(len(w) <= 3 for w in words):
        return True
    if len(plain) <= 7 and plain.replace(" ", "").isupper():
        return True
    return False


def iter_page_lines(page_chunks: list[dict]) -> list[dict]:
    lines: list[dict] = []
    current_doc_page: int | None = None
    for page in page_chunks:
        physical_page: int = page["metadata"]["page_number"] + 1
        text = page.get("text", "")

        page_lines: list[str] = []
        found_doc_page: int | None = None
        for line in text.splitlines():
            doc_page_match = DOC_PAGE_PATTERN.match(line)
            if doc_page_match:
                found_doc_page = int(doc_page_match.group(1))
                continue
            if PICTURE_ARTIFACT_PATTERN.match(line.strip()):
                continue
            if TABLE_SEPARATOR_PATTERN.match(line.strip()):
                continue
            if TABLE_EMPTY_PATTERN.match(line.strip()):
                continue
            table_content_match = TABLE_CONTENT_PATTERN.match(line.strip())
            if table_content_match:
                line = table_content_match.group(1).strip()
            cleaned = STRIKETHROUGH_PATTERN.sub("", line).rstrip()
            if line.strip() and not cleaned.strip():
                continue
            page_lines.append(cleaned)

        if found_doc_page is not None:
            doc_page = found_doc_page
            current_doc_page = found_doc_page
        elif current_doc_page is not None:
            current_doc_page += 1
            doc_page = current_doc_page
        else:
            doc_page = physical_page

        for line_text in page_lines:
            lines.append({"text": line_text, "page": doc_page})
    return lines


def build_sections(page_chunks: list[dict]) -> list[dict]:
    sections: list[dict] = []
    current_heading = PREFACE_LABEL
    current_lines: list[dict] = []
    in_noise_section = False

    def flush_section() -> None:
        if not current_lines:
            return

        content_lines = [line["text"] for line in current_lines]
        section_text = "\n".join(content_lines).strip()
        if not section_text:
            return

        sections.append(
            {
                "heading": current_heading,
                "text": section_text,
                "fragments": _build_fragment_spans(current_lines),
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


def _build_fragment_spans(lines: list[dict]) -> list[dict]:
    spans: list[dict] = []
    cursor = 0
    for index, line in enumerate(lines):
        start = cursor
        end = start + len(line["text"])
        spans.append({"page": line["page"], "start": start, "end": end})
        cursor = end
        if index < len(lines) - 1:
            cursor += 1
    return spans


def locate_chunk(section_text: str, chunk_text: str, search_start: int) -> tuple[int, int]:
    start = section_text.find(chunk_text, search_start)
    if start == -1 and search_start > 0:
        start = section_text.find(chunk_text)
    if start == -1:
        raise ValueError("Chunk tidak bisa dipetakan kembali ke section asal.")
    return start, start + len(chunk_text)


def resolve_page_range(fragments: list[dict], chunk_start: int, chunk_end: int) -> dict:
    touched_pages = [
        fragment["page"]
        for fragment in fragments
        if fragment["end"] > chunk_start and fragment["start"] < chunk_end
    ]
    if not touched_pages:
        raise ValueError("Chunk tidak memiliki halaman asal.")
    return {"start": min(touched_pages), "end": max(touched_pages)}


def _find_first_arabic_page_idx(page_chunks: list[dict]) -> int:
    for i, page in enumerate(page_chunks):
        for line in page.get("text", "").splitlines():
            if DOC_PAGE_PATTERN.match(line):
                return i
    return 0


def build_sections_from_ranges(
    page_chunks: list[dict],
    bab_ranges: list[dict],
    toc_page_idx: int = 0,
) -> list[dict]:
    # Halaman dari TOC page sampai penanda angka pertama — pakai heading detection
    # (halaman cover sebelum TOC dilewati)
    first_arabic_idx = _find_first_arabic_page_idx(page_chunks)
    pre_start = min(toc_page_idx, first_arabic_idx)
    pre_sections = build_sections(page_chunks[pre_start:first_arabic_idx]) if first_arabic_idx > pre_start else []

    # Lapis 1: page-based range dari TOC → titik awal heading per page
    page_to_heading: dict[int, str] = {}
    for r in bab_ranges:
        for page in range(r["page_start"], r["page_end"] + 1):
            page_to_heading[page] = r["heading"]

    # Lapis 2: lookup normalized heading → original heading string dari bab_ranges,
    # untuk mendeteksi transisi heading di dalam page yang sama.
    # Kasus: konten BAB A dan awal BAB B berada di page yang sama — page_to_heading
    # mengirim seluruh page ke satu heading, padahal perlu dipotong lebih halus.
    bab_heading_lookup: dict[str, str] = {
        normalize_heading(r["heading"]).upper(): r["heading"]
        for r in bab_ranges
    }
    # Lapis 2 hanya memicu switch jika salah satu dari dua kondisi terpenuhi:
    # (1) halaman saat ini sudah mencapai atau melewati halaman ekspektasi dari daftar isi, ATAU
    # (2) peta halaman lapisan 1 memang menetapkan halaman ini ke bagian yang sama.
    # Kondisi (1) memanfaatkan fakta bahwa nomor halaman dokumen sinkron dengan daftar isi.
    # Kondisi (2) menjadi jaring pengaman jika ada selisih kecil antara nomor halaman.
    bab_expected_page: dict[str, int] = {
        normalize_heading(r["heading"]).upper(): r["page_start"]
        for r in bab_ranges
    }

    heading_lines: dict[str, list[dict]] = {r["heading"]: [] for r in bab_ranges}

    # current_heading: heading yang sedang aktif, diperbarui saat heading bab_ranges
    # ditemukan di dalam konten (bukan reset per page).
    # page_to_heading hanya dipakai sebagai bootstrap saat current_heading belum diset.
    current_heading: str | None = None

    for line in iter_page_lines(page_chunks[first_arabic_idx:]):
        stripped = line["text"].strip()
        heading_match = HEADING_PATTERN.match(stripped)

        if heading_match:
            raw = heading_match.group(2)
            normalized = normalize_heading(raw).upper()
            if normalized in bab_heading_lookup:
                target_heading = bab_heading_lookup[normalized]
                expected_page = bab_expected_page.get(normalized, 0)
                sudah_di_zona = line["page"] >= expected_page
                lapisan1_setuju = page_to_heading.get(line["page"]) == target_heading
                if sudah_di_zona or lapisan1_setuju:
                    current_heading = target_heading
                    heading_lines[current_heading].append(line)
                    continue

        # Bootstrap: gunakan page_to_heading hanya jika current_heading belum diset
        if current_heading is None:
            current_heading = page_to_heading.get(line["page"])

        if current_heading and current_heading in heading_lines:
            heading_lines[current_heading].append(line)

    main_sections: list[dict] = []
    for r in bab_ranges:
        heading = r["heading"]
        lines = heading_lines[heading]
        if not lines:
            continue

        content_lines = [line["text"] for line in lines]
        section_text = "\n".join(content_lines).strip()
        if not section_text:
            continue

        main_sections.append({"heading": heading, "text": section_text, "fragments": _build_fragment_spans(lines)})

    return pre_sections + main_sections


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
