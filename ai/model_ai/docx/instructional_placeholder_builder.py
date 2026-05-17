"""
Fungsi: Menyusun instructional placeholder per section DOCX dari chunk panduan.

Digunakan oleh: model_ai/docx/generator.py; tests/docx/test_docx_generator.py

Tujuan: Mengisi template DOCX dengan instruksi kontekstual per bagian agar placeholder
tidak kosong dan tetap selaras dengan sumber chunk panduan.
"""
import re
from typing import Iterable

from model_ai.extractor.doc_extractor import _build_llm
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

    chapter_fmt = metadata.numbering.chapter_format or "BAB {n}"

    for section in structure.sections:
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
            # Cari chunk dari judul sub_bab; jika tidak ada, perluas ke BAB induk
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
            # Cari chunk relevan dari judul lampiran, fallback ke nomor lampiran
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

    return placeholders


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_make_bab_heading` sebagai bagian alur `instructional_placeholder_builder`.
# ---------------------------------------------------------------------------
def _make_bab_heading(section: SectionItem, chapter_fmt: str = "BAB {n}") -> str:
    title = section.title or "[JUDUL_BAB_BELUM_TERDETEKSI]"
    if section.number:
        bab_label = chapter_fmt.replace("{n}", str(section.number))
    else:
        bab_label = "BAB"
    return f"{bab_label} {title}".strip()


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
# Digunakan oleh: build_instructional_placeholder_map
# Menjalankan fungsi `_get_lampiran_fallback_hint` sebagai bagian alur `instructional_placeholder_builder`.
# ---------------------------------------------------------------------------
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
    # Generic fallback kontekstual
    return (
        f"lengkapi isi {lampiran_number} sesuai ketentuan panduan; "
        "pastikan format, kelengkapan data, dan urutan dokumen memenuhi syarat yang ditetapkan"
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
        result = _build_instruction_text_with_llm(display_title, sources)
        if result:
            return result
    # Kembalikan fallback_hint mentah — tanpa pemrosesan regex tambahan
    return fallback_hint


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_build_instruction_text_with_llm` sebagai bagian alur `instructional_placeholder_builder`.
# ---------------------------------------------------------------------------
def _build_instruction_text_with_llm(display_title: str, sources: list[ChunkSource]) -> str | None:
    try:
        # Lazy import supaya mode fallback tetap jalan walau dependency LLM tidak terpasang.
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_groq import ChatGroq

        llm = _build_llm()
        context = "\n\n---\n\n".join(
            f"Header: {source.chunk_parent}\nHalaman: {source.page_start}-{source.page_end}\nIsi:\n{_clean_source_text(source.content)}"
            for source in sources[:6]
        )

        system_prompt = (
            "Anda adalah mentor PKM berpengalaman yang memandu tim mahasiswa menyusun proposal berkualitas tinggi. "
            "Tugas Anda adalah menulis panduan pengisian satu section proposal — bukan merangkum panduan, "
            "melainkan memberi arahan spesifik dan actionable seperti seorang pembimbing yang tahu persis "
            "apa yang membuat proposal lolos seleksi.\n\n"
            "ATURAN PERMANEN:\n"
            "- Tulis dalam sudut pandang langsung kepada penulis ('Uraikan...', 'Pastikan...', 'Jelaskan...').\n"
            "- Gunakan hanya informasi yang berasal dari sumber — jangan menambah informasi baru.\n"
            "- Aturan format dokumen seperti margin, font, ukuran huruf, spasi baris, dan nomor halaman "
            "DILARANG disebutkan.\n"
            "- Jangan gunakan bullet list, numbering, atau markdown.\n"
            "- Output akhir adalah plain text saja."
        )

        human_prompt = (
            f"Tulis panduan pengisian untuk section: {display_title}\n\n"
            "Sebelum menulis panduan, lakukan analisis internal berikut (tidak perlu ditampilkan):\n"
            "  1. Identifikasi kalimat-kalimat dari sumber yang benar-benar relevan untuk section ini "
            "(fokus pada apa yang harus DITULIS, bukan aturan format dokumen).\n"
            "  2. Abaikan kalimat yang membahas margin, font, spasi, atau ketentuan teknis penulisan global.\n"
            "  3. Dari kalimat relevan tersebut, sintesiskan — jangan hanya menyalin ulang.\n\n"
            "Kemudian tulis panduan pengisian dalam 4 sampai 5 kalimat yang:\n"
            "  - Dimulai dengan menjelaskan MENGAPA section ini penting dalam konteks penilaian proposal PKM.\n"
            "  - Menyebut secara konkret APA yang wajib ada (bukan sekadar 'isi sesuai panduan').\n"
            "  - Memberi arahan BAGAIMANA menyusunnya — alur logis, sudut pandang, atau struktur argumen.\n"
            "  - Menyebut jebakan atau kesalahan umum yang harus dihindari, jika dapat disimpulkan dari sumber.\n\n"
            "PENTING — FORMAT OUTPUT:\n"
            "Tulis hanya baris-baris panduan akhir. "
            "Awali dengan penanda ##MULAI## dan akhiri dengan ##SELESAI##. "
            "Jangan tampilkan proses analisis.\n\n"
            f"Sumber:\n{context}"
        )

        result = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)])
        text = str(result.content)

        match = re.search(r"##MULAI##\s*(.*?)\s*##SELESAI##", text, re.DOTALL)
        if match:
            return " ".join(match.group(1).strip().split())
        # Fallback: strip penanda jika ada tapi tidak berpasangan
        text = re.sub(r"##MULAI##|##SELESAI##", "", text)
        return " ".join(text.strip().split()) or None
    except Exception as exc:
        print(f"[instructional_placeholder] LLM gagal untuk '{display_title}': {type(exc).__name__}: {exc}")
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
