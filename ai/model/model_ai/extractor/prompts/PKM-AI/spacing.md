---
queries:
  - "ketentuan jarak spasi antar baris (line spacing) format penulisan utama naskah artikel PKM"
  - "aturan spasi baris khusus untuk halaman judul, abstrak, paragraf, caption, dan daftar pustaka referensi"
  - "jarak baris artikel ilmiah ketentuan penulisan"
  - "line spacing teks artikel PKM format penulisan"
section_focus:
  - "Lampiran 7"
  - "Sistematika Penulisan Isi Utama Artikel Ilmiah"
  - "FORMAT ARTIKEL ILMIAH"
  - "SISTEMATIKA PENULISAN ARTIKEL"
  - "FORMAT PENULISAN ARTIKEL"
---

# Tugas Ekstraksi: Spasi dan Format Paragraf Artikel Ilmiah PKM-AI

## Konteks
{context}

## Tugas
Ekstrak informasi spasi dan format paragraf untuk **artikel ilmiah PKM-AI** dari konteks di atas.
Jangan gunakan pengetahuan umum — hanya berdasarkan konteks yang diberikan.

## Langkah-Langkah Penalaran — Lakukan Langkah Ini Secara Nalar Sebelum Menulis Output

**Langkah 1 — Temukan section sumber kebenaran:**
Aturan format artikel ilmiah PKM-AI dapat berada di berbagai lokasi tergantung tahun panduan.
Gunakan prioritas bertingkat:

- **[P1 — Exact match]** Cari section dengan judul eksplisit seperti:
  - `"Lampiran 7"` (panduan 2023–2025)
  - `"Sistematika Penulisan Isi Utama Artikel Ilmiah"` (panduan 2026+)
  - `"FORMAT ARTIKEL ILMIAH"` atau `"SISTEMATIKA PENULISAN ARTIKEL"`
  → Jika ditemukan, gunakan section itu sebagai sumber utama.

- **[P2 — Keyword fallback]** Jika tidak ada, cari section yang membahas:
  spasi baris artikel, jarak antar baris, format paragraf artikel ilmiah.

- **[P3 — Last resort]** Jika P1 dan P2 tidak menghasilkan apapun, baca konteks secara umum.

**Langkah 2 — Identifikasi aturan spasi baris body artikel (line_spacing_rule dan line_spacing):**
Cari pernyataan tentang spasi baris untuk **isi/body artikel** (paragraf utama, bukan halaman judul).
Petakan ke enum berikut:

| Deskripsi di dokumen                      | `line_spacing_rule`  | `line_spacing`         |
|-------------------------------------------|----------------------|------------------------|
| "Spasi tunggal", "Single", "Tunggal"      | `"SINGLE"`           | `null` (wajib null)    |
| "1,5 baris", "1.5 lines"                  | `"ONE_POINT_FIVE"`   | `null` (wajib null)    |
| "Spasi ganda", "Double"                   | `"DOUBLE"`           | `null` (wajib null)    |
| Angka desimal bebas: 1.15, 1.25, 2.0     | `"MULTIPLE"`         | angka tersebut (float) |
| "Minimum X pt", "Sedikitnya X pt"         | `"AT_LEAST"`         | nilai X dalam pt       |
| "Tepat X pt", "Exactly X pt"              | `"EXACTLY"`          | nilai X dalam pt       |

Contoh penalaran: *"Konteks menyebut 'spasi 1,15' → angka desimal bebas → MULTIPLE, line_spacing = 1.15."*

**Langkah 3 — Identifikasi spasi halaman judul/abstrak (line_spacing_rule_title_abstract dan line_spacing_title_abstract):**
Artikel PKM-AI memiliki dua zona spasi berbeda:
- **Zona 1: Judul Artikel, Nama Penulis, Alamat Institusi, Abstrak** — cari pernyataan seperti:
  "judul dan abstrak menggunakan spasi 1,0", "halaman pertama spasi tunggal", "abstrak 1 spasi"
  → Keluarkan `line_spacing_rule_title_abstract` menggunakan tabel enum di Langkah 2
  → Keluarkan `line_spacing_title_abstract` (float) hanya jika rule adalah MULTIPLE/AT_LEAST/EXACTLY
- **Zona 2: Body artikel** — sudah diekstrak di Langkah 2

Jika panduan tidak membedakan → `line_spacing_rule_title_abstract = null`, `line_spacing_title_abstract = null`.

**Langkah 4 — Identifikasi rata paragraf (paragraph_alignment):**
Cari pernyataan tentang rata paragraf:
- "rata kanan kiri", "justify", "justified" → `"JUSTIFY"`
- "rata kiri", "left aligned" → `"LEFT"`
- "rata kanan" → `"RIGHT"`
- "tengah", "centered" → `"CENTER"`

