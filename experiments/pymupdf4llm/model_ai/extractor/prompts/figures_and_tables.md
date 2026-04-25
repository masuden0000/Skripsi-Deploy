---
queries:
  - "penulisan keterangan gambar caption di bawah gambar format nomor sumber"
  - "penulisan keterangan tabel caption di atas tabel format nomor"
  - "gambar tabel lebar tidak melebihi batas margin kolom halaman constraint ukuran"
top_k: 8
---

# Extraction Task: Figures and Tables

## Context
{context}

## Task
Ekstrak aturan penulisan keterangan gambar dan tabel dari konteks di atas.
Jika tidak ditemukan dalam konteks, gunakan null (JSON null, BUKAN string "null").

## Normalization Rules
- Gunakan JSON null (bukan string "null") untuk nilai yang tidak ditemukan
- Nilai bool: true atau false (bukan string)
- Jika format caption tidak konsisten dalam dokumen (misalnya ada "Tabel 1." dan juga "Tabel 4.1"), catat format yang lebih representatif dan tambahkan catatan inkonsistensi, contoh: "Tabel [N]. [Judul] (inkonsisten: kadang Tabel [N.N])"
- max_width_constraint: cari aturan tentang lebar gambar/tabel tidak boleh melebihi margin atau ukuran tertentu

## Output Fields
- table_caption_position: posisi keterangan tabel (contoh: "Di atas tabel")
- figure_caption_position: posisi keterangan gambar (contoh: "Di bawah gambar")
- caption_format_figure: format keterangan gambar (contoh: "Gambar [N]. [Judul Gambar] ([Sumber jika ada])")
- caption_format_table: format keterangan tabel (contoh: "Tabel [N.N] [Judul Tabel]")
- source_required_if_not_own: apakah sumber wajib dicantumkan jika bukan karya sendiri (bool)
- max_width_constraint: batasan lebar gambar/tabel (contoh: "Tidak melebihi batas margin dokumen")
