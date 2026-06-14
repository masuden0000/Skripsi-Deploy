---
queries:
  - "penomoran halaman artikel ilmiah PKM-AI letak sudut kanan atas bawah angka arab"
  - "nomor halaman artikel PKM format penomoran ketentuan penulisan"
  - "format penulisan bab sub bab artikel ilmiah PKM-AI angka arab"
  - "penomoran bab pendahuluan metodologi artikel ilmiah ketentuan"
top_k: 10
section_focus:
  - "Lampiran 7"
  - "Sistematika Penulisan Isi Utama Artikel Ilmiah"
  - "FORMAT ARTIKEL ILMIAH"
  - "SISTEMATIKA PENULISAN ARTIKEL"
  - "FORMAT PENULISAN ARTIKEL"
---

# Tugas Ekstraksi: Sistem Penomoran Artikel Ilmiah PKM-AI

## Konteks
{context}

## Tugas
Ekstrak sistem penomoran halaman dan format bab untuk **artikel ilmiah PKM-AI** dari konteks di atas.
Jangan gunakan pengetahuan umum — hanya berdasarkan konteks yang diberikan.

Catatan: Artikel ilmiah umumnya TIDAK memiliki halaman preliminari (romawi) seperti proposal.
Penomoran biasanya langsung menggunakan angka arab dari halaman pertama.

## Langkah-Langkah Penalaran — Lakukan Secara Nalar Sebelum Menulis Output

**Langkah 1 — Temukan section sumber kebenaran:**
Aturan format artikel ilmiah PKM-AI dapat berada di berbagai lokasi tergantung tahun panduan.
Gunakan prioritas bertingkat:

- **[P1 — Exact match]** Cari section dengan judul eksplisit:
  - `"Lampiran 7"` (panduan 2023–2025)
  - `"Sistematika Penulisan Isi Utama Artikel Ilmiah"` (panduan 2026+)
  - `"FORMAT ARTIKEL ILMIAH"` atau `"SISTEMATIKA PENULISAN ARTIKEL"`

- **[P2 — Keyword fallback]** Cari section yang membahas penomoran halaman atau format bab artikel.

- **[P3 — Last resort]** Baca konteks secara umum.

**Langkah 2 — Cari aturan penomoran halaman:**
Identifikasi aturan penomoran untuk artikel:
- Apakah ada halaman preliminari (romawi)? Artikel PKM-AI biasanya langsung angka arab.
- Format angka: arab (1, 2, 3), romawi kecil (i, ii), romawi besar (I, II)?
- Letak nomor halaman: header atau footer?
- Alignment: kanan, kiri, atau tengah?
- Mulai dari section mana?

Jika panduan tidak menyebut penomoran secara eksplisit → gunakan default (Langkah 4).

**Langkah 3 — Inferensikan format bab (chapter_format):**
Cari contoh heading BAB yang muncul di konteks atau pernyataan tentang format judul bab:
- "BAB 1", "BAB I", "1.", "1 " (tanpa prefix) → petakan ke template `{n}`
- Abstraksi pola menjadi template menggunakan `{n}` sebagai placeholder angka.

**Langkah 4 — Terapkan default jika tidak ditemukan:**
Artikel ilmiah PKM-AI biasanya tidak menggunakan format BAB seperti proposal.
Jika tidak ditemukan:
- `preliminary`: `null` (artikel tidak punya halaman preliminari romawi)
- `content`: decimal, FOOTER, CENTER, mulai dari `"judul_abstrak"`
- `chapter_format`: `"{n}."` (standar artikel: "1.", "2.", "3.")
- `sub_chapter_format`: `"{bab}.{sub}"` (standar artikel)

## Normalization Rules
- `format`: `"lowerRoman"` / `"upperRoman"` / `"decimal"`
- `location`: `"HEADER"` atau `"FOOTER"`
- `alignment`: `"RIGHT"`, `"LEFT"`, atau `"CENTER"`
- `start_at_section`: nama section valid untuk artikel: `"judul_abstrak"`, `"bab"`, `"daftar_pustaka"`
- Gunakan JSON null untuk nilai yang benar-benar tidak bisa diinferensikan

## Output Fields
- `preliminary`: `{format, location, alignment, start_at_section}` — halaman awal romawi (null jika tidak ada)
- `content`: `{format, location, alignment, start_at_section}` — halaman isi angka arab
- `chapter_format`: template format judul bab artikel (contoh: `"{n}."`)
- `sub_chapter_format`: template format sub-bab (contoh: `"{bab}.{sub}"`)
