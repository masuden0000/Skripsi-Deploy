---
queries:
  - "bagian inti maksimum 10 sepuluh halaman proposal PKM"
  - "Bab 1 Pendahuluan sampai dengan Daftar Pustaka bagian inti halaman"
  - "Sistematika Penulisan Proposal PKM jumlah halaman batas maksimum inti"
  - "maksimum halaman inti batas halaman proposal lampiran judul kata"
---

# Extraction Task: Page Count Limits (Proposal PKM)

## Context
{context}

## Task
Ekstrak batas maksimum halaman inti dari konteks di atas.
Fokus HANYA pada ketentuan untuk **proposal PKM** — abaikan aturan yang berlaku khusus untuk laporan kemajuan, laporan akhir, atau jenis dokumen PKM lainnya.
Jika tidak ditemukan, gunakan null.

## Chain of Thought — Lakukan Langkah Ini Secara Mental Sebelum Menulis Output

**Langkah 1 — Temukan section sumber kebenaran (targeted scan):**
Jangan scan seluruh konteks secara acak. Gunakan prioritas bertingkat berikut:

- **[P1 — Exact match]** Cari section dengan judul persis:
  - `"Sistematika Proposal Kegiatan"`, atau
  - `"Sistematika Penulisan Proposal"`
  → Jika ditemukan, gunakan section itu sebagai **satu-satunya sumber kebenaran** untuk batas halaman proposal.

- **[P2 — Keyword fallback]** Jika tidak ada judul persis, cari section yang judulnya mengandung **kedua kata** `"sistematika"` DAN `"proposal"` (tidak harus persis, tidak case-sensitive).
  → Gunakan section paling relevan yang ditemukan.

- **[P3 — Last resort]** Jika P1 dan P2 tidak menghasilkan apapun, baru baca konteks secara umum — khusus cari informasi batas halaman proposal.

Contoh penalaran: *"Saya menemukan section 'Sistematika Proposal Kegiatan' → saya gunakan section itu."*

**Langkah 2 — Identifikasi batas halaman:**
Dari section yang ditemukan, cari pernyataan eksplisit tentang jumlah halaman maksimum inti proposal.
Contoh penalaran: *"Ditemukan 'maksimum 10 halaman inti dari BAB 1 sampai Daftar Pustaka' → proposal_halaman_inti_maks=10, halaman_inti_mulai='bab', halaman_inti_selesai='daftar_pustaka'."*

**Langkah 3 — Tentukan batas awal dan akhir hitungan halaman:**
Jika tidak disebutkan secara eksplisit, gunakan default:
- halaman_inti_mulai = "bab" (merujuk ke BAB 1 PENDAHULUAN)
- halaman_inti_selesai = "daftar_pustaka" (merujuk ke DAFTAR PUSTAKA)

**Langkah 4 — Validasi fokus proposal:**
Jika konteks menyebut batas halaman untuk "laporan kemajuan", "laporan akhir", atau dokumen selain proposal, abaikan sepenuhnya — hanya ketentuan untuk **proposal PKM** yang dimasukkan ke output.

## Output Fields

- `proposal_halaman_inti_maks` (integer): batas maksimum halaman inti proposal yang disebutkan eksplisit di konteks.

- `halaman_inti_mulai` (string): nama section tempat hitungan halaman inti dimulai.
  Gunakan TEPAT salah satu nilai section berikut: `"bab"`, `"daftar_isi"`, `"daftar_pustaka"`, `"lampiran"`.
  Jika tidak disebutkan eksplisit, default: `"bab"` (merujuk ke BAB 1 PENDAHULUAN).

- `halaman_inti_selesai` (string): nama section tempat hitungan halaman inti berakhir (inklusif).
  Gunakan TEPAT salah satu nilai section berikut: `"bab"`, `"daftar_isi"`, `"daftar_pustaka"`, `"lampiran"`.
  Jika tidak disebutkan eksplisit, default: `"daftar_pustaka"` (merujuk ke DAFTAR PUSTAKA).

## Normalization Rules
- `halaman_inti_mulai` dan `halaman_inti_selesai` harus menggunakan nilai dari daftar section di atas — jangan gunakan string bebas.
- Jika konteks menyebut "dari BAB 1 sampai Daftar Pustaka" atau padanannya, set `halaman_inti_mulai = "bab"` dan `halaman_inti_selesai = "daftar_pustaka"`.
- Jangan keluarkan field untuk laporan kemajuan atau laporan akhir.
