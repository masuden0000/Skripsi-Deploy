---
queries:
  - "rekapitulasi rencana anggaran biaya persentase jenis pengeluaran sumber dana PKM"
  - "sistematika proposal PKM biaya jadwal anggaran belmawa persentase maksimum"
  - "pengeluaran bahan habis pakai peralatan penunjang perjalanan lainnya persentase"
  - "contoh tabel keterangan judul nomor caption format penulisan PKM"
  - "Gambar 1. Tabel 4.1 contoh penomoran keterangan gambar tabel dalam dokumen"
top_k: 10
section_focus:
  - "SISTEMATIKA PENULISAN PROPOSAL"
  - "SISTEMATIKA PROPOSAL KEGIATAN"
---

# Tugas Ekstraksi: Format Gambar, Tabel, dan Anggaran Biaya

## Konteks
{context}

## Tugas
Ekstrak aturan penulisan keterangan gambar, keterangan tabel, dan format anggaran biaya
dari konteks di atas.

## Langkah-Langkah Penalaran — Lakukan Secara Nalar Sebelum Menulis Output

**Langkah 1 — Temukan section sumber kebenaran untuk anggaran:**
Cari section sistematika proposal dengan prioritas:

- **[P1 — Exact match]** Cari section berjudul persis:
  - `"Sistematika Proposal Kegiatan"`, atau
  - `"Sistematika Penulisan Proposal"`
  → Gunakan sebagai sumber utama untuk budget format rules.

- **[P2 — Keyword fallback]** Jika tidak ada, cari section yang mengandung kata
  `"sistematika"` DAN `"proposal"`.

- **[P3 — Last resort]** Jika P1 dan P2 kosong, baca konteks secara umum.

**Langkah 2 — Ekstrak budget format rules dari section yang ditemukan di Langkah 1:**
Dalam section sistematika, cari bagian yang membahas anggaran/biaya:
- Identifikasi setiap jenis pengeluaran yang disebutkan
- Catat persentase maksimum per jenis jika ada (contoh: "maksimum 60%", "maks 15%")
- Catat semua opsi sumber dana (Belmawa, PT, Instansi Lain, dll)

**Langkah 3 — Inferensikan posisi dan format caption dari contoh yang ada:**
Jangan mencari pernyataan eksplisit. Cari contoh nyata di seluruh konteks:

- Cari contoh tabel dengan judulnya → apakah judul ada **di atas** atau **di bawah** tabel?
  Contoh: `"Tabel 4.1. Rekapitulasi..."` yang muncul sebelum baris tabel → posisi ABOVE
- Cari contoh gambar dengan keterangannya → apakah keterangan ada **di atas** atau **di bawah**?
  Contoh: `"Gambar 1. Skema alur..."` yang muncul setelah gambar → posisi BELOW
- Dari pola penomoran yang ditemukan, inferensikan template format:
  `"Tabel 4.1. Judul"` → `"Tabel {bab}.{n} {title}"`
  `"Gambar 1. Judul"` → `"Gambar {n}. {title}"`

**Langkah 4 — Terapkan default jika contoh tidak ditemukan:**
- Jika tidak ada contoh tabel: `table_caption_position = "ABOVE"` (standar akademik)
- Jika tidak ada contoh gambar: `figure_caption_position = "BELOW"` (standar akademik)

## Normalization Rules
- Gunakan JSON null (bukan string "null") untuk nilai yang tidak ditemukan
- `table_caption_position`: `"ABOVE"` atau `"BELOW"`
- `figure_caption_position`: `"ABOVE"` atau `"BELOW"`
- Template caption: gunakan `{n}` untuk nomor urut, `{bab}` untuk nomor bab,
  `{title}` untuk judul, `{source}` untuk sumber

## Output Fields
- `table_caption_position`: posisi keterangan tabel
- `figure_caption_position`: posisi keterangan gambar
- `caption_format_figure`: template format keterangan gambar
- `caption_format_table`: template format keterangan tabel
- `budget_format_rules`:
  - `budget_items`: array `{jenis_pengeluaran, persentase_maksimum, contoh}`
  - `sumber_dana_options`: array string opsi sumber dana
  - `additional_rules`: aturan tambahan atau null