Jika tidak disebutkan → `null`.

**Langkah 5 — Identifikasi spasi daftar pustaka (line_spacing_rule_bibliography dan line_spacing_bibliography):**
Cari pernyataan yang secara eksplisit menyebut spasi untuk bagian **Daftar Pustaka**:
- "daftar pustaka menggunakan spasi 1,15" → `line_spacing_rule_bibliography = "MULTIPLE"`, `line_spacing_bibliography = 1.15`
- "referensi ditulis dengan spasi tunggal" → `line_spacing_rule_bibliography = "SINGLE"`, `line_spacing_bibliography = null`

Jika tidak disebutkan terpisah → `line_spacing_rule_bibliography = null`, `line_spacing_bibliography = null`
(sistem akan otomatis menggunakan spasi body sebagai fallback).

**Langkah 7 — Ekstrak pengaturan format judul artikel (title_case, title_alignment, title_bold):**
Cari pernyataan atau contoh tentang cara penulisan judul artikel pada halaman pertama:

- **`title_case`** — huruf pada judul:
  - "judul ditulis huruf kapital semua", "all caps", "cetak kapital" → `"UPPERCASE"`
  - "judul huruf kecil semua" → `"LOWERCASE"`
  - "judul huruf kalimat biasa" → `"SENTENCE_CASE"`
  - Jika tidak disebutkan → `null`

- **`title_alignment`** — rata judul:
  - "judul rata tengah", "centered" → `"CENTER"`
  - "rata kiri" → `"LEFT"`
  - "rata kanan kiri", "justify" → `"JUSTIFY"`
  - Jika tidak disebutkan → `null`

- **`title_bold`** — ketebalan judul:
  - "dicetak tebal", "bold", "huruf tebal" → `true`
  - "tidak tebal", "tidak bold", "normal weight" → `false`
  - Jika tidak disebutkan → `null` (sistem akan default `true`)

**Langkah 8 — Terapkan default jika tidak ditemukan:**
Semua field yang tidak ditemukan → `null`.
Jangan mengarang nilai berdasarkan pengetahuan umum PKM.

## Normalization Rules
- `line_spacing_rule`: TEPAT SATU dari `"SINGLE"`, `"ONE_POINT_FIVE"`, `"DOUBLE"`, `"MULTIPLE"`, `"AT_LEAST"`, `"EXACTLY"`, atau `null`
- Untuk `SINGLE`, `ONE_POINT_FIVE`, `DOUBLE`: `line_spacing` **HARUS** `null`
- Untuk `MULTIPLE`: `line_spacing` adalah pengali desimal (contoh: 1.15)
- `line_spacing_title_abstract`: float atau `null` (contoh: 1.0)
- `paragraph_alignment`: TEPAT SATU dari `"JUSTIFY"`, `"LEFT"`, `"RIGHT"`, `"CENTER"`, atau `null`
- `title_case`: TEPAT SATU dari `"UPPERCASE"`, `"LOWERCASE"`, `"SENTENCE_CASE"`, `"TOGGLE_CASE"`, atau `null`
- `title_alignment`: TEPAT SATU dari `"CENTER"`, `"LEFT"`, `"RIGHT"`, `"JUSTIFY"`, atau `null`
- `title_bold`: boolean `true`, `false`, atau `null`

## Normalization Rules — Spasi Daftar Pustaka
Sama dengan body: gunakan tabel enum yang sama untuk `line_spacing_rule_bibliography`.
Jika tidak ditemukan → kedua field `null`.

## Output Fields
- `line_spacing_rule`: aturan spasi baris body artikel (string enum atau null)
- `line_spacing`: nilai spasi numerik body artikel — hanya untuk MULTIPLE/AT_LEAST/EXACTLY (float atau null)
- `line_spacing_rule_title_abstract`: aturan spasi baris Judul Artikel, Nama Penulis, Alamat Institusi, Abstrak (string enum atau null)
- `line_spacing_title_abstract`: nilai spasi numerik zona judul/abstrak — hanya untuk MULTIPLE/AT_LEAST/EXACTLY (float atau null)
- `line_spacing_rule_bibliography`: aturan spasi baris daftar pustaka (string enum atau null)
- `line_spacing_bibliography`: nilai spasi numerik daftar pustaka — hanya untuk MULTIPLE/AT_LEAST/EXACTLY (float atau null)
- `paragraph_alignment`: rata paragraf (string enum atau null)
- `title_case`: style huruf judul artikel (string enum atau null)
- `title_alignment`: rata judul artikel (string enum atau null)
- `title_bold`: apakah judul dicetak tebal (boolean atau null)
