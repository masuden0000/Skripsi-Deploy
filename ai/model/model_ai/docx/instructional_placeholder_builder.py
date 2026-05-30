"""Menyusun instructional placeholder per section DOCX dari chunk panduan berbasis LLM. Posisi pipeline: metadata_repository → instructional_placeholder_builder → generator."""
import re
import time
from pathlib import Path
from typing import Iterable

from model_ai.extractor.doc_extractor import _build_llm, CONFIG, MAX_RATE_LIMIT_WAIT
from model_ai.shared import BATCH_PAUSE_EVERY as _PLACEHOLDER_PAUSE_EVERY, BATCH_PAUSE_SECONDS as _PLACEHOLDER_PAUSE_SECONDS
from model_ai.docx.chunk_loader import ChunkSource, match_sources_for_section
from model_ai.extractor.models import DocumentMetadata, SectionItem

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_SYSTEM_PROMPT: str | None = None
_HUMAN_PROMPT_TEMPLATE: str | None = None


def _load_prompt(filename: str) -> str:
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8").strip()


def _get_system_prompt() -> str:
    global _SYSTEM_PROMPT
    if _SYSTEM_PROMPT is None:
        _SYSTEM_PROMPT = _load_prompt("placeholder_system.md")
    return _SYSTEM_PROMPT


def _get_human_prompt_template() -> str:
    global _HUMAN_PROMPT_TEMPLATE
    if _HUMAN_PROMPT_TEMPLATE is None:
        _HUMAN_PROMPT_TEMPLATE = _load_prompt("placeholder_human.md")
    return _HUMAN_PROMPT_TEMPLATE


def make_instruction_key(
    section_type: str,
    title: str,
    number: int | None = None,
) -> str:
    normalized_title = " ".join((title or "").strip().upper().split())
    if section_type == "bab":
        return f"bab::{number or 0}::{normalized_title}"
    return f"{section_type}::{normalized_title}"


