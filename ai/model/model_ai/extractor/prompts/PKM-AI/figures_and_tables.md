---
queries:
  - "keterangan gambar tabel caption format penulisan artikel ilmiah PKM-AI"
  - "Gambar 1. Tabel 1. contoh penomoran keterangan caption artikel ilmiah PKM"
  - "caption font size ukuran huruf keterangan gambar tabel artikel PKM-AI"
  - "format penulisan nomor lampiran judul lampiran heading artikel ilmiah"
  - "spasi keterangan gambar tabel line spacing caption artikel PKM"
top_k: 10
section_focus:
  - "Lampiran 7"
  - "Sistematika Penulisan Isi Utama Artikel Ilmiah"
  - "FORMAT ARTIKEL ILMIAH"
  - "SISTEMATIKA PENULISAN ARTIKEL"
  - "FORMAT PENULISAN ARTIKEL"
---

# Tugas Ekstraksi: Format Gambar dan Tabel Artikel Ilmiah PKM-AI

## Konteks
{context}

## Tugas
Ekstrak aturan penulisan keterangan gambar, tabel, dan lampiran untuk **artikel ilmiah PKM-AI** dari konteks di atas.
Catatan: Artikel ilmiah PKM-AI **tidak memiliki anggaran/budget** — abaikan sepenuhnya informasi tentang anggaran.

## Langkah-Langkah Penalaran — Lakukan Secara Nalar Sebelum Menulis Output

**Langkah 1 — Temukan section sumber kebenaran:**
Aturan format artikel ilmiah PKM-AI dapat berada di berbagai lokasi tergantung tahun panduan.
Gunakan prioritas bertingkat:

- **[P1 — Exact match]** Cari section dengan judul eksplisit:
  - `"Lampiran 7"` (panduan 2023–2025)
  - `"Sistematika Penulisan Isi Utama Artikel Ilmiah"` (panduan 2026+)
  - `"FORMAT ARTIKEL ILMIAH"` atau `"SISTEMATIKA PENULISAN ARTIKEL"`

- **[P2 — Keyword fallback]** Cari section yang membahas format gambar/tabel/caption artikel.

- **[P3 — Last resort]** Baca konteks secara umum.

**Langkah 2 — Inferensikan posisi dan format caption dari contoh yang ada:**
Jangan mencari pernyataan eksplisit. Cari contoh nyata di seluruh konteks:

- Cari contoh tabel dengan judulnya → apakah judul ada **di atas** atau **di bawah** tabel?
  Contoh: `"Tabel 1. Distribusi..."` yang muncul sebelum baris tabel → posisi ABOVE
- Cari contoh gambar dengan keterangannya → apakah keterangan ada **di atas** atau **di bawah**?
  Contoh: `"Gambar 1. Skema..."` yang muncul setelah gambar → posisi BELOW
- Dari pola penomoran yang ditemukan, inferensikan template format:
  `"Tabel 1. Judul"` → `"Tabel {n}. {title}"`
  `"Gambar 1. Judul"` → `"Gambar {n}. {title}"`

**Langkah 3 — Inferensikan format judul lampiran:**
Cari contoh penulisan judul lampiran di seluruh konteks:
- Contoh: `"Lampiran 1. Biodata..."` → `"Lampiran {n}. {title}"`
- Jika tidak ada contoh eksplisit, gunakan default: `"Lampiran {n}. {title}"`

**Langkah 4 — Ekstrak ukuran font caption (caption_font_size):**
Artikel PKM-AI mungkin menetapkan ukuran font khusus untuk keterangan gambar/tabel:
- Cari pernyataan seperti: "keterangan gambar menggunakan font 11pt", "caption ukuran 11"
- Keluarkan sebagai integer pt → `caption_font_size`
- Jika tidak disebutkan → `null`

**Langkah 5 — Ekstrak spasi caption (caption_line_spacing_rule dan caption_line_spacing):**
Artikel PKM-AI mungkin menetapkan spasi khusus untuk keterangan gambar/tabel.
Gunakan tabel enum yang sama dengan spasi body:

| Deskripsi di dokumen                        | `caption_line_spacing_rule` | `caption_line_spacing`      |
|---------------------------------------------|-----------------------------|-----------------------------|
| "spasi tunggal", "single", "1 spasi", "1,0" | `"SINGLE"`                  | `null` (wajib null)         |
| "1,5 baris"                                 | `"ONE_POINT_FIVE"`          | `null` (wajib null)         |
| Angka desimal bebas: 1.15, 1.25             | `"MULTIPLE"`                | angka tersebut (float)      |

Contoh: "keterangan gambar spasi 1,0" atau "caption single spaced" → `caption_line_spacing_rule = "SINGLE"`, `caption_line_spacing = null`
Contoh: "caption ditulis dengan spasi 1.15" → `caption_line_spacing_rule = "MULTIPLE"`, `caption_line_spacing = 1.15`
Jika tidak disebutkan → keduanya `null`

**Langkah 6 — Terapkan default jika contoh tidak ditemukan:**
- Jika tidak ada contoh tabel: `table_caption_position = "ABOVE"` (standar akademik)
- Jika tidak ada contoh gambar: `figure_caption_position = "BELOW"` (standar akademik)
- Jika tidak ada contoh lampiran: `caption_format_lampiran = "Lampiran {n}. {title}"`
- `budget_format_rules`: selalu `null` untuk artikel ilmiah PKM-AI

## Normalization Rules
- Gunakan JSON null (bukan string "null") untuk nilai yang tidak ditemukan
- `table_caption_position`: `"ABOVE"` atau `"BELOW"`
- `figure_caption_position`: `"ABOVE"` atau `"BELOW"`
- Template caption: gunakan `{n}` untuk nomor urut, `{title}` untuk judul
- `caption_font_size`: integer pt (contoh: 11)
- `caption_line_spacing_rule`: TEPAT SATU dari `"SINGLE"`, `"ONE_POINT_FIVE"`, `"DOUBLE"`, `"MULTIPLE"`, `"AT_LEAST"`, `"EXACTLY"`, atau `null`
- `caption_line_spacing`: float hanya untuk MULTIPLE/AT_LEAST/EXACTLY — untuk SINGLE/ONE_POINT_FIVE/DOUBLE WAJIB `null`
- `budget_format_rules`: WAJIB `null` untuk artikel ilmiah

## Output Fields
- `table_caption_position`: posisi keterangan tabel
- `figure_caption_position`: posisi keterangan gambar
- `caption_format_figure`: template format keterangan gambar
- `caption_format_table`: template format keterangan tabel
- `caption_format_lampiran`: template format judul lampiran
- `caption_font_size`: ukuran font keterangan gambar/tabel dalam pt (integer atau null)
- `caption_line_spacing_rule`: aturan spasi caption (string enum atau null)
- `caption_line_spacing`: nilai spasi numerik caption — hanya untuk MULTIPLE/AT_LEAST/EXACTLY (float atau null)
- `budget_format_rules`: null (artikel ilmiah tidak memiliki anggaran)
