"""
Fungsi: Menyusun instructional placeholder per section DOCX dari chunk panduan.

Digunakan oleh: model_ai/docx/generator.py; tests/docx/test_docx_generator.py

Tujuan: Mengisi template DOCX dengan instruksi kontekstual per bagian agar placeholder
tidak kosong dan tetap selaras dengan sumber chunk panduan.
"""
import re
from typing import Iterable

from model_ai.config import get_config
from model_ai.docx.chunk_loader import ChunkSource, match_sources_for_section
from model_ai.extractor.models import DocumentMetadata, SectionItem


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/docx/generator.py; model_ai/docx/docx_renderer.py
# Menjalankan fungsi `make_instruction_key` sebagai bagian alur `instructional_placeholder_builder`.
# ---------------------------------------------------------------------------
def make_instruction_key(
    section_type: str,
    title: str,
    number: int | None = None,
) -> str:
    normalized_title = " ".join((title or "").strip().upper().split())
    if section_type == "bab":
        return f"bab::{number or 0}::{normalized_title}"
    return f"{section_type}::{normalized_title}"


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/docx/generator.py
# Menjalankan fungsi `build_instructional_placeholder_map` sebagai bagian alur `instructional_placeholder_builder`.
# ---------------------------------------------------------------------------
def build_instructional_placeholder_map(
    metadata: DocumentMetadata,
    chunks: list[ChunkSource],
    use_llm: bool = True,
) -> dict[str, str]:
    placeholders: dict[str, str] = {}
    structure = metadata.document_structure_proposal

    if structure.halaman_sampul:
        title = "HALAMAN SAMPUL"
        key = make_instruction_key("halaman_sampul", title)
        placeholders[key] = _build_instruction_text(
            display_title=title,
            sources=[],
            use_llm=False,
            fallback_hint=(
                "cantumkan judul proposal, identitas tim, institusi, dan informasi dokumen "
                "secara ringkas sesuai format sampul panduan"
            ),
        )
    if structure.halaman_pengesahan:
        title = "HALAMAN PENGESAHAN"
        key = make_instruction_key("halaman_pengesahan", title)
        placeholders[key] = _build_instruction_text(
            display_title=title,
            sources=[],
            use_llm=False,
            fallback_hint=(
                "cantumkan identitas proposal, pihak yang mengesahkan, serta ruang tanda "
                "tangan sesuai ketentuan panduan"
            ),
        )
    if structure.ringkasan:
        title = "RINGKASAN"
        key = make_instruction_key("ringkasan", title)
        sources = _match_named_section_sources(chunks, title)
        placeholders[key] = _build_instruction_text(
            display_title=title,
            sources=sources,
            use_llm=use_llm,
            fallback_hint="ringkas inti masalah, solusi/prototipe, dan manfaat utama program",
        )

    for section in structure.sections:
        if section.type == "bab":
            title = section.title or "[JUDUL_BAB_BELUM_TERDETEKSI]"
            heading_text = _make_bab_heading(section)
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

    return placeholders


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_make_bab_heading` sebagai bagian alur `instructional_placeholder_builder`.
# ---------------------------------------------------------------------------
def _make_bab_heading(section: SectionItem) -> str:
    title = section.title or "[JUDUL_BAB_BELUM_TERDETEKSI]"
    bab_number = f"BAB {section.number}" if section.number else "BAB"
    return f"{bab_number} {title}".strip()


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_match_named_section_sources` sebagai bagian alur `instructional_placeholder_builder`.
# ---------------------------------------------------------------------------
def _match_named_section_sources(chunks: list[ChunkSource], title: str) -> list[ChunkSource]:
    return match_sources_for_section(
        chunks=chunks,
        section_label=title,
        section_title=title,
    )


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_build_instruction_text` sebagai bagian alur `instructional_placeholder_builder`.
# ---------------------------------------------------------------------------
def _build_instruction_text(
    display_title: str,
    sources: list[ChunkSource],
    use_llm: bool,
    fallback_hint: str,
) -> str:
    if use_llm and sources:
        llm_text = _build_instruction_text_with_llm(display_title, sources)
        if llm_text:
            return llm_text
    return _build_instruction_text_fallback(display_title, sources, fallback_hint)


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_build_instruction_text_with_llm` sebagai bagian alur `instructional_placeholder_builder`.
# ---------------------------------------------------------------------------
def _build_instruction_text_with_llm(display_title: str, sources: list[ChunkSource]) -> str | None:
    try:
        # Lazy import supaya mode fallback tetap jalan walau dependency LLM tidak terpasang.
        from langchain_groq import ChatGroq

        config = get_config()
        config.disable_blackhole_proxies()
        llm = ChatGroq(
            model=config.model_name,
            api_key=config.groq_api_key.get_secret_value(),
            temperature=0,
        )
        context = "\n\n---\n\n".join(
            f"Header: {source.chunk_parent}\nHalaman: {source.page_start}-{source.page_end}\nIsi:\n{_clean_source_text(source.content)}"
            for source in sources[:6]
        )
        prompt = (
            "Anda menyusun instructional placeholder untuk template proposal.\n"
            f"Section target: {display_title}\n\n"
            "Tulis 2 sampai 4 kalimat instruksi dalam Bahasa Indonesia.\n"
            "Wajib memuat:\n"
            "1. tujuan atau fokus isi bagian ini,\n"
            "2. aturan khusus yang benar-benar disebut pada sumber jika ada,\n"
            "3. arahan singkat tentang apa yang harus diisi penulis.\n\n"
            "Aturan keras:\n"
            "- Gunakan hanya informasi dari sumber.\n"
            "- Jangan menambah informasi baru di luar sumber.\n"
            "- Jangan gunakan bullet list.\n"
            "- Keluarkan plain text saja.\n\n"
            f"Sumber:\n{context}"
        )
        result = llm.invoke(prompt)
        text = " ".join(str(result.content).split())
        return text or None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_build_instruction_text_fallback` sebagai bagian alur `instructional_placeholder_builder`.
# ---------------------------------------------------------------------------
def _build_instruction_text_fallback(
    display_title: str,
    sources: list[ChunkSource],
    fallback_hint: str,
) -> str:
    if not sources:
        return (
            f"Instruksi pengisian untuk {display_title}: bagian ini dipakai untuk {fallback_hint}. "
            "Lengkapi isi final sesuai struktur panduan yang berlaku."
        )

    cleaned_blocks = [_clean_source_text(source.content) for source in sources]
    purpose = _pick_purpose_sentence(cleaned_blocks) or fallback_hint
    rule_lines = _pick_rule_lines(cleaned_blocks)

    instruction = (
        f"Instruksi pengisian untuk {display_title}: bagian ini dipakai untuk {purpose}. "
        "Isi bagian dengan uraian yang langsung mendukung fokus tersebut."
    )
    if rule_lines:
        instruction += " Aturan terkait dari panduan: " + " ".join(rule_lines[:2])
    else:
        instruction += " Pada potongan sumber yang cocok tidak ditemukan aturan teknis yang lebih spesifik."
    return " ".join(instruction.split())


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_clean_source_text` sebagai bagian alur `instructional_placeholder_builder`.
# ---------------------------------------------------------------------------
def _clean_source_text(text: str) -> str:
    # Hilangkan heading markdown dan marker dekoratif agar kalimat inti lebih mudah dipakai.
    cleaned = re.sub(r"#+\s*", "", text)
    cleaned = cleaned.replace("**", "").replace("__", "").replace("_", "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_pick_purpose_sentence` sebagai bagian alur `instructional_placeholder_builder`.
# ---------------------------------------------------------------------------
def _pick_purpose_sentence(blocks: Iterable[str]) -> str | None:
    for block in blocks:
        for sentence in re.split(r"(?<=[.!?])\s+", block):
            candidate = sentence.strip(" -:;")
            if len(candidate) < 20:
                continue
            if candidate.upper() == candidate and len(candidate.split()) <= 6:
                continue
            return candidate
    return None


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_pick_rule_lines` sebagai bagian alur `instructional_placeholder_builder`.
# ---------------------------------------------------------------------------
def _pick_rule_lines(blocks: Iterable[str]) -> list[str]:
    matches: list[str] = []
    rule_pattern = re.compile(
        r"\b(wajib|harus|tidak boleh|ditulis|maksimal|maks\.?|ukuran|margin|spasi|judul)\b",
        re.IGNORECASE,
    )
    for block in blocks:
        for sentence in re.split(r"(?<=[.!?])\s+", block):
            candidate = sentence.strip(" -:;")
            if len(candidate) < 12:
                continue
            if not rule_pattern.search(candidate):
                continue
            if candidate not in matches:
                matches.append(candidate)
            if len(matches) >= 3:
                return matches
    return matches
