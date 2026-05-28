---
queries:
  - "Sistematika Penulisan Proposal PKM"
  - "huruf romawi i ii iii sudut kanan bawah Daftar Isi penomoran"
  - "angka arab 1 2 3 sudut kanan atas Bab 1 Pendahuluan penomoran"
  - "BAB 1 BAB 2 BAB 3 BAB 4 format nomor bab sub bab 4.1 4.2"
---

# Extraction Task: Numbering

## Context
{context}

## Task
Ekstrak informasi sistem penomoran halaman, bab, dan sub-bab dari konteks di atas.
Fokus HANYA pada ketentuan untuk **proposal PKM** — abaikan aturan yang berlaku khusus untuk laporan kemajuan, laporan akhir, atau jenis dokumen PKM lainnya.
Jika tidak ditemukan, gunakan null (JSON null, BUKAN string "null").

## Chain of Thought — Lakukan Langkah Ini Secara Mental Sebelum Menulis Output

**Langkah 1 — Temukan section sumber kebenaran (targeted scan):**
Jangan scan seluruh konteks secara acak. Gunakan prioritas bertingkat berikut:

- **[P1 — Exact match]** Cari section dengan judul persis:
  - `"Sistematika Proposal Kegiatan"`, atau
  - `"Sistematika Penulisan Proposal"`
  → Jika ditemukan, gunakan section itu sebagai **satu-satunya sumber kebenaran** untuk aturan penomoran.

- **[P2 — Keyword fallback]** Jika tidak ada judul persis, cari section yang judulnya mengandung **kedua kata** `"sistematika"` DAN `"proposal"` (tidak harus persis, tidak case-sensitive).
  → Gunakan section paling relevan yang ditemukan.

- **[P3 — Last resort]** Jika P1 dan P2 tidak menghasilkan apapun, baru baca konteks secara umum termasuk contoh-contoh penomoran yang muncul di teks.

Contoh penalaran: *"Saya menemukan section 'Sistematika Penulisan Proposal' → saya gunakan section itu."*

**Langkah 2 — Identifikasi penomoran halaman:**
Tentukan dua zona penomoran: halaman awal (preliminary, biasanya romawi) dan halaman isi (content, biasanya arab).
Untuk setiap zona, catat: format angka, posisi (header/footer), rata (kiri/tengah/kanan), dan section awal penomoran.
Contoh penalaran: *"Halaman awal: romawi kecil di footer kanan, mulai dari daftar_isi. Halaman isi: desimal di header kanan, mulai dari BAB 1."*

**Langkah 3 — Identifikasi format bab dan sub-bab:**
Tentukan template penomoran BAB dan sub-bab menggunakan placeholder.
**WAJIB inferensikan** dari contoh yang ada di konteks jika aturan tidak dinyatakan eksplisit.
Contoh penalaran: *"Muncul '4.1 Anggaran Biaya' dan 'BAB 4.' → chapter_format='BAB {n}.' dan sub_chapter_format='{bab}.{sub}'."*

**Langkah 4 — Validasi fokus proposal:**
Pastikan nilai yang diekstrak berasal dari ketentuan untuk **proposal PKM**. Jika konteks memuat aturan penomoran berbeda antara proposal dan laporan, ambil hanya aturan proposal. Jika aturan berlaku untuk semua jenis dokumen PKM, masukkan ke output.

**Langkah 5 — Validasi tipe data:**
- `start_at_section` harus berupa nama section yang valid (contoh: "daftar_isi", "bab")
- `chapter_format` dan `sub_chapter_format` harus menggunakan placeholder {n}, {bab}, {sub}

## Normalization Rules
- format halaman: gunakan nilai standar Word — "lowerRoman" (i, ii, iii), "upperRoman" (I, II, III), "decimal" (1, 2, 3)
- location: "HEADER" jika nomor di atas halaman, "FOOTER" jika di bawah halaman
- alignment: "RIGHT" untuk sudut kanan, "LEFT" untuk sudut kiri, "CENTER" untuk tengah
- start_at_section: gunakan nama section yang sama persis dengan entries di `sections` list
- chapter_format: gunakan template dengan placeholder {n} (contoh: "BAB {n}.") — perhatikan titik setelah nomor jika dokumen menggunakannya
- sub_chapter_format: gunakan template dengan placeholder {bab} dan {sub} (contoh: "{bab}.{sub}") — inferensikan dari contoh sub-bab yang ada (misal: "4.1 Anggaran Biaya" → "{bab}.{sub}")
- **PENTING**: Jika aturan penomoran tidak dinyatakan secara eksplisit, **wajib inferensikan** dari contoh-contoh penomoran yang muncul dalam konteks. Dokumen akademik Indonesia umumnya menggunakan format "BAB {n}." untuk bab dan "{bab}.{sub}" untuk sub-bab.

## Output Fields
Keluarkan dua objek: `preliminary` (halaman awal/romawi) dan `content` (halaman isi/arab).
Setiap objek memiliki:
- format: format angka halaman ("lowerRoman", "decimal", dst.)
- location: posisi di halaman ("HEADER" atau "FOOTER")
- alignment: rata teks nomor ("RIGHT", "LEFT", "CENTER")
- start_at_section: section tempat penomoran ini dimulai (contoh: "daftar_isi", "bab")

Field tambahan di luar objek:
- chapter_format: template format BAB (contoh: "BAB {n}.")
- sub_chapter_format: template format sub-bab (contoh: "{bab}.{sub}")

Contoh output:
```json
{
  "preliminary": {
    "format": "lowerRoman",
    "location": "FOOTER",
    "alignment": "RIGHT",
    "start_at_section": "daftar_isi"
  },
  "content": {
    "format": "decimal",
    "location": "HEADER",
    "alignment": "RIGHT",
    "start_at_section": "bab"
  },
  "chapter_format": "BAB {n}.",
  "sub_chapter_format": "{bab}.{sub}"
}
```
