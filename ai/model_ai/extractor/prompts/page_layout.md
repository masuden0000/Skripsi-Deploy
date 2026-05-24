---
queries:
  - "Format Penulisan Proposal ukuran kertas A4 satu kolom margin"
  - "margin kiri 4 cm margin kanan atas bawah masing-masing 3 cm"
  - "Sistematika Penulisan Proposal A4 margin kiri kanan atas bawah"
---

# Extraction Task: Page Layout

## Context
{context}

## Task
Ekstrak informasi tata letak halaman dari konteks di atas.
Fokus HANYA pada ketentuan untuk **proposal PKM** — abaikan aturan yang berlaku khusus untuk laporan kemajuan, laporan akhir, atau jenis dokumen PKM lainnya.
Jika tidak ditemukan, gunakan null (JSON null, BUKAN string "null").

## Chain of Thought — Lakukan Langkah Ini Secara Mental Sebelum Menulis Output

**Langkah 1 — Temukan section sumber kebenaran (targeted scan):**
Jangan scan seluruh konteks secara acak. Gunakan prioritas bertingkat berikut:

- **[P1 — Exact match]** Cari section dengan judul persis:
  - `"Sistematika Proposal Kegiatan"`, atau
  - `"Sistematika Penulisan Proposal"`
  → Jika ditemukan, gunakan section itu sebagai **satu-satunya sumber kebenaran** untuk margin dan tata letak halaman.

- **[P2 — Keyword fallback]** Jika tidak ada judul persis, cari section yang judulnya mengandung **kedua kata** `"sistematika"` DAN `"proposal"` (tidak harus persis, tidak case-sensitive).
  → Gunakan section paling relevan yang ditemukan.

- **[P3 — Last resort]** Jika P1 dan P2 tidak menghasilkan apapun, baru baca konteks secara umum.

Contoh penalaran: *"Saya menemukan section 'Sistematika Proposal Kegiatan' → saya gunakan section itu."*

**Langkah 2 — Ekstrak nilai margin:**
Catat keempat nilai margin (atas, bawah, kiri, kanan) dalam satuan cm.
Perhatikan: urutan penyebutan margin di dokumen sumber bisa bervariasi (atas-bawah-kiri-kanan atau kiri-kanan-atas-bawah) — baca konteksnya dengan teliti.
Contoh penalaran: *"Ditemukan '4-4-3-3 cm' → margin_top=4, margin_left=4, margin_bottom=3, margin_right=3."*

**Langkah 3 — Tentukan orientasi:**
Jika orientasi tidak disebutkan secara eksplisit, gunakan "Portrait" sebagai default karena proposal PKM umumnya menggunakan orientasi Portrait.

**Langkah 4 — Validasi fokus proposal:**
Pastikan nilai yang diekstrak berasal dari ketentuan untuk **proposal PKM**. Jika konteks memuat aturan margin berbeda antara proposal dan laporan, ambil hanya aturan proposal. Jika aturan berlaku untuk semua jenis dokumen PKM, masukkan ke output.

## Normalization Rules
- Gunakan JSON null (bukan string "null") untuk nilai yang tidak ditemukan
- paper_size: gunakan "A4" sebagai default PKM — kecuali konteks menyebut ukuran lain secara eksplisit
- orientation: gunakan "Portrait" atau "Landscape" — jika tidak disebutkan eksplisit, default "Portrait"

## Output Fields
- margin_top_cm: margin atas dalam cm (float)
- margin_bottom_cm: margin bawah dalam cm (float)
- margin_left_cm: margin kiri dalam cm (float)
- margin_right_cm: margin kanan dalam cm (float)
- paper_size: ukuran kertas (contoh: "A4")
- orientation: orientasi halaman ("Portrait" atau "Landscape")
