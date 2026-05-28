---
queries:
  - "font huruf ukuran tipografi heading body Times New Roman ukuran 12"
  - "huruf kapital judul BAB ALL CAPS cetak tebal bold heading capitalization penulisan"
top_k: 6
---

# Extraction Task: Typography

## Context
{context}

## Task
Ekstrak informasi tipografi dokumen dari konteks di atas.
Jika informasi tidak ditemukan dalam konteks, gunakan null (JSON null, BUKAN string "null").
Jangan gunakan pengetahuan umum — hanya berdasarkan konteks yang diberikan.

## Normalization Rules
- Gunakan JSON null (bukan string "null") untuk nilai yang tidak ditemukan
- font_size_heading_pt: selalu keluarkan sebagai integer pt (contoh: 12)
  - **Fallback**: Jika dokumen tidak menyebut ukuran font heading secara eksplisit dan berbeda dari body, gunakan nilai yang sama dengan `font_size_body_pt` (bukan null). Null hanya digunakan jika ukuran font body JUGA tidak diketahui.
- heading_bold: true jika heading/judul BAB dicetak tebal (bold), false jika tidak
  - Jika konteks menampilkan judul BAB/DAFTAR/RINGKASAN dengan markdown tebal `**...**`, anggap itu bukti bahwa heading dicetak tebal (heading_bold=true) meskipun kata "bold" tidak ditulis eksplisit.
- heading_all_caps: true jika judul BAB ditulis ALL CAPS, false jika tidak (Title Case, Sentence Case, dsb.)

## Output Fields
- font_family: nama font utama dokumen (contoh: "Times New Roman")
- font_size_body_pt: ukuran font body dalam satuan pt sebagai integer (contoh: 12)
- font_size_heading_pt: ukuran font heading dalam satuan pt sebagai integer
- heading_bold: apakah judul BAB dicetak tebal/bold (bool — true/false, bukan string)
- heading_all_caps: apakah judul BAB ditulis ALL CAPS (bool — true/false, bukan string)
