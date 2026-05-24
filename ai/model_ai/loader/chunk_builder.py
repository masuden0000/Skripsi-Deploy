"""
Fungsi: Bangun chunks dari markdown hasil PDF extraction dengan grouping berbasis section.
Digunakan oleh: model_ai/loader/pdf_extractor.py
Tujuan: Memecah dokumen PDF menjadi chunks terstruktur yang siap di-index untuk RAG.
Keyword: automated document generation
"""
import re

from langchain_text_splitters import MarkdownTextSplitter

PREFACE_LABEL = "PREFACE"
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
DOC_PAGE_PATTERN = re.compile(r"^\s*(\d{1,3})\s*$")
STRIKETHROUGH_PATTERN = re.compile(r"~~[^~]*~~")


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
    if len(plain) <= 3 and plain.replace(" ", "").isupper():
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


def _extract_valid_headings_from_toc(lines: list[dict]) -> set[str]:
    in_toc = False
    headings: set[str] = set()

    for line in lines:
        text = line["text"].strip()
        if not text:
            continue

        heading_match = HEADING_PATTERN.match(text)
        if heading_match:
            normalized = normalize_heading(heading_match.group(2))
            if normalized.upper() == "DAFTAR ISI":
                in_toc = True
                headings.add(normalized)
            elif in_toc:
                break
            continue

        if not in_toc:
            continue

        lower = text.lower()
        if "picture" in lower or "start of picture" in lower or "end of picture" in lower:
            continue

        if text.startswith("|"):
            if re.match(r"^\|[-|\s]+\|?$", text):
                continue
            cells = [c.strip() for c in text.strip("|").split("|") if c.strip()]
            if len(cells) == 2 and re.match(r"^[A-Za-z]\.$|^\d+\.$", cells[0]):
                continue
            raw_text = " ".join(cells)
        else:
            if re.match(r"^[A-Za-z]\.\s|^\d+\.\s", text):
                continue
            raw_text = text

        cleaned = re.sub(r"\s*\.{2,}.*$", "", raw_text).strip()
        cleaned = re.sub(r"\s+[ivxlcdmIVXLCDM\d]+\s*$", "", cleaned).strip()

        if cleaned:
            headings.add(normalize_heading(cleaned))

    print(f"[TOC DEBUG] valid_headings ({len(headings)}): {sorted(headings)}")
    return headings


def build_sections(page_chunks: list[dict]) -> list[dict]:
    sections: list[dict] = []
    current_heading = PREFACE_LABEL
    current_lines: list[dict] = []
    in_noise_section = False

    all_lines = iter_page_lines(page_chunks)
    valid_headings = _extract_valid_headings_from_toc(all_lines)

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

    for line in all_lines:
        stripped_line = line["text"].strip()
        heading_match = HEADING_PATTERN.match(stripped_line)

        if heading_match:
            raw_heading = heading_match.group(2)
            normalized = normalize_heading(raw_heading)
            in_noise = is_noise_heading(raw_heading)

            if in_noise:
                in_noise_section = True
            else:
                in_noise_section = False
                if valid_headings and normalized not in valid_headings:
                    in_noise_section = True

            if not in_noise_section or not valid_headings:
                flush_section()
                current_heading = normalized
                current_lines = []

        if not in_noise_section or not valid_headings:
            current_lines.append(line)

    flush_section()
    return sections


def _build_fragments(sections: list[dict]) -> list[dict]:
    fragments: list[dict] = []
    chunk_index = 0
    for section in sections:
        section_heading = section.get("heading") or PREFACE_LABEL
        text = section.get("text", "")
        section_fragments = section.get("fragments", [])

        sub_texts = MarkdownTextSplitter(chunk_size=500, chunk_overlap=50).split_text(text)
        for i, sub_text in enumerate(sub_texts):
            fragment_text = sub_text.strip()
            if not fragment_text:
                continue

            pages: set[int] = set()
            for f in section_fragments:
                f_start = f.get("start", 0)
                f_end = f.get("end", 0)
                f_text = text[f_start:f_end]
                if f_text in sub_text:
                    pages.add(f.get("page", 0))

            page_start = min(pages) if pages else 0
            page_end = max(pages) if pages else page_start

            fragments.append({
                "chunk_index": chunk_index,
                "chunk_parent": section_heading,
                "content": fragment_text,
                "page_start": page_start,
                "page_end": page_end,
            })
            chunk_index += 1

    return fragments


def build_chunks(page_chunks: list[dict]) -> list[dict]:
    sections = build_sections(page_chunks)
    return _build_fragments(sections)