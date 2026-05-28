---
query: "maksimum halaman inti batas halaman proposal lampiran judul kata"
---

# Extraction Task: Page Count Limits (Proposal PKM)

## Context
{context}

## Task
Ekstrak batas maksimum halaman inti untuk **proposal PKM** dari konteks di atas.
Fokus HANYA pada ketentuan yang berlaku untuk proposal — abaikan informasi tentang laporan kemajuan atau laporan akhir.
Jika tidak ditemukan, gunakan null.

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
