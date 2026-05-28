---
queries:
  - "Format Penulisan Proposal jarak baris 1,15 spasi perataan rata kiri dan kanan"
  - "teks paragraf jarak baris 1,15 spasi rata kiri kanan justify"
  - "Daftar Pustaka baris kedua setelahnya menjorok ke dalam hanging indent"
  - "Sistematika Penulisan Proposal PKM spasi paragraf"
---

# Extraction Task: Spacing

## Context
{context}

## Task
Ekstrak informasi spasi dan format paragraf dari konteks di atas.
Fokus HANYA pada ketentuan untuk **proposal PKM** — abaikan aturan yang berlaku khusus untuk laporan kemajuan, laporan akhir, atau jenis dokumen PKM lainnya.
Jika tidak ditemukan, gunakan null (JSON null, BUKAN string "null").

## Chain of Thought — Lakukan Langkah Ini Secara Mental Sebelum Menulis Output

**Langkah 1 — Temukan section sumber kebenaran (targeted scan):**
Jangan scan seluruh konteks secara acak. Gunakan prioritas bertingkat berikut:

- **[P1 — Exact match]** Cari section dengan judul persis:
  - `"Sistematika Proposal Kegiatan"`, atau
  - `"Sistematika Penulisan Proposal"`
  → Jika ditemukan, gunakan section itu sebagai **satu-satunya sumber kebenaran** untuk aturan spasi.

- **[P2 — Keyword fallback]** Jika tidak ada judul persis, cari section yang judulnya mengandung **kedua kata** `"sistematika"` DAN `"proposal"` (tidak harus persis, tidak case-sensitive).
  → Gunakan section paling relevan yang ditemukan.

- **[P3 — Last resort]** Jika P1 dan P2 tidak menghasilkan apapun, baru baca konteks secara umum.

Contoh penalaran: *"Saya menemukan section 'Sistematika Penulisan Proposal' → saya gunakan section itu."*

**Langkah 2 — Identifikasi jenis spasi:**
Dari section yang ditemukan, tentukan jenis `line_spacing_rule` berdasarkan tabel di bawah, lalu catat nilai `line_spacing` jika diperlukan.
Contoh penalaran: *"Dokumen menyebut 'spasi 1,15' → ini MULTIPLE dengan line_spacing = 1.15."*

**Langkah 3 — Ekstrak alignment dan indentasi:**
Catat rata paragraf (JUSTIFY/LEFT/RIGHT/CENTER) dan indentasi baris pertama jika disebutkan.

**Langkah 4 — Validasi fokus proposal:**
Pastikan nilai yang diekstrak berasal dari ketentuan untuk **proposal PKM**. Jika konteks memuat aturan berbeda antara proposal dan laporan, ambil hanya aturan proposal. Jika aturan berlaku untuk semua jenis dokumen PKM, masukkan ke output.

**Langkah 5 — Validasi tipe data:**
- `line_spacing` HARUS null untuk SINGLE / ONE_POINT_FIVE / DOUBLE
- `line_spacing` WAJIB diisi untuk MULTIPLE / AT_LEAST / EXACTLY

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
Indentasi baris pertama paragraf dalam cm (float atau null jika tidak disebutkan).
