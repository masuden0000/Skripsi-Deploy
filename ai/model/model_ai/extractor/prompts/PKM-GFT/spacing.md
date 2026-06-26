---
queries:
  - "spasi baris paragraf rata kanan kiri justify indentasi menjorok"
  - "spasi antar baris 1.5 ganda tunggal multiple ketentuan penulisan"
  - "paragraf rata kanan kiri justify alignment format teks body"
section_focus:
  - "Sistematika Gagasan Futuristik Tertulis"
---

# Tugas Ekstraksi: Spasi dan Format Paragraf

## Konteks
{context}

## Tugas
Ekstrak informasi spasi dan format paragraf dari konteks di atas.

## Langkah-Langkah Penalaran — Lakukan Langkah Ini Secara Nalar Sebelum Menulis Output

**Langkah 1 — Temukan section sumber kebenaran:**
Gunakan prioritas bertingkat:

- **[P1 — Exact match]** Cari section dengan judul persis: 
  - `"Ketentuan Penulisan"`
  - `"Tata Cara Penulisan"`
  - `"Format Penulisan"`
  - `"Sistematika Proposal Kegiatan"`
  - `"Sistematika Penulisan Proposal"`
  → Jika ditemukan, gunakan section itu sebagai sumber utama.

- **[P2 — Keyword fallback]** Jika tidak ada, cari section yang judulnya mengandung kata **"penulisan"** atau **"format"** (tidak case-sensitive).

- **[P3 — Last resort]** Jika P1 dan P2 tidak menghasilkan apapun, baca konteks secara umum.

**Langkah 2 — Identifikasi aturan spasi baris (`line_spacing_rule` dan `line_spacing`):**
Dari section yang ditemukan, cari pernyataan eksplisit tentang spasi baris.

Identifikasi kata kunci dan petakan ke enum berikut:

| Deskripsi di dokumen                     | `line_spacing_rule`  | `line_spacing`               |
|------------------------------------------|----------------------|------------------------------|
| "Spasi tunggal", "Single", "Tunggal"     | `"SINGLE"`           | `null` (wajib null)          |
| "1,5 baris", "1.5 lines", "One point five" | `"ONE_POINT_FIVE"` | `null` (wajib null)          |
| "Spasi ganda", "Double", "Ganda"         | `"DOUBLE"`           | `null` (wajib null)          |
| Angka desimal bebas: 1.15, 1.25, 2.0    | `"MULTIPLE"`         | angka tersebut (float)       |
| "Minimum X pt", "Sedikitnya X pt"        | `"AT_LEAST"`         | nilai X dalam pt (float)     |
| "Tepat X pt", "Exactly X pt"             | `"EXACTLY"`          | nilai X dalam pt (float)     |

Contoh penalaran: *"Konteks menyebut 'spasi 1,15' → ini angka desimal bebas → MULTIPLE, line_spacing = 1.15."*

**Langkah 3 — Identifikasi rata paragraf (`paragraph_alignment`):**
Cari pernyataan tentang rata paragraf:
- "rata kanan kiri", "justify", "justified" → `"JUSTIFY"`
- "rata kiri", "left aligned" → `"LEFT"`
- "rata kanan" → `"RIGHT"`
- "tengah", "centered" → `"CENTER"`

Jika tidak disebutkan → `null`.

**Langkah 4 — Terapkan default jika tidak ditemukan:**
Semua field yang tidak ditemukan → `null`.
Jangan mengarang nilai berdasarkan pengetahuan umum PKM.

## Normalization Rules
- `line_spacing_rule`: TEPAT SATU dari `"SINGLE"`, `"ONE_POINT_FIVE"`, `"DOUBLE"`, `"MULTIPLE"`, `"AT_LEAST"`, `"EXACTLY"`, atau `null`
- Untuk `SINGLE`, `ONE_POINT_FIVE`, `DOUBLE`: `line_spacing` **HARUS** `null`
- Untuk `MULTIPLE`: `line_spacing` adalah pengali desimal (contoh: 1.15)
- Untuk `AT_LEAST` atau `EXACTLY`: `line_spacing` dalam satuan pt (contoh: 14.0)
- `paragraph_alignment`: TEPAT SATU dari `"JUSTIFY"`, `"LEFT"`, `"RIGHT"`, `"CENTER"`, atau `null`

## Output Fields
- `line_spacing_rule`: aturan spasi baris (string enum atau null)
- `line_spacing`: nilai spasi numerik — hanya untuk MULTIPLE/AT_LEAST/EXACTLY (float atau null)
- `paragraph_alignment`: rata paragraf (string enum atau null)
