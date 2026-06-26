"""Mengekstrak daftar isi dari page_chunks untuk menentukan rentang halaman tiap BAB. Posisi pipeline: pdf_extractor → toc_extractor → chunk_builder."""
import re
from pathlib import Path
from typing import Optional

from model_ai.shared import TOC_SECTION_DENYLIST

TOC_HEADING_VARIANTS = [
    "DAFTAR ISI",
    "DAFTAR",
    "TABLE OF CONTENTS",
    "CONTENTS",
    "ISI",
    "DAFTAR HALAMAN",
]

TOC_PAGE_LIMIT = 3

_ENTRY_WITH_DOTS = re.compile(r"^(.+?)\s*\.{4,}\s*(\d+)\s*$")
_ENTRY_NO_DOTS = re.compile(r"^(.+?)\s{4,}(\d+)\s*$")
_SUBBAB_PREFIX = re.compile(r"^(?:[A-Z]\.|[a-z]\.|[IVXLC]{1,5}\.|[0-9]+\.|Lampiran\s+\d+\.)[|\s]+")


def _strip_markdown(line: str) -> str:
    line = re.sub(r"<[^>]+>", " ", line)
    line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
    line = re.sub(r"__(.*?)__", r"\1", line)
    line = re.sub(r"^#{1,6}\s+", "", line)
    return " ".join(line.split())


def _strip_table_cell(line: str) -> str:
    return re.sub(r"^\||\|$", "", line).strip()


def _is_toc_heading(line: str) -> bool:
    normalized = _strip_markdown(line).upper()
    if normalized in TOC_SECTION_DENYLIST:
        return False
    return normalized in TOC_HEADING_VARIANTS


def find_toc_page(page_chunks: list[dict]) -> tuple[Optional[dict], int]:
    for i, page in enumerate(page_chunks[:TOC_PAGE_LIMIT]):
        text = page.get("text", "")
        for line in text.splitlines():
            if _is_toc_heading(line):
                return page, i
    return None, 0


def _is_subbab(heading: str) -> bool:
    return bool(_SUBBAB_PREFIX.match(heading))


def _parse_entries_with_dots(toc_text: str) -> list[tuple[str, int]]:
    entries: list[tuple[str, int]] = []
    for line in toc_text.splitlines():
        line = _strip_table_cell(line)
        
        # Cek apakah line ini hasil squashed (banyak entri digabung dalam 1 baris)
        # Karakteristiknya: punya banyak titik-titik (....) dan sangat panjang
        if line.count("....") > 1 and len(line) > 150:
            # Ekstrak berulang kali. Regex ini mencari teks yang TIDAK mengandung "....",
            # lalu diikuti oleh "...." dan angka (halaman).
            for match in re.finditer(r"((?:(?!\.{4,}).)+?)\s*\.{4,}\s*(\d+)", line):
                heading = _strip_markdown(match.group(1)).strip()
                # Buang sisa angka romawi halaman sebelumnya yang menempel di awal teks
                heading = re.sub(r"^(?:[ivxlcdmIVXLCDM]+)\s+", "", heading)
                heading = re.sub(r"^[a-zA-Z]\s+", "", heading) # Buang huruf tunggal
                
                if not _is_subbab(heading) and heading:
                    entries.append((heading, int(match.group(2))))
            continue

        match = _ENTRY_WITH_DOTS.match(line)
        if match:
            heading = _strip_markdown(match.group(1))
            if not _is_subbab(heading):
                entries.append((heading, int(match.group(2))))
    return entries


def _parse_entries_no_dots(toc_text: str) -> list[tuple[str, int]]:
    entries: list[tuple[str, int]] = []
    for line in toc_text.splitlines():
        line = _strip_table_cell(line)
        match = _ENTRY_NO_DOTS.match(line)
        if match:
            heading = _strip_markdown(match.group(1))
            if not _is_subbab(heading):
                entries.append((heading, int(match.group(2))))
    return entries


