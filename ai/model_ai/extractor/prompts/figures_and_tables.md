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
- table_caption_position: "ABOVE" jika keterangan di atas tabel, "BELOW" jika di bawah
- figure_caption_position: "ABOVE" jika keterangan di atas gambar, "BELOW" jika di bawah
- Untuk template caption, gunakan placeholder {n} untuk nomor urut, {bab} untuk nomor bab, {title} untuk judul, {source} untuk sumber
- max_width_constraint: "within_margins" jika gambar/tabel tidak boleh melebihi batas margin

## Output Fields
- table_caption_position: posisi keterangan tabel — "ABOVE" atau "BELOW"
- figure_caption_position: posisi keterangan gambar — "ABOVE" atau "BELOW"
- caption_format_figure: template format keterangan gambar (contoh: "Gambar {n}. {title} ({source})")
- caption_format_table: template format keterangan tabel (contoh: "Tabel {bab}.{n} {title}")
- source_required_if_not_own: apakah sumber wajib dicantumkan jika bukan karya sendiri (bool)
- max_width_constraint: batasan lebar gambar/tabel (contoh: "within_margins")