def build_instructional_placeholder_map(
    metadata: DocumentMetadata,
    chunks: list[ChunkSource],
    use_llm: bool = True,
) -> dict[str, str]:
    placeholders: dict[str, str] = {}
    structure = metadata.document_structure_proposal
    if structure is None:
        return placeholders

    chapter_fmt = (metadata.numbering.chapter_format if metadata.numbering else None) or "BAB {n}"

    llm_call_count = 0
    total_sections = len(structure.sections)

    for section_idx, section in enumerate(structure.sections, start=1):
        if use_llm:
            section_label = section.title or section.type
            print(f"[placeholder] ({section_idx}/{total_sections}) Generate placeholder: {section_label}...", flush=True)
        if section.type == "bab":
            title = section.title or "[JUDUL_BAB_BELUM_TERDETEKSI]"
            heading_text = _make_bab_heading(section, chapter_fmt)
            key = make_instruction_key("bab", heading_text, number=section.number)
            sources = match_sources_for_section(
                chunks=chunks,
                section_label=f"BAB {section.number}" if section.number else "BAB",
                section_title=title,
            )
            placeholders[key] = _build_instruction_text(
                display_title=heading_text,
                sources=sources,
                use_llm=use_llm,
                fallback_hint=f"jelaskan isi utama untuk bagian {heading_text.lower()}",
            )
        elif section.type in {"daftar_pustaka", "lampiran", "daftar_isi", "daftar_gambar", "daftar_tabel", "daftar_lampiran"}:
            title = (section.title or section.type.upper().replace("_", " ")).strip()
            key = make_instruction_key(section.type, title)
            sources = _match_named_section_sources(chunks, title)
            placeholders[key] = _build_instruction_text(
                display_title=title,
                sources=sources,
                use_llm=use_llm,
                fallback_hint=f"isi bagian {title.lower()} sesuai fungsi dan urutan yang diwajibkan panduan",
            )
        elif section.type == "sub_bab":
            sub_num = section.sub_number or "?"
            title = section.title or "[SUB_BAB_TANPA_JUDUL]"
            heading_text = f"{sub_num} {title}".strip()
            key = make_instruction_key("sub_bab", heading_text)
            sources = _match_named_section_sources(chunks, title)
            if not sources:
                bab_num = str(sub_num).split(".")[0] if "." in str(sub_num) else str(sub_num)
                sources = match_sources_for_section(
                    chunks=chunks,
                    section_label=f"BAB {bab_num}",
                    section_title=title,
                )
            placeholders[key] = _build_instruction_text(
                display_title=heading_text,
                sources=sources,
                use_llm=use_llm,
                fallback_hint=(
                    f"uraikan secara detail isi {heading_text.lower()} — jelaskan konten yang harus ada, "
                    "format yang digunakan, batasan yang berlaku, dan contoh relevan sesuai panduan"
                ),
            )
        elif section.type == "item_lampiran":
            lampiran_number = section.lampiran_number or "Lampiran ?"
            title = section.title or "[LAMPIRAN_TANPA_JUDUL]"
            heading_text = f"{lampiran_number}. {title}".strip()
            key = make_instruction_key("item_lampiran", heading_text)
            sources = _match_named_section_sources(chunks, title)
            if not sources:
                sources = _match_named_section_sources(chunks, lampiran_number)
            fallback_hint = _get_lampiran_fallback_hint(title, lampiran_number)
            placeholders[key] = _build_instruction_text(
                display_title=heading_text,
                sources=sources,
                use_llm=use_llm,
                fallback_hint=fallback_hint,
            )

        if use_llm:
            llm_call_count += 1
            if (
                llm_call_count % _PLACEHOLDER_PAUSE_EVERY == 0
                and llm_call_count < total_sections
            ):
                print(
                    f"[placeholder] {llm_call_count}/{total_sections} section selesai. "
                    f"Jeda {_PLACEHOLDER_PAUSE_SECONDS} detik untuk mengurangi risiko rate limit..."
                )
                time.sleep(_PLACEHOLDER_PAUSE_SECONDS)

    return placeholders


def _make_bab_heading(section: SectionItem, chapter_fmt: str = "BAB {n}") -> str:
    title = section.title or "[JUDUL_BAB_BELUM_TERDETEKSI]"
    if section.number:
        bab_label = chapter_fmt.replace("{n}", str(section.number))
    else:
        bab_label = "BAB"
    return f"{bab_label} {title}".strip()


def _match_named_section_sources(chunks: list[ChunkSource], title: str) -> list[ChunkSource]:
    return match_sources_for_section(
        chunks=chunks,
        section_label=title,
        section_title=title,
    )


def _get_lampiran_fallback_hint(title: str, lampiran_number: str) -> str:
    """Kembalikan hint fallback kontekstual berdasarkan judul lampiran."""
    t = title.upper()
    if "BIODATA" in t:
        return (
            "cantumkan biodata lengkap ketua tim, setiap anggota, dan dosen pendamping meliputi "
            "nama lengkap, NIM/NIP, program studi, perguruan tinggi, nomor telepon, email, "
            "dan tanda tangan asli (basah)"
        )
    if "JUSTIFIKASI" in t and "ANGGARAN" in t:
        return (
            "rincikan setiap pos pengeluaran beserta volume, harga satuan, dan total biaya "
            "dalam format tabel; pastikan subtotal tiap jenis pengeluaran tidak melebihi "
            "persentase maksimum yang ditetapkan panduan"
        )
    if "SUSUNAN TIM" in t or "PEMBAGIAN TUGAS" in t:
        return (
            "cantumkan nama, NIM, program studi, bidang ilmu, alokasi waktu dalam jam per minggu, "
            "dan uraian tugas spesifik masing-masing anggota tim pengusul"
        )
    if "SURAT PERNYATAAN" in t:
        return (
            "isi surat pernyataan ketua tim yang menyatakan keaslian karya, bebas plagiarisme, "
            "dan kesanggupan menyelesaikan program; sertakan tanda tangan asli dan materai sesuai ketentuan"
        )
    if "GAMBARAN TEKNOLOGI" in t or ("TEKNOLOGI" in t and "KEMBANG" in t):
        return (
            "uraikan spesifikasi teknis, prinsip kerja, keunggulan, dan perbedaan teknologi yang "
            "dikembangkan dibandingkan produk atau solusi yang sudah ada sebelumnya; "
            "sertakan gambar skema atau diagram jika diperlukan"
        )
    return (
        f"lengkapi isi {lampiran_number} sesuai ketentuan panduan; "
        "pastikan format, kelengkapan data, dan urutan dokumen memenuhi syarat yang ditetapkan"
    )


