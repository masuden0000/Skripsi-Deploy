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
- line_spacing: spasi antar baris body (float, contoh: 1.15)
- line_spacing_rule: aturan spasi — gunakan "MULTIPLE" untuk spasi berlipat (contoh: 1.15x), "EXACT" untuk pt tetap, "AT_LEAST" untuk minimum
- paragraph_alignment: rata paragraf menggunakan nilai enum python-docx: "JUSTIFY", "LEFT", "RIGHT", atau "CENTER"
- first_line_indent_cm: indentasi baris pertama paragraf dalam cm (float atau null jika tidak ada)
- references_hanging_indent: true jika daftar pustaka menggunakan hanging indent (baris ke-2 dst. menjorok ke dalam), false jika tidak (bool — true/false, bukan string)
