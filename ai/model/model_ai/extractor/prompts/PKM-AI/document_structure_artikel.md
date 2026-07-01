---
queries:
  - "sistematika penulisan artikel ilmiah PKM-AI format struktur bagian"
  - "isi utama artikel ilmiah pendahuluan metode hasil pembahasan kesimpulan"
  - "daftar pustaka lampiran artikel ilmiah PKM format urutan bagian"
  - "format nama file PKM-AI pengumpulan berkas artikel ilmiah"
  - "judul abstrak kata kunci pendahuluan artikel PKM-AI struktur"
section_focus:
  - "Lampiran 7"
  - "Sistematika Penulisan Isi Utama Artikel Ilmiah"
  - "FORMAT ARTIKEL ILMIAH"
  - "SISTEMATIKA PENULISAN ARTIKEL"
  - "FORMAT PENULISAN ARTIKEL"
---

# Tugas Ekstraksi: Struktur Dokumen Artikel Ilmiah PKM-AI

## Konteks
{context}

## Tugas
Ekstrak struktur dokumen untuk **artikel ilmiah PKM-AI** dari konteks di atas.
Susun sections sesuai urutan kemunculannya dalam dokumen.
Fokus HANYA pada ketentuan artikel ilmiah PKM-AI — abaikan informasi tentang proposal, laporan kemajuan, atau laporan akhir.

## Langkah-Langkah Penalaran — Lakukan Langkah Ini Secara Nalar Sebelum Menulis Output

**Langkah 1 — Temukan section sumber kebenaran (targeted scan):**
Jangan scan seluruh konteks secara acak. Gunakan prioritas bertingkat:

- **[P1 — Exact match]** Cari section dengan judul eksplisit seperti:
  - `"Lampiran 7"` (panduan 2023–2025)
  - `"Sistematika Penulisan Isi Utama Artikel Ilmiah"` (panduan 2026+)
  - `"FORMAT ARTIKEL ILMIAH"` atau `"SISTEMATIKA PENULISAN ARTIKEL"`
  → Jika ditemukan, gunakan section itu sebagai **satu-satunya sumber kebenaran** untuk struktur.

- **[P2 — Keyword fallback]** Jika tidak ada, cari section yang judulnya mengandung **"sistematika"** DAN **"artikel"** (tidak case-sensitive).

- **[P3 — Last resort]** Jika P1 dan P2 tidak menghasilkan apapun, baca konteks secara umum.

Contoh penalaran: *"Saya menemukan section 'Lampiran 7' → saya gunakan section itu."*

**Langkah 2 — Identifikasi halaman pertama artikel (judul, penulis, abstrak):**
Halaman pertama artikel PKM-AI selalu memuat empat elemen berurutan sebelum BAB 1:
- Judul artikel → `{"type": "judul", "required": true, "is_major_section": true, "title": "Judul"}`
- Identitas penulis (nama + afiliasi institusi) → `{"type": "identitas_penulis", "required": true, "is_major_section": true, "title": "Identitas Penulis"}`
- Abstrak bahasa Indonesia → `{"type": "abstrak", "required": true, "is_major_section": true, "title": "Abstrak"}`
- Abstract bahasa Inggris → `{"type": "abstract", "required": true, "is_major_section": true, "title": "Abstract"}`

Sertakan keempat section ini selalu di urutan pertama.

**Langkah 3 — Identifikasi semua BAB artikel:**
Dari section sistematika yang ditemukan, catat seluruh BAB artikel beserta nomor dan judulnya.
Perhatikan: artikel ilmiah menggunakan `type: "bab"` untuk setiap section isi (bukan sub-bab).
Bagian standar artikel PKM-AI biasanya:
- Pendahuluan (BAB 1)
- Metode / Metodologi (BAB 2)
- Hasil dan Pembahasan (BAB 3)
- Kesimpulan (BAB 4)
- Ucapan Terima Kasih (BAB 5, jika ada)
- Kontribusi Penulis (BAB 6, jika ada)
Ikuti dokumen sumber — jika berbeda dari pola di atas, gunakan apa yang disebutkan di konteks.

**Langkah 4 — Identifikasi Daftar Pustaka:**
Cek apakah dokumen menyebutkan adanya Daftar Pustaka/Referensi untuk artikel.
Artikel ilmiah selalu memiliki daftar pustaka → sertakan dengan `required: true` dan `title: "Daftar Pustaka"`.

**Langkah 5 — Identifikasi lampiran:**
Cari apakah dokumen menyebutkan lampiran untuk artikel.
- Jika ada → sertakan `lampiran` sebagai header lampiran, diikuti `item_lampiran` untuk setiap lampiran.
- Jika tidak ada referensi eksplisit tentang lampiran → tidak perlu disertakan (berbeda dari proposal).

