---
queries:
  - "penomoran halaman romawi kecil arab letak sudut kanan atas bawah mulai halaman pertama"
  - "halaman preliminari romawi kecil daftar isi penomoran awal dokumen"
  - "halaman isi arab dimulai bab pendahuluan penomoran konten"
  - "format penulisan bab sub bab ketentuan penulisan tata cara PKM"
  - "4.1 4.2 sub bab anggaran biaya jadwal kegiatan contoh penomoran format"
top_k: 10
section_focus:
  - "SISTEMATIKA PENULISAN PROPOSAL"
  - "SISTEMATIKA PROPOSAL KEGIATAN"
---

# Tugas Ekstraksi: Sistem Penomoran Dokumen

## Konteks
{context}

## Tugas
Ekstrak sistem penomoran halaman, format bab, dan format sub-bab dari konteks di atas.
Fokus HANYA pada ketentuan yang berlaku untuk proposal — abaikan informasi tentang laporan kemajuan atau laporan akhir.

## Langkah-Langkah Penalaran — Lakukan Secara Nalar Sebelum Menulis Output

**Langkah 1 — Cari aturan penomoran halaman (explicit search):**
Cari bagian yang membahas ketentuan atau tata cara penulisan. Bagian ini biasanya
memuat aturan eksplisit seperti lokasi nomor halaman, format angka, dan titik mulai penomoran.

Dari bagian tersebut, identifikasi:
- Halaman preliminari (sebelum BAB I): format angka, letak, alignment, mulai dari section mana
- Halaman isi (mulai BAB I): format angka, letak, alignment, mulai dari section mana

Jika aturan tidak ditemukan secara eksplisit → lanjut ke Langkah 4 untuk default.

**Langkah 2 — Inferensikan `chapter_format` dari pola heading BAB yang ditemukan:**
Jangan mencari pernyataan eksplisit "format bab adalah...".
Temukan contoh heading BAB yang nyata di konteks, lalu identifikasi komponennya:

- Apakah ada prefix? (misalnya "BAB", "Bab", atau tidak ada sama sekali)
- Format angkanya: Arab (1, 2, 3) atau Romawi (I, II, III)?
- Apakah ada tanda baca setelah angka? (titik, tidak ada)
- Apakah ada spasi antara prefix dan angka?

Abstraksi pola tersebut menjadi template menggunakan `{n}` sebagai placeholder angka.
Gunakan pola yang paling konsisten muncul di konteks — bukan mencocokkan ke daftar.

**Langkah 3 — Inferensikan `sub_chapter_format` dari pola angka bertingkat:**
Cari contoh penomoran sub-bab yang muncul di konteks (pola: angka titik angka).
Dari contoh yang ditemukan, identifikasi komponennya:

- Format angka tingkat pertama (bab): Arab atau Romawi?
- Separator antara bab dan sub: titik atau karakter lain?
- Apakah ada tanda baca penutup setelah angka sub?

Abstraksi pola tersebut menjadi template menggunakan `{bab}` dan `{sub}` sebagai placeholder.
Abaikan angka satu level (misal "1." tanpa sub) — fokus pada pola dua level atau lebih.
Gunakan pola yang paling konsisten muncul di konteks — bukan mencocokkan ke daftar.

**Langkah 4 — Terapkan default jika tidak ditemukan:**
- `preliminary`: lowerRoman, FOOTER, CENTER, mulai dari daftar_isi
- `content`: decimal, HEADER, RIGHT, mulai dari BAB I
- `chapter_format`: `"BAB {n}"` (standar PKM tanpa titik)
- `sub_chapter_format`: `"{bab}.{sub}"` (standar PKM)

## Normalization Rules
- `format`: `"lowerRoman"` (i, ii, iii) / `"upperRoman"` (I, II, III) / `"decimal"` (1, 2, 3)
- `location`: `"HEADER"` atau `"FOOTER"`
- `alignment`: `"RIGHT"`, `"LEFT"`, atau `"CENTER"`
- `start_at_section`: nama section tempat penomoran dimulai (contoh: `"daftar_isi"`, `"bab_1"`)
- Gunakan JSON null untuk nilai yang benar-benar tidak bisa diinferensikan

## Output Fields
- `preliminary`: `{format, location, alignment, start_at_section}` — halaman awal (romawi)
- `content`: `{format, location, alignment, start_at_section}` — halaman isi (arab)
- `chapter_format`: template format BAB (contoh: `"BAB {n}."`)
- `sub_chapter_format`: template format sub-bab (contoh: `"{bab}.{sub}"`)
