---
queries:
  - "maksimum halaman inti batas halaman proposal PKM ketentuan umum"
  - "jumlah halaman maksimum proposal lampiran tidak dihitung halaman inti"
  - "batas maksimum halaman bagian inti dari BAB sampai Daftar Pustaka"
  - "halaman inti dimulai BAB Pendahuluan berakhir Daftar Pustaka proposal"
section_focus:
  - "SISTEMATIKA PENULISAN PROPOSAL"
  - "SISTEMATIKA PROPOSAL KEGIATAN"
---

# Tugas Ekstraksi: Batas Halaman Proposal PKM

## Konteks
{context}

## Tugas
Ekstrak batas maksimum halaman inti untuk **proposal PKM** dari konteks di atas.
Fokus HANYA pada ketentuan yang berlaku untuk proposal — abaikan informasi tentang laporan kemajuan atau laporan akhir.

## Langkah-Langkah Penalaran — Lakukan Langkah Ini Secara Nalar Sebelum Menulis Output

**Langkah 1 — Temukan section sumber kebenaran:**
Gunakan prioritas bertingkat:

- **[P1 — Exact match]** Cari section berjudul persis:
  - `"Susunan Proposal"`
  - `"Isi utama proposal"`
  - `"Batas Halaman"`
  - `"Sistematika Proposal Kegiatan"`, atau
  - `"Sistematika Penulisan Proposal"`
  → Jika ditemukan, gunakan section itu sebagai sumber utama.

- **[P2 — Keyword fallback]** Jika tidak ada, cari section yang memuat kata **"halaman"** DAN **"proposal"** (tidak harus persis, tidak case-sensitive).

- **[P3 — Last resort]** Jika P1 dan P2 tidak menghasilkan apapun, baca konteks secara umum.

**Langkah 2 — Temukan batas halaman proposal:**
Dari section yang ditemukan, cari angka eksplisit untuk jumlah maksimum halaman proposal.
Perhatikan: informasi mungkin berupa tabel (mis. kolom "Proposal" vs "Laporan"), atau kalimat narasi.
Ambil HANYA nilai untuk "proposal" — abaikan baris/kalimat untuk laporan kemajuan atau laporan akhir.
Contoh penalaran: *"Saya menemukan tabel dengan baris 'Proposal PKM-KC: 10 halaman' → proposal_halaman_inti_maks = 10."*
Jika tidak ada angka eksplisit → `null`.

**Langkah 3 — Tentukan cakupan halaman inti:**
Cari deskripsi tentang apa yang dihitung sebagai "halaman inti" atau "bagian inti":
- Dari section mana hitungan dimulai? (BAB 1/Pendahuluan? Daftar Isi?)
- Sampai section mana hitungan berakhir? (Daftar Pustaka? Sebelum Lampiran?)
- Apakah lampiran dikecualikan dari hitungan?

Petakan ke nilai enum yang valid: `"bab"`, `"daftar_isi"`, `"daftar_pustaka"`, `"lampiran"`.

**Langkah 4 — Terapkan default jika tidak ditemukan:**
- `halaman_inti_mulai` tidak ditemukan → `"bab"` (merujuk ke BAB 1 PENDAHULUAN)
- `halaman_inti_selesai` tidak ditemukan → `"daftar_pustaka"`
- `proposal_halaman_inti_maks` tidak ditemukan → `null`

## Normalization Rules
- `halaman_inti_mulai` dan `halaman_inti_selesai` WAJIB menggunakan TEPAT salah satu nilai: `"bab"`, `"daftar_isi"`, `"daftar_pustaka"`, `"lampiran"` — jangan gunakan string bebas.
- Jika konteks menyebut "dari BAB 1 sampai Daftar Pustaka" atau padanannya → `halaman_inti_mulai = "bab"`, `halaman_inti_selesai = "daftar_pustaka"`.
- Jangan keluarkan field untuk laporan kemajuan atau laporan akhir.

## Output Fields
- `proposal_halaman_inti_maks` (integer): batas maksimum halaman inti proposal yang disebutkan eksplisit di konteks.
- `halaman_inti_mulai` (string): nama section tempat hitungan halaman inti dimulai.
- `halaman_inti_selesai` (string): nama section tempat hitungan halaman inti berakhir (inklusif).