def _build_instruction_text(
    display_title: str,
    sources: list[ChunkSource],
    use_llm: bool,
    fallback_hint: str,
) -> str:
    if use_llm and sources:
        result = _build_instruction_text_with_llm(display_title, sources)
        if result:
            return result
    return fallback_hint


def _build_instruction_text_with_llm(display_title: str, sources: list[ChunkSource]) -> str | None:
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        context = "\n\n---\n\n".join(
            f"Header: {source.chunk_parent}\nHalaman: {source.page_start}-{source.page_end}\nIsi:\n{_clean_source_text(source.content)}"
            for source in sources[:6]
        )

        system_prompt = _get_system_prompt()
        human_prompt = _get_human_prompt_template().format(
            display_title=display_title,
            context=context,
        )

        llm = _build_llm()
        max_retries = 5
        for attempt in range(max_retries):
            try:
                result = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)])
                break
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "rate_limit_exceeded" in err_str:
                    wait_match = re.search(r"try again in (\d+)m(\d+(?:\.\d+)?)s", err_str)
                    if wait_match:
                        wait_secs = int(wait_match.group(1)) * 60 + float(wait_match.group(2)) + 5
                    else:
                        wait_secs = 60 * (2 ** attempt)
                    wait_secs = min(wait_secs, MAX_RATE_LIMIT_WAIT)

                    if not CONFIG._groq_exhausted:
                        if len(CONFIG.groq_api_keys) > 1:
                            CONFIG.rotate_groq_key()
                            print(f"[placeholder] Rate limit hit. Rotasi ke Groq key berikutnya (percobaan {attempt + 1}/{max_retries})...")
                        else:
                            CONFIG._groq_exhausted = True
                            print(f"[placeholder] Rate limit hit. Semua Groq key exhausted, switch ke Gemini (percobaan {attempt + 1}/{max_retries})...")
                    else:
                        if len(CONFIG.google_api_keys) > 1:
                            CONFIG.rotate_google_key()
                        print(f"[placeholder] Rate limit hit pada Gemini. Menunggu {wait_secs:.0f} detik (percobaan {attempt + 1}/{max_retries})...")
                        time.sleep(wait_secs)

                    llm = _build_llm()
                else:
                    raise
        else:
            print(f"[placeholder] Gagal setelah {max_retries} percobaan untuk '{display_title}'.")
            return None

        text = str(result.content)
        match = re.search(r"##MULAI##\s*(.*?)\s*##SELESAI##", text, re.DOTALL)
        if match:
            return " ".join(match.group(1).strip().split())
        text = re.sub(r"##MULAI##|##SELESAI##", "", text)
        return " ".join(text.strip().split()) or None
    except Exception as exc:
        print(f"[placeholder] LLM gagal untuk '{display_title}': {type(exc).__name__}: {exc}")
        return None


def _clean_source_text(text: str) -> str:
    cleaned = re.sub(r"#+\s*", "", text)
    cleaned = cleaned.replace("**", "").replace("__", "").replace("_", "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()