**Langkah 6 — Identifikasi format nama file:**
Cari ketentuan penamaan file untuk pengumpulan berkas artikel PKM-AI.
Contoh: "PKM-AI-NamaKetua-NamaInstitusi-JudulSingkat.pdf"
Jika tidak ada ketentuan eksplisit → `null`.

## Normalization Rules
- Gunakan JSON null (bukan string "null") untuk nilai yang tidak ditemukan
- Judul BAB menggunakan Title Case: "Pendahuluan", "Hasil dan Pembahasan"
- Nilai bool: true atau false (bukan string)
- `required`: true = wajib ada; false = opsional

## Format sections
Setiap entry di `sections` adalah objek dengan fields berikut:
- `type`: nama section — gunakan TEPAT salah satu dari nilai berikut:
  `"judul"`, `"identitas_penulis"`, `"abstrak"`, `"abstract"`, `"bab"`, `"daftar_pustaka"`, `"lampiran"`, `"item_lampiran"`
  **PENTING**: Jangan gunakan `"judul_abstrak"`, `"sub_bab"`, `"daftar_isi"` — tipe itu hanya untuk proposal.
- `required`: true jika wajib ada, false jika opsional
- `number`: nomor BAB (integer) — hanya untuk `type: "bab"`
- `title`: judul section (string) — untuk `"bab"` gunakan Title Case; untuk `"item_lampiran"` gunakan ALL CAPS
- `lampiran_number`: nomor lampiran seperti `"Lampiran 1"` — hanya untuk `type: "item_lampiran"`
- `is_major_section`: true untuk `"judul"`, `"identitas_penulis"`, `"abstrak"`, `"abstract"`, `"bab"`, `"daftar_pustaka"`, `"lampiran"`

## Aturan Halaman Pertama Artikel (4 section wajib)
Selalu sertakan keempat section ini di urutan pertama, sebelum BAB 1:
- `{"type": "judul", "required": true, "is_major_section": true, "title": "Judul"}`
- `{"type": "identitas_penulis", "required": true, "is_major_section": true, "title": "Identitas Penulis"}`
- `{"type": "abstrak", "required": true, "is_major_section": true, "title": "Abstrak"}`
- `{"type": "abstract", "required": true, "is_major_section": true, "title": "Abstract"}`

## Aturan BAB Artikel
- Gunakan `type: "bab"` untuk setiap section isi artikel
- Nomor BAB berurutan mulai dari 1
- Ikuti judul dan urutan yang disebutkan di dokumen sumber
- Format: `{"type": "bab", "number": 1, "title": "Pendahuluan", "required": true}`

## Aturan Lampiran Artikel
- Header lampiran: `{"type": "lampiran", "required": false, "title": "Lampiran"}`
- Setiap item: `{"type": "item_lampiran", "lampiran_number": "Lampiran 1", "title": "BIODATA PENULIS"}`
- Sertakan lampiran HANYA jika disebutkan eksplisit di dokumen sumber

Contoh sections untuk artikel PKM-AI:
```json
[
  {"type": "judul", "required": true, "is_major_section": true, "title": "Judul"},
  {"type": "identitas_penulis", "required": true, "is_major_section": true, "title": "Identitas Penulis"},
  {"type": "abstrak", "required": true, "is_major_section": true, "title": "Abstrak"},
  {"type": "abstract", "required": true, "is_major_section": true, "title": "Abstract"},
  {"type": "bab", "number": 1, "title": "Pendahuluan", "required": true},
  {"type": "bab", "number": 2, "title": "Metode", "required": true},
  {"type": "bab", "number": 3, "title": "Hasil dan Pembahasan", "required": true},
  {"type": "bab", "number": 4, "title": "Kesimpulan", "required": true},
  {"type": "bab", "number": 5, "title": "Ucapan Terima Kasih", "required": false},
  {"type": "bab", "number": 6, "title": "Kontribusi Penulis", "required": false},
  {"type": "daftar_pustaka", "required": true, "is_major_section": true, "title": "Daftar Pustaka"},
  {"type": "lampiran", "required": false, "is_major_section": true, "title": "Lampiran"},
  {"type": "item_lampiran", "lampiran_number": "Lampiran 1", "title": "BIODATA PENULIS"}
]
```

> **Catatan contoh di atas:** Jumlah BAB dan item_lampiran HARUS mengikuti dokumen sumber.
> Jika dokumen sumber menyebut 4 BAB, output 4. Jika ada 7, output 7. Ikuti dokumen sumber.
