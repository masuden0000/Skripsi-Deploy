"""Membentuk potongan teks (chunk) dari hasil ekstraksi halaman untuk keperluan RAG. Posisi pipeline: pdf_extractor → chunk_builder → supabase_ingest."""
import re

from langchain_text_splitters import MarkdownTextSplitter

PREFACE_LABEL = "PREFACE"
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
BOLD_HEADING_PATTERN = re.compile(r"^\*\*(.+?)\*\*$")
BOLD_HEADING_PREFIX_PATTERN = re.compile(r"^\*\*(.+?)\*\*")
DOC_PAGE_PATTERN = re.compile(r"^\s*(\d{1,3})\s*$")
ROMAN_PAGE_PATTERN = re.compile(r"^\s*(x{0,2}(?:ix|iv|v?i{0,3}))\s*$", re.IGNORECASE)
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
        found_roman: bool = False
        for line in text.splitlines():
            doc_page_match = DOC_PAGE_PATTERN.match(line)
            if doc_page_match:
                found_doc_page = int(doc_page_match.group(1))
                continue
            if ROMAN_PAGE_PATTERN.match(line):
                found_roman = True
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
            doc_page: int | None = found_doc_page
            current_doc_page = found_doc_page
        elif found_roman:
            doc_page = None
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

        # Deteksi bold-only heading (**teks**) — PDF panduan sering menggunakan bold
        # untuk judul section tanpa markdown heading marker.
        if not heading_match:
            bold_match = BOLD_HEADING_PATTERN.match(stripped_line)
            if bold_match:
                raw_heading = bold_match.group(1)
                # Baris tabel yang di-strip outer '|' oleh iter_page_lines meninggalkan
                # '|' di dalam raw_heading. Ini konten, bukan section heading.
                if "|" in raw_heading:
                    pass
                elif is_noise_heading(raw_heading):
                    in_noise_section = True
                    continue
                else:
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
    valid_pages = [p for p in touched_pages if p is not None]
    if not valid_pages:
        return {"start": None, "end": None}
    return {"start": min(valid_pages), "end": max(valid_pages)}


def _find_first_arabic_page_idx(page_chunks: list[dict]) -> int:
    for i, page in enumerate(page_chunks):
        for line in page.get("text", "").splitlines():
            if DOC_PAGE_PATTERN.match(line):
                return i
    return 0


