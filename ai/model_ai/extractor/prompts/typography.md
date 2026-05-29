---
queries:
  - "font huruf ukuran tipografi heading body Times New Roman ukuran 12"
  - "huruf kapital judul BAB ALL CAPS cetak tebal bold heading capitalization"
  - "ukuran font body heading pt tipografi ketentuan penulisan"
  - "jenis huruf font yang digunakan dokumen proposal PKM"
section_focus:
  - "SISTEMATIKA PENULISAN PROPOSAL"
  - "SISTEMATIKA PROPOSAL KEGIATAN"
---

# Tugas Ekstraksi: Tipografi

## Konteks
{context}

## Tugas
Ekstrak informasi tipografi dokumen dari konteks di atas.
Jangan gunakan pengetahuan umum — hanya berdasarkan konteks yang diberikan.

## Langkah-Langkah Penalaran — Lakukan Langkah Ini Secara Nalar Sebelum Menulis Output

**Langkah 1 — Temukan section sumber kebenaran:**
Gunakan prioritas bertingkat:

- **[P1 — Exact match]** Cari section dengan judul persis: `"Ketentuan Penulisan"`, `"Tata Cara Penulisan"`, atau `"Format Penulisan"`
  → Jika ditemukan, gunakan section itu sebagai sumber utama.

- **[P2 — Keyword fallback]** Jika tidak ada, cari section yang judulnya mengandung kata **"penulisan"** atau **"format"** (tidak case-sensitive).

- **[P3 — Last resort]** Jika P1 dan P2 tidak menghasilkan apapun, baca konteks secara umum.

**Langkah 2 — Ekstrak font dan ukuran (explicit search):**
Dari section yang ditemukan, cari pernyataan eksplisit tentang:
- Jenis/nama font: "Times New Roman", "Arial", "Calibri", dsb. → `font_family`
- Ukuran font body (teks utama/naskah): angka dalam pt → `font_size_body_pt`
- Ukuran font heading/judul BAB: angka dalam pt → `font_size_heading_pt`

Jika ukuran heading tidak disebutkan secara terpisah dari body → gunakan nilai yang sama dengan `font_size_body_pt`.
`font_size_heading_pt = null` HANYA jika `font_size_body_pt` juga tidak diketahui.

**Langkah 3 — Inferensikan `heading_bold` dari bukti konteks:**
Jangan hanya mencari kata "bold" atau "tebal". Identifikasi dari dua sumber:
- **Pernyataan eksplisit**: "judul BAB dicetak tebal", "heading bold", "huruf tebal untuk BAB"
- **Bukti format markdown**: jika judul BAB/DAFTAR/RINGKASAN ditulis `**...**` di konteks

Jika salah satu bukti ada → `heading_bold = true`.
Jika konteks secara eksplisit menyatakan "tidak tebal", "cetak normal", "bukan bold" → `heading_bold = false`.
Jika tidak ada bukti sama sekali → `null`.

**Langkah 4 — Inferensikan `heading_all_caps` dari contoh heading di konteks:**
Cari contoh nyata heading BAB yang muncul di konteks (contoh aktual, bukan definisi aturan).
Perhatikan apakah teks setelah nomor BAB ditulis ALL CAPS atau tidak:

- Ditemukan "BAB 1. PENDAHULUAN", "BAB 2. TINJAUAN PUSTAKA" (huruf kapital semua) → `heading_all_caps = true`
- Ditemukan "BAB 1. Pendahuluan", "BAB 2. Tinjauan Pustaka" (Title Case) → `heading_all_caps = false`
- Ada pernyataan eksplisit "judul BAB menggunakan huruf kapital seluruhnya" → `heading_all_caps = true`
- Tidak ada contoh maupun pernyataan → `null`

**Langkah 5 — Terapkan default jika tidak ditemukan:**
- `font_family` tidak disebutkan → `null`
- `font_size_body_pt` tidak disebutkan → `null`
- `font_size_heading_pt` tidak disebutkan, tapi `font_size_body_pt` ada → sama dengan `font_size_body_pt`
- `heading_bold` tidak ada bukti → `null`
- `heading_all_caps` tidak ada bukti → `null`

## Normalization Rules
- Gunakan JSON null (bukan string "null") untuk nilai yang tidak ditemukan
- `font_size_heading_pt`: keluarkan sebagai integer pt (contoh: 12)
- `heading_bold`: `true` atau `false` (bool, bukan string)
- `heading_all_caps`: `true` atau `false` (bool, bukan string)

## Output Fields
- `font_family`: nama font utama dokumen (contoh: `"Times New Roman"`)
- `font_size_body_pt`: ukuran font body dalam pt (integer)
- `font_size_heading_pt`: ukuran font heading dalam pt (integer)
- `heading_bold`: apakah judul BAB dicetak tebal/bold (bool)
- `heading_all_caps`: apakah judul BAB ditulis ALL CAPS (bool)
