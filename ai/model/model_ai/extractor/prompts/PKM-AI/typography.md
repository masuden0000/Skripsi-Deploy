---
queries:
  - "font huruf ukuran tipografi judul penulis abstrak artikel ilmiah Times New Roman"
  - "ukuran font body text artikel PKM-AI pt ketentuan penulisan"
  - "judul artikel cetak tebal bold huruf kapital Times New Roman ukuran"
  - "nama penulis font size ukuran huruf artikel ilmiah"
  - "abstrak abstract font size ukuran huruf artikel ilmiah PKM"
section_focus:
  - "Lampiran 7"
  - "Sistematika Penulisan Isi Utama Artikel Ilmiah"
  - "FORMAT ARTIKEL ILMIAH"
  - "SISTEMATIKA PENULISAN ARTIKEL"
  - "FORMAT PENULISAN ARTIKEL"
---

# Tugas Ekstraksi: Tipografi Artikel Ilmiah PKM-AI

## Konteks
{context}

## Tugas
Ekstrak informasi tipografi untuk **artikel ilmiah PKM-AI** dari konteks di atas.
Jangan gunakan pengetahuan umum — hanya berdasarkan konteks yang diberikan.

## Langkah-Langkah Penalaran — Lakukan Langkah Ini Secara Nalar Sebelum Menulis Output

**Langkah 1 — Temukan section sumber kebenaran:**
Aturan format artikel ilmiah PKM-AI dapat berada di berbagai lokasi tergantung tahun panduan.
Gunakan prioritas bertingkat:

- **[P1 — Exact match]** Cari section dengan judul eksplisit seperti:
  - `"Lampiran 7"` (panduan 2023–2025)
  - `"Sistematika Penulisan Isi Utama Artikel Ilmiah"` (panduan 2026+)
  - `"FORMAT ARTIKEL ILMIAH"` atau `"SISTEMATIKA PENULISAN ARTIKEL"`
  → Jika ditemukan, gunakan section itu sebagai sumber utama.

- **[P2 — Keyword fallback]** Jika tidak ada, cari section yang membahas kombinasi dari:
  ukuran font artikel, jenis huruf (Times New Roman), format penulisan artikel ilmiah.

- **[P3 — Last resort]** Jika P1 dan P2 tidak menghasilkan apapun, baca konteks secara umum.

**Langkah 2 — Ekstrak font keluarga (font_family):**
Cari pernyataan eksplisit tentang jenis/nama font yang digunakan:
- "Times New Roman", "Arial", "Calibri", dsb. → `font_family`
Jika tidak disebutkan → `null`.

**Langkah 3 — Ekstrak ukuran font body (font_size_body_pt):**
Cari pernyataan tentang ukuran font untuk isi/body artikel (teks paragraf utama):
- Contoh: "teks artikel menggunakan ukuran 12", "body text 12pt" → `font_size_body_pt = 12`
Artikel ilmiah PKM-AI umumnya menggunakan body 12pt — tetapi ambil hanya dari konteks.

**Langkah 4 — Ekstrak ukuran font per elemen (khusus PKM-AI):**
Artikel PKM-AI memiliki hierarki ukuran font berbeda untuk setiap elemen di halaman pertama.
Cari pernyataan yang MEMBEDAKAN ukuran font untuk:
- **Judul artikel** (`font_size_title_pt`): font untuk judul di baris paling atas artikel.
  Contoh: "judul artikel... Times New Roman ukuran 12", "title font 12pt"
- **Nama penulis** (`font_size_author_pt`): font untuk baris nama penulis/author.
  Contoh: "nama penulis ukuran 10", "author name 10pt"
- **Abstrak** (`font_size_abstract_pt`): font untuk paragraf abstrak.
  Contoh: "abstrak ditulis dengan ukuran 11", "abstract 11pt"

Jika elemen tidak disebutkan secara terpisah → `null` untuk elemen tersebut.

**Langkah 5 — Terapkan default jika tidak ditemukan:**
- `font_family` tidak disebutkan → `null`
- `font_size_body_pt` tidak disebutkan → `null`
- `font_size_heading_pt` tidak disebutkan, tapi `font_size_body_pt` ada → sama dengan `font_size_body_pt`
- Semua field per elemen yang tidak disebutkan → `null`

## Normalization Rules
- Gunakan JSON null (bukan string "null") untuk nilai yang tidak ditemukan
- Semua `font_size_*_pt`: integer dalam pt (contoh: 12)

## Output Fields
- `font_family`: nama font utama dokumen (contoh: `"Times New Roman"`)
- `font_size_body_pt`: ukuran font body/paragraf dalam pt (integer)
- `font_size_heading_pt`: ukuran font heading dalam pt (integer) — untuk artikel: sama dengan body jika tidak disebutkan berbeda
- `font_size_title_pt`: ukuran font judul artikel di halaman pertama (integer atau null)
- `font_size_author_pt`: ukuran font nama penulis (integer atau null)
- `font_size_abstract_pt`: ukuran font teks abstrak (integer atau null)
