---
queries:
  - "penomoran halaman romawi kecil arab sudut kanan atas bawah mulai dari halaman berapa"
  - "format nomor sub bab BAB 1 BAB 2 penomoran bab chapter"
  - "penomoran gambar Gambar 1 Gambar 2 tabel Tabel 1 format nomor keterangan"
top_k: 8
---

# Extraction Task: Numbering

## Context
{context}

## Task
Ekstrak informasi sistem penomoran halaman, bab, gambar, dan tabel dari konteks di atas.
Jika tidak ditemukan, gunakan null (JSON null, BUKAN string "null").

## Normalization Rules
- Gunakan JSON null (bukan string "null") untuk nilai yang tidak ditemukan
- sub_chapter_format: gunakan format PERSIS seperti yang tertulis di dokumen (contoh: jika dokumen pakai "4.1, 4.2" maka output "4.1, 4.2, dst." — jangan ganti dengan "1.1, 1.2" kecuali dokumen memang menyebutkan itu)
- figure_numbering_format dan table_numbering_format: kutip contoh persis dari dokumen
- Jika format tidak konsisten di dokumen, catat format yang lebih umum/representatif

## Output Fields
- preliminary_page_format: format nomor halaman awal (contoh: "Romawi kecil (i, ii, iii, ...)")
- preliminary_page_position: posisi nomor halaman awal (contoh: "Sudut kanan bawah")
- preliminary_page_start_from: mulai dari halaman mana penomoran awal (contoh: "Daftar Isi (halaman i)")
- content_page_format: format nomor halaman isi (contoh: "Angka Arab (1, 2, 3, ...)")
- content_page_position: posisi nomor halaman isi (contoh: "Sudut kanan atas")
- content_page_start_from: mulai dari halaman mana penomoran isi dimulai
- chapter_numbering_format: format penomoran BAB (contoh: "BAB 1, BAB 2, BAB 3, ...")
- sub_chapter_format: format sub-bab persis seperti di dokumen (contoh: "4.1, 4.2, dst.")
- figure_numbering_format: format penomoran gambar persis seperti di dokumen
- table_numbering_format: format penomoran tabel persis seperti di dokumen