def _parse_entries_table(toc_text: str) -> list[tuple[str, int]]:
    """Parse daftar isi berformat tabel markdown: `|Heading|8|`."""
    entries: list[tuple[str, int]] = []
    for line in toc_text.splitlines():
        line = line.strip()
        
        # Cek apakah ini squashed table (banyak kolom/tabel digabung dalam 1 baris)
        # Karakteristiknya: punya banyak simbol pipa '|' dan sangat panjang
        if line.count("|") > 4 and len(line) > 150:
            # Cari pola | Teks | Angka | berulang kali di dalam baris
            for match in re.finditer(r"\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|", line):
                heading = _strip_markdown(match.group(1)).strip()
                if not heading or _is_subbab(heading):
                    continue
                entries.append((heading, int(match.group(2))))
            continue
            
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        page_raw = cells[-1]
        if not page_raw.isdigit():
            continue
        heading = _strip_markdown(cells[0])
        if not heading or _is_subbab(heading):
            continue
        entries.append((heading, int(page_raw)))
    return entries


def _extract_from_native_toc(pdf_path: Path) -> Optional[list[dict]]:
    """Baca TOC langsung dari metadata PDF (bookmark/outline) via PyMuPDF.

    Ini OS-independent — tidak bergantung pada font rendering — sehingga hasilnya
    konsisten antara Windows dan Linux. Gunakan sebagai jalur primer sebelum text parsing.
    """
    try:
        import pymupdf  # sudah tersedia sebagai dependency pymupdf4llm
        doc = pymupdf.open(str(pdf_path))
        raw_toc = doc.get_toc()
        doc.close()
    except Exception as e:
        print(f"[toc] Native TOC tidak tersedia: {e}. Fallback ke text parsing.")
        return None

    if not raw_toc:
        return None

    entries: list[tuple[str, int]] = []
    for item in raw_toc:
        if len(item) < 3:
            continue
        level, title, page = item[0], str(item[1]).strip(), item[2]
        if level != 1:
            continue  # skip sub-bab
        title = _strip_markdown(title)
        if not title or _is_subbab(title):
            continue
        entries.append((title, page))

    if not entries:
        return None

    return _build_ranges(entries)


def _build_ranges(entries: list[tuple[str, int]]) -> list[dict]:
    ranges = []
    for i, (heading, start_page) in enumerate(entries):
        end_page = entries[i + 1][1] - 1 if i + 1 < len(entries) else 9999
        ranges.append({"heading": heading, "page_start": start_page, "page_end": end_page})
    return ranges


def extract_bab_ranges(
    page_chunks: list[dict],
    pdf_path: Optional[Path] = None,
) -> tuple[Optional[list[dict]], str, int]:
    """Kembalikan (bab_ranges, jalur, toc_page_idx).

    jalur:
      'native'        — TOC dari metadata PDF (bookmark) — OS-independent, paling reliable
      'main'          — halaman TOC ditemukan + titik-titik berhasil diparsing
      'fallback_2a'   — halaman TOC ditemukan tapi tanpa titik-titik (spasi lebar)
      'fallback_2b'   — halaman TOC ditemukan tapi format tabel markdown (`|heading|page|`)
      'fallback_total'— halaman TOC tidak ditemukan atau tidak ada entri yang valid
    toc_page_idx: 0-indexed posisi fisik halaman TOC (0 jika tidak ditemukan)
    """
    # Jalur primer: baca TOC dari metadata PDF langsung (OS-independent)
    if pdf_path is not None:
        native_ranges = _extract_from_native_toc(pdf_path)
        if native_ranges:
            print(f"[toc] Native TOC berhasil: {len(native_ranges)} entri BAB ditemukan")
            return native_ranges, "native", 0

    toc_page, toc_page_idx = find_toc_page(page_chunks)
    if toc_page is None:
        return None, "fallback_total", 0

    toc_text = toc_page.get("text", "")

    if re.search(r"\.{4,}", toc_text):
        entries = _parse_entries_with_dots(toc_text)
        if entries:
            return _build_ranges(entries), "main", toc_page_idx

    entries = _parse_entries_no_dots(toc_text)
    if entries:
        return _build_ranges(entries), "fallback_2a", toc_page_idx

    entries = _parse_entries_table(toc_text)
    if entries:
        return _build_ranges(entries), "fallback_2b", toc_page_idx

    return None, "fallback_total", toc_page_idx
