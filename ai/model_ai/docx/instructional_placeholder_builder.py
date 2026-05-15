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

        system_prompt = (
            "Anda adalah asisten penyusun instructional placeholder untuk template "
            "proposal akademik PKM.\n\n"
            "ATURAN PERMANEN:\n"
            "- Gunakan hanya informasi dari sumber yang diberikan.\n"
            "- Jangan tambah informasi baru di luar sumber.\n"
            "- Kalimat tentang margin, font, ukuran huruf, spasi baris, nomor halaman "
            "DILARANG muncul di instruksi akhir.\n"
            "- Jangan gunakan bullet list di instruksi akhir.\n"
            "- Output instruksi adalah plain text saja, tanpa markdown."
        )

        human_prompt = (
            f"Section target: {display_title}\n\n"
            "Ikuti langkah-langkah berikut secara berurutan sebelum menulis output akhir.\n\n"
            "LANGKAH 1 — KLASIFIKASI SUMBER\n"
            "Baca setiap kalimat penting dari sumber. Tandai masing-masing sebagai:\n"
            "  [KONTEN] → aturan atau panduan yang spesifik untuk section ini\n"
            "             (apa yang harus ditulis, batasan isi, struktur argumen)\n"
            "  [FORMAT GLOBAL] → aturan yang berlaku untuk seluruh dokumen\n"
            "                    (margin, font, ukuran huruf, spasi baris, nomor halaman)\n"
            "  [TIDAK RELEVAN] → informasi yang tidak berkaitan dengan section ini\n\n"
            "LANGKAH 2 — FILTER\n"
            "Buang semua kalimat berlabel [FORMAT GLOBAL] dan [TIDAK RELEVAN].\n"
            "Lanjutkan hanya dengan kalimat berlabel [KONTEN].\n\n"
            "LANGKAH 3 — TULIS INSTRUKSI\n"
            "Dari hasil filter, tulis 4 sampai 6 kalimat instruksi dalam Bahasa Indonesia.\n"
            "Wajib memuat:\n"
            "  1. Tujuan utama section ini.\n"
            "  2. Konten spesifik yang wajib ada.\n"
            "  3. Batasan atau aturan isi yang relevan (bukan format dokumen).\n"
            "  4. Arahan konkret kepada penulis tentang cara menyusun isi.\n\n"
            "FORMAT OUTPUT (wajib diikuti):\n"
            "<analisis>\n"
            "[hasil LANGKAH 1 dan 2]\n"
            "</analisis>\n"
            "<instruksi>\n"
            "[hasil LANGKAH 3 — plain text saja]\n"
            "</instruksi>\n\n"
            f"Sumber:\n{context}"
        )

        result = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)])
        text = str(result.content)

        match = re.search(r"<instruksi>(.*?)</instruksi>", text, re.DOTALL)
        if match:
            return " ".join(match.group(1).strip().split())
        return " ".join(text.split()) or None
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
