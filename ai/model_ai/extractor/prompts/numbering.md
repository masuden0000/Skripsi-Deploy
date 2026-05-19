---
queries:
  - "penomoran halaman romawi kecil arab sudut kanan atas bawah mulai dari halaman berapa"
  - "format nomor sub bab BAB 1 BAB 2 penomoran bab chapter"
  - "penomoran gambar Gambar 1 Gambar 2 tabel Tabel 1 format nomor keterangan"
  - "Gambar 1. Gambar 4. contoh keterangan gambar dalam isi teks pendahuluan"
  - "4.1 4.2 sub bab Anggaran Biaya Jadwal Kegiatan penomoran format sub bab"
top_k: 10
---

# Extraction Task: Numbering

## Context
{context}

## Task
Ekstrak informasi sistem penomoran halaman, bab, gambar, dan tabel dari konteks di atas.
Jika tidak ditemukan, gunakan null (JSON null, BUKAN string "null").

## Normalization Rules
- format halaman: gunakan nilai standar Word — "lowerRoman" (i, ii, iii), "upperRoman" (I, II, III), "decimal" (1, 2, 3)
- location: "HEADER" jika nomor di atas halaman, "FOOTER" jika di bawah halaman
- alignment: "RIGHT" untuk sudut kanan, "LEFT" untuk sudut kiri, "CENTER" untuk tengah
- start_at_section: gunakan nama section yang sama persis dengan entries di `sections` list
- chapter_format: gunakan template dengan placeholder {n} (contoh: "BAB {n}.") — perhatikan titik setelah nomor jika dokumen menggunakannya
- sub_chapter_format: gunakan template dengan placeholder {bab} dan {sub} (contoh: "{bab}.{sub}") — inferensikan dari contoh sub-bab yang ada (misal: "4.1 Anggaran Biaya" → "{bab}.{sub}")
- figure_format: gunakan template dengan placeholder {n} (contoh: "Gambar {n}.") — inferensikan dari contoh keterangan gambar yang ada (misal: "Gambar 1. Reaktor..." → "Gambar {n}.")
- table_format: gunakan template (contoh: "Tabel {bab}.{n}") — inferensikan dari contoh nama tabel yang ada (misal: "Tabel 4.1. Format..." → "Tabel {bab}.{n}")

**PENTING**: Jika aturan penomoran tidak dinyatakan secara eksplisit, **wajib inferensikan** dari contoh-contoh penomoran yang muncul dalam konteks. Dokumen akademik Indonesia umumnya menggunakan format "BAB {n}." untuk bab, "{bab}.{sub}" untuk sub-bab, "Gambar {n}." untuk gambar, dan "Tabel {bab}.{n}" untuk tabel.

## Output Fields
Keluarkan dua objek: `preliminary` (halaman awal/romawi) dan `content` (halaman isi/arab).
Setiap objek memiliki:
- format: format angka halaman ("lowerRoman", "decimal", dst.)
- location: posisi di halaman ("HEADER" atau "FOOTER")
- alignment: rata teks nomor ("RIGHT", "LEFT", "CENTER")
- start_at_section: section tempat penomoran ini dimulai (contoh: "daftar_isi", "BAB 1 PENDAHULUAN")

Field tambahan di luar objek:
- chapter_format: template format BAB (contoh: "BAB {n}.")
- sub_chapter_format: template format sub-bab (contoh: "{bab}.{sub}")
- figure_format: template format nomor gambar (contoh: "Gambar {n}.")
- table_format: template format nomor tabel (contoh: "Tabel {bab}.{n}")
