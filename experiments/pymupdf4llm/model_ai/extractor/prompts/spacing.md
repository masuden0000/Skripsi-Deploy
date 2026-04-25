---
query: "spasi baris paragraf rata kanan kiri justify indentasi menjorok"
---

# Extraction Task: Spacing

## Context
{context}

## Task
Ekstrak informasi spasi dan format paragraf dari konteks di atas.
Jika tidak ditemukan, gunakan null.

## Output Fields
- line_spacing_body: spasi antar baris body (float, contoh: 1.15)
- paragraph_alignment: rata paragraf (contoh: "Justify (rata kiri dan kanan)")
- paragraph_first_indent: indentasi awal paragraf jika ada, null jika tidak ada
- hanging_indent_references: aturan hanging indent untuk daftar pustaka
