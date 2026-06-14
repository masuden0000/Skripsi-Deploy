---
queries:
  - "maksimum minimum halaman inti batas halaman artikel ilmiah PKM-AI"
  - "jumlah halaman artikel PKM-AI ketentuan umum lampiran tidak dihitung"
  - "batas halaman inti artikel dari judul abstrak sampai daftar pustaka"
  - "panjang artikel ilmiah PKM halaman minimum maksimum ketentuan"
section_focus:
  - "Lampiran 7"
  - "Sistematika Penulisan Isi Utama Artikel Ilmiah"
  - "FORMAT ARTIKEL ILMIAH"
  - "SISTEMATIKA PENULISAN ARTIKEL"
  - "KETENTUAN UMUM"
---

# Tugas Ekstraksi: Batas Halaman Artikel Ilmiah PKM-AI

## Konteks
{context}

## Tugas
Ekstrak batas halaman inti untuk **artikel ilmiah PKM-AI** dari konteks di atas.
Fokus HANYA pada ketentuan yang berlaku untuk artikel ilmiah — abaikan informasi tentang proposal, laporan kemajuan, atau laporan akhir.

## Langkah-Langkah Penalaran — Lakukan Langkah Ini Secara Nalar Sebelum Menulis Output

**Langkah 1 — Temukan section sumber kebenaran:**
Gunakan prioritas bertingkat:

- **[P1 — Exact match]** Cari section dengan judul eksplisit:
  - `"Lampiran 7"` (panduan 2023–2025)
  - `"Sistematika Penulisan Isi Utama Artikel Ilmiah"` (panduan 2026+)
  - `"FORMAT ARTIKEL ILMIAH"`, `"KETENTUAN UMUM"`, atau `"SISTEMATIKA PENULISAN ARTIKEL"`

- **[P2 — Keyword fallback]** Cari section yang memuat kata **"halaman"** DAN **"artikel"** (tidak case-sensitive).

- **[P3 — Last resort]** Baca konteks secara umum.

**Langkah 2 — Temukan batas halaman artikel:**
Dari section yang ditemukan, cari angka untuk jumlah halaman artikel ilmiah.
Perhatikan bahwa artikel mungkin memiliki:
- Batas **minimum** halaman (contoh: "minimal 8 halaman")
- Batas **maksimum** halaman (contoh: "maksimum 15 halaman")
- Atau keduanya dalam satu pernyataan

Perhatikan: informasi mungkin dalam tabel (kolom "Artikel" vs "Proposal") atau kalimat narasi.
Ambil HANYA nilai untuk "artikel" — abaikan baris/kalimat untuk proposal atau laporan.

Contoh penalaran:
- *"Menemukan 'artikel ilmiah minimal 8 halaman' → artikel_halaman_inti_min = 8."*
- *"Menemukan 'tidak lebih dari 15 halaman inti' → artikel_halaman_inti_maks = 15."*

**Langkah 3 — Tentukan cakupan halaman inti artikel:**
Cari deskripsi tentang apa yang dihitung sebagai "halaman inti" untuk artikel:
- Dari section mana hitungan dimulai? (Judul+Abstrak? BAB 1?)
- Sampai section mana hitungan berakhir? (Daftar Pustaka? Sebelum Lampiran?)
- Apakah lampiran dikecualikan?

Petakan ke nilai enum yang valid: `"judul_abstrak"`, `"bab"`, `"daftar_pustaka"`, `"lampiran_utama"`.
Jika tidak ditemukan eksplisit → gunakan default (Langkah 4).

**Langkah 4 — Terapkan default jika tidak ditemukan:**
- `halaman_inti_mulai` → `"judul_abstrak"` (artikel dimulai dari halaman judul/abstrak)
- `halaman_inti_selesai` → `"daftar_pustaka"`
- `artikel_halaman_inti_min` tidak ditemukan → `null`
- `artikel_halaman_inti_maks` tidak ditemukan → `null`

## Normalization Rules
- `halaman_inti_mulai` dan `halaman_inti_selesai` WAJIB menggunakan TEPAT salah satu nilai: `"judul_abstrak"`, `"bab"`, `"daftar_pustaka"`, `"lampiran_utama"` — jangan gunakan string bebas
- Jangan keluarkan field untuk proposal atau laporan
- `artikel_halaman_inti_min` dan `artikel_halaman_inti_maks`: integer atau null

## Output Fields
- `artikel_halaman_inti_min` (integer atau null): batas minimum halaman inti artikel
- `artikel_halaman_inti_maks` (integer atau null): batas maksimum halaman inti artikel
- `halaman_inti_mulai` (string): nama section tempat hitungan halaman inti dimulai
- `halaman_inti_selesai` (string): nama section tempat hitungan halaman inti berakhir (inklusif)
