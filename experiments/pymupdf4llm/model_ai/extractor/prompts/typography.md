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
- font_size_heading_pt: jika sama dengan body, tulis sebagai string dengan keterangan (contoh: "12pt (sama dengan body, bold untuk BAB)")
- heading_style: ekstrak dari konteks, jangan tulis "null" sebagai string
- heading_capitalization: cari aturan apakah judul BAB ditulis ALL CAPS, Title Case, dsb. (contoh: "ALL CAPS untuk judul BAB")

## Output Fields
- font_family: nama font utama dokumen (contoh: "Times New Roman")
- font_size_body_pt: ukuran font body dalam satuan pt sebagai integer (contoh: 12)
- font_size_heading_pt: ukuran font heading — boleh string jika ada keterangan tambahan
- heading_style: gaya penulisan heading (contoh: "Bold")
- heading_capitalization: aturan kapitalisasi judul BAB (contoh: "ALL CAPS untuk judul BAB")
