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

### line_spacing_rule
Aturan spasi yang digunakan. Pilih TEPAT SATU dari nilai berikut:

| Nilai             | Keterangan                                                                                      | Contoh di dokumen                  |
|-------------------|-------------------------------------------------------------------------------------------------|------------------------------------|
| `"SINGLE"`        | Spasi tunggal (multiplier internal 1.0). `line_spacing` HARUS null.                            | "Spasi: Tunggal", "Single"         |
| `"ONE_POINT_FIVE"`| Spasi 1.5 baris (multiplier internal 1.5). `line_spacing` HARUS null.                          | "Spasi: 1,5 baris", "1.5 lines"    |
| `"DOUBLE"`        | Spasi ganda (multiplier internal 2.0). `line_spacing` HARUS null.                              | "Spasi: Ganda", "Double"           |
| `"MULTIPLE"`      | Kelipatan kustom. `line_spacing` WAJIB diisi sebagai angka desimal (pengali, contoh: 1.15).    | "Spasi: 1,15", "Spasi 1.25x"       |
| `"AT_LEAST"`      | Minimum nilai pt. `line_spacing` WAJIB diisi dalam satuan pt (contoh: 14.0).                   | "Spasi minimum: 14pt"              |
| `"EXACTLY"`       | Nilai absolut pt. `line_spacing` WAJIB diisi dalam satuan pt (contoh: 16.0).                   | "Spasi tepat: 16pt", "Exactly"     |

### line_spacing
- Untuk `SINGLE`, `ONE_POINT_FIVE`, `DOUBLE` → **null** (wajib null, multiplier sudah encoded di rule)
- Untuk `MULTIPLE` → angka desimal (pengali, contoh: 1.15, 1.25, 2.0)
- Untuk `AT_LEAST` atau `EXACTLY` → angka dalam satuan pt (contoh: 14.0, 16.5)

### paragraph_alignment
Rata paragraf. Gunakan nilai enum python-docx: `"JUSTIFY"`, `"LEFT"`, `"RIGHT"`, atau `"CENTER"`.

### first_line_indent_cm
Indentasi baris pertama paragraf dalam cm (float atau null jika tidak ada).
