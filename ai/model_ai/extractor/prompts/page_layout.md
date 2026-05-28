---
query: "margin halaman ukuran kertas A4 portrait batas tepi"
---

# Extraction Task: Page Layout

## Context
{context}

## Task
Ekstrak informasi tata letak halaman dari konteks di atas.
Jika tidak ditemukan, gunakan null (JSON null, BUKAN string "null").

## Normalization Rules
- Gunakan JSON null (bukan string "null") untuk nilai yang tidak ditemukan
- paper_size: selalu gunakan "A4"
- orientation: gunakan "Portrait" atau "Landscape" — jika tidak disebutkan eksplisit dalam konteks, gunakan "Portrait" sebagai default

## Output Fields
- margin_top_cm: margin atas dalam cm (float)
- margin_bottom_cm: margin bawah dalam cm (float)
- margin_left_cm: margin kiri dalam cm (float)
- margin_right_cm: margin kanan dalam cm (float)
- paper_size: ukuran kertas (contoh: "A4")
- orientation: orientasi halaman (contoh: "Portrait")
