---
queries:
  - "penulisan keterangan gambar caption di bawah gambar format nomor sumber"
  - "penulisan keterangan tabel caption di atas tabel format nomor"
  - "gambar tabel lebar tidak melebihi batas margin kolom halaman constraint ukuran"
  - "rekapitulasi rencana anggaran biaya persentase jenis pengeluaran sumber dana"
  - "Gambar 1. Gambar 4. contoh penomoran gambar dalam isi dokumen teks"
top_k: 10
---

# Extraction Task: Figures and Tables

## Context
{context}

## Task
Ekstrak aturan penulisan keterangan gambar, tabel, dan format anggaran biaya dari konteks di atas.
Jika tidak ditemukan dalam konteks, gunakan null (JSON null, BUKAN string "null").

## Normalization Rules
- Gunakan JSON null (bukan string "null") untuk nilai yang tidak ditemukan
- table_caption_position: "ABOVE" jika keterangan di atas tabel, "BELOW" jika di bawah — jika tidak disebutkan eksplisit, gunakan "ABOVE" sebagai default
- figure_caption_position: "ABOVE" jika keterangan di atas gambar, "BELOW" jika di bawah — jika tidak disebutkan eksplisit, gunakan "BELOW" sebagai default
- Untuk template caption, gunakan placeholder {n} untuk nomor urut, {bab} untuk nomor bab, {title} untuk judul, {source} untuk sumber
- max_width_constraint: "within_margins" jika gambar/tabel tidak boleh melebihi batas margin

## Budget Format Rules Extraction
Fokus pada REKAPITULASI RENCANA ANGGARAN BIAYA untuk ekstraksi:

1. **Identifikasi setiap jenis pengeluaran** yang ada dalam aturan
2. **Ekstrak persentase maksimum** jika disebutkan (contoh: "maksimum 60%", "maks 15%")
3. **Kumpulkan semua opsi sumber dana** (Belmawa, PT, Instansi Lain, dll)
4. **Ekstrak contoh** jika ada dalam teks (contoh: "bahan habis pakai seperti ATK, kertas")

### Budget Items Rules:
- budget_items: array of objects dengan fields:
  - jenis_pengeluaran: string (nama jenis pengeluaran)
  - persentase_maksimum: number (0-100) jika ada aturan persentase, null jika tidak ada
  - contoh: string opsional dengan contoh item
- sumber_dana_options: array of strings untuk semua opsi sumber dana
- additional_rules: string opsional untuk aturan tambahan

## Output Fields
- table_caption_position: posisi keterangan tabel — "ABOVE" atau "BELOW"
- figure_caption_position: posisi keterangan gambar — "ABOVE" atau "BELOW"
- caption_format_figure: template format keterangan gambar (contoh: "Gambar {n}. {title} ({source})") — **jika tidak dinyatakan eksplisit, inferensikan dari contoh gambar di konteks** (misal: "Gambar 1. Reaktor Pengolahan Limbah" → "Gambar {n}. {title}")
- caption_format_table: template format keterangan tabel (contoh: "Tabel {bab}.{n} {title}") — **jika tidak dinyatakan eksplisit, inferensikan dari contoh nama tabel di konteks** (misal: "Tabel 4.1. Format Rekapitulasi..." → "Tabel {bab}.{n} {title}")
- max_width_constraint: batasan lebar gambar/tabel (contoh: "within_margins")
- budget_format_rules: object dengan:
  - budget_items: array of {jenis_pengeluaran, persentase_maksimum, contoh}
  - sumber_dana_options: array of strings
  - additional_rules: string atau null