def _detect_page_offset(page_chunks: list[dict], bab_ranges: list[dict], scan_start: int) -> int:
    """Deteksi offset antara nomor halaman iter_page_lines dan nomor dokumen dari TOC.
    Mengembalikan (physical_page - toc_doc_page), atau 0 jika tidak terdeteksi.
    Digunakan saat DOC_PAGE_PATTERN tidak mendeteksi angka halaman embedded di PDF."""
    bab_headings = {normalize_heading(r["heading"]).upper(): r["page_start"] for r in bab_ranges}
    for line in iter_page_lines(page_chunks[scan_start:]):
        if line["page"] is None:
            continue
        stripped = line["text"].strip()
        heading_match = HEADING_PATTERN.match(stripped)
        if heading_match:
            norm = normalize_heading(heading_match.group(2)).upper()
            if norm in bab_headings:
                return line["page"] - bab_headings[norm]
        bold_match = BOLD_HEADING_PATTERN.match(stripped)
        if bold_match:
            norm = normalize_heading(bold_match.group(1)).upper()
            if norm in bab_headings:
                return line["page"] - bab_headings[norm]
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

    # Deteksi offset antara physical page dan document page dari TOC.
    # Terjadi saat PDF tidak menyematkan page numbers sebagai baris standalone,
    # sehingga iter_page_lines() fallback ke physical_page (cover dihitung sebagai halaman 1)
    # sedangkan TOC mencatat document page (mulai dari 1 setelah halaman romawi).
    scan_start_idx = max(first_arabic_idx, toc_page_idx + 1)
    page_offset = _detect_page_offset(page_chunks, bab_ranges, scan_start_idx)
    if page_offset != 0:
        print(f"[chunk_builder] Page offset terdeteksi: +{page_offset}. Menyesuaikan rentang halaman TOC.")
        bab_ranges = [
            {
                "heading": r["heading"],
                "page_start": r["page_start"] + page_offset,
                "page_end": r["page_end"] + page_offset if r["page_end"] != 9999 else 9999,
            }
            for r in bab_ranges
        ]

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
    # (1) halaman saat ini tepat sama dengan halaman ekspektasi dari daftar isi, ATAU
    # (2) peta halaman lapisan 1 memang menetapkan halaman ini ke bagian yang sama.
    # Kondisi (1) menggunakan kecocokan tepat (==) agar heading yang muncul lebih awal
    # di halaman lain (misalnya sebagai deskripsi sistematika) tidak salah diaktifkan.
    # Kondisi (2) menjadi jaring pengaman untuk kasus di mana halaman sinkron dengan TOC.
    bab_expected_page: dict[str, int] = {
        normalize_heading(r["heading"]).upper(): r["page_start"]
        for r in bab_ranges
    }
    bab_heading_end_page: dict[str, int] = {
        normalize_heading(r["heading"]).upper(): r["page_end"]
        for r in bab_ranges
    }

    heading_lines: dict[str, list[dict]] = {r["heading"]: [] for r in bab_ranges}

    # Pre-scan: temukan halaman yang memiliki TOC heading detectable (via Layer 2 / 2b).
    # Digunakan oleh page-transition fallback untuk memutuskan apakah perlu buffer +1.
    # Halaman yang punya heading detectable dibiarkan ditangani Layer 2 (bukan fallback).
    heading_transition_pages: set[int] = set()
    for _line in iter_page_lines(page_chunks[first_arabic_idx:]):
        if _line["page"] is None:
            continue
        _stripped = _line["text"].strip()
        _hm = HEADING_PATTERN.match(_stripped)
        if _hm:
            _norm = normalize_heading(_hm.group(2)).upper()
            if _norm in bab_heading_lookup:
                heading_transition_pages.add(_line["page"])
        else:
            _bm = BOLD_HEADING_PATTERN.match(_stripped)
            if _bm:
                _norm = normalize_heading(_bm.group(1)).upper()
                if _norm in bab_heading_lookup:
                    heading_transition_pages.add(_line["page"])

    # current_heading: heading yang sedang aktif, diperbarui saat heading bab_ranges
    # ditemukan di dalam konten (bukan reset per page).
    # page_to_heading hanya dipakai sebagai bootstrap saat current_heading belum diset.
    current_heading: str | None = None

    for line in iter_page_lines(page_chunks[first_arabic_idx:]):
        if line["page"] is None:
            continue
        stripped = line["text"].strip()
        heading_match = HEADING_PATTERN.match(stripped)

        if heading_match:
            raw = heading_match.group(2)
            normalized = normalize_heading(raw).upper()
            if normalized in bab_heading_lookup:
                target_heading = bab_heading_lookup[normalized]
                expected_page = bab_expected_page.get(normalized, 0)
                sudah_di_zona = line["page"] == expected_page
                lapisan1_setuju = page_to_heading.get(line["page"]) == target_heading
                if sudah_di_zona or lapisan1_setuju:
                    current_heading = target_heading
                    heading_lines[current_heading].append(line)
                    continue

        # Lapis 2b: bold-only heading (**teks**) yang cocok dengan entri TOC.
        # Menangani kasus PDF merender heading sebagai bold text, bukan markdown #,
        # sehingga HEADING_PATTERN tidak mendeteksinya. Syarat keamanan sama dengan
        # Lapis 2: hanya aktif jika halaman sesuai ekspektasi TOC atau lapisan 1 setuju.
        if not heading_match:
            bold_match = BOLD_HEADING_PATTERN.match(stripped)
            if bold_match:
                raw = bold_match.group(1)
                normalized = normalize_heading(raw).upper()
                if normalized in bab_heading_lookup:
                    target_heading = bab_heading_lookup[normalized]
                    expected_page = bab_expected_page.get(normalized, 0)
                    sudah_di_zona = line["page"] == expected_page
                    lapisan1_setuju = page_to_heading.get(line["page"]) == target_heading
                    if sudah_di_zona or lapisan1_setuju:
                        current_heading = target_heading
                        heading_lines[current_heading].append(line)
                        continue

        # Lapis 2c: **TOC_HEADING prefix** di awal baris (baris tidak harus seluruhnya bold).
        # Menangani kasus konten lampiran yang diawali **LAMPIRAN Lampiran N. ...** tanpa
        # heading markdown #. Menggunakan toleransi ±1 halaman dari ekspektasi TOC karena
        # TOC sering mencatat page start 1 halaman setelah konten sesungguhnya dimulai.
        if not heading_match:
            prefix_match = BOLD_HEADING_PREFIX_PATTERN.match(stripped)
            if prefix_match:
                raw_pfx = prefix_match.group(1)
                normalized_pfx = normalize_heading(raw_pfx).upper()
                _lapis2c_found = False
                for norm_key, target_heading in bab_heading_lookup.items():
                    after_key = normalized_pfx[len(norm_key):]
                    if normalized_pfx.startswith(norm_key) and (not after_key or after_key[0] in " \t."):
                        expected_page = bab_expected_page.get(norm_key, 0)
                        if abs(line["page"] - expected_page) <= 1:
                            current_heading = target_heading
                            heading_lines[current_heading].append(line)
                            _lapis2c_found = True
                            break
                if _lapis2c_found:
                    continue

        # Bootstrap: gunakan page_to_heading hanya jika current_heading belum diset
        if current_heading is None:
            current_heading = page_to_heading.get(line["page"])
        elif current_heading:
            # Page-transition fallback: jika halaman saat ini sudah melewati akhir
            # rentang section aktif, pindah ke section berikutnya dari page_to_heading.
            #
            # Threshold: jika halaman boundary (current_end + 1) memiliki TOC heading
            # detectable (ada di heading_transition_pages), fallback diberi buffer +1
            # sehingga Layer 2 yang menangani transisi dan pre-heading content tetap masuk
            # ke section sebelumnya. Jika boundary page tidak punya heading detectable
            # (misal LAMPIRAN yang konten lampirannya tidak pakai ## heading), fallback
            # langsung aktif di halaman boundary agar section tidak terlambat 1 halaman.
            normalized_current = normalize_heading(current_heading).upper()
            current_end = bab_heading_end_page.get(normalized_current, 9999)
            boundary_page = current_end + 1
            has_heading_on_boundary = boundary_page in heading_transition_pages
            threshold = current_end + 1 if has_heading_on_boundary else current_end
            if line["page"] > threshold:
                new_heading = page_to_heading.get(line["page"])
                if new_heading and new_heading in heading_lines:
                    current_heading = new_heading

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

    result = pre_sections + main_sections
    if not result:
        # Nomor halaman TOC (document page) tidak cocok dengan nomor halaman yang terdeteksi
        # oleh iter_page_lines (physical page). Seluruh konten tidak ter-assign ke section manapun.
        # Fallback ke HEADING_PATTERN agar pipeline tetap menghasilkan chunk yang dapat digunakan.
        print(
            "[chunk_builder] WARNING: 0 section dihasilkan dari bab_ranges. "
            "Kemungkinan page numbering TOC tidak cocok dengan embedded page markers. "
            "Fallback ke build_sections (HEADING_PATTERN)."
        )
        return build_sections(page_chunks)
    return result


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
