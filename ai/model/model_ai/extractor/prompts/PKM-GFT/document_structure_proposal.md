---
queries:
  - "Sistematika Penulisan Proposal PKM lampiran daftar isi daftar pustaka"
  - "Sistematika Proposal Kegiatan PKM lampiran daftar isi"
  - "format nama file PKM pengumpulan berkas proposal"
  - "batas maksimum halaman bagian inti proposal PKM"
  - "gagasan kesimpulan sub bab proposal PKM-GFT"
  - "rekapitulasi anggaran biaya format tabel PKM"
section_focus:
  - "SISTEMATIKA PENULISAN PROPOSAL"
  - "SISTEMATIKA PROPOSAL KEGIATAN"
---

# Tugas Ekstraksi: Struktur Dokumen Proposal PKM

## Konteks
{context}

## Tugas
Ekstrak struktur dokumen untuk jenis PROPOSAL PKM dari konteks di atas.
Susun sections sesuai urutan kemunculannya dalam dokumen.
Fokus HANYA pada ketentuan yang berlaku untuk proposal — abaikan informasi tentang laporan kemajuan atau laporan akhir.

Catatan: Konteks yang diterima bisa berupa bagian spesifik sistematika maupun konteks
yang lebih luas. Gunakan Langkah 1 untuk menemukan section yang relevan terlebih dahulu
sebelum mengekstrak data.

## Langkah-Langkah Penalaran — Lakukan Langkah Ini Secara Nalar Sebelum Menulis Output

**Langkah 1 — Temukan section sumber kebenaran (targeted scan):**
Jangan scan seluruh konteks secara acak. Gunakan prioritas bertingkat berikut:

- **[P1 — Exact match]** Cari section dengan judul persis:
  - `"Sistematika Proposal Kegiatan"`, atau
  - `"Sistematika Penulisan Proposal"`
  → Jika ditemukan, gunakan section itu sebagai **satu-satunya sumber kebenaran** untuk struktur dokumen.

- **[P2 — Keyword fallback]** Jika tidak ada judul persis, cari section yang judulnya mengandung **kedua kata** `"sistematika"` DAN `"proposal"` (tidak harus persis, tidak case-sensitive).
  → Gunakan section paling relevan yang ditemukan.

- **[P3 — Last resort]** Jika P1 dan P2 tidak menghasilkan apapun, baru baca konteks secara umum.

Contoh penalaran: *"Saya menemukan section 'Sistematika Penulisan Proposal' → saya gunakan section itu."*

**Langkah 2 — Identifikasi semua sub-BAB dari section sistematika penulisan proposal yang ditemukan di Langkah 1:**
Dari section sistematika tersebut, catat seluruh sub-BAB yang disebutkan beserta nomor dan judulnya.
Contoh penalaran: *"Dari section 'Sistematika Penulisan Proposal', saya menemukan sub-BAB: 4.1 Anggaran Biaya, 4.2 Jadwal Kegiatan."*

**Langkah 3 — Hitung dan daftarkan SEMUA lampiran dari section yang ditemukan:**
Buat daftar semua lampiran yang disebutkan, terurut dari Lampiran 1 sampai lampiran terakhir.
Contoh penalaran: *"Saya menemukan 4 lampiran: Lampiran 1 ... Lampiran 4."*
**JANGAN berhenti di Lampiran 3 jika dokumen sumber menyebutkan lebih.**

**Langkah 4 — Validasi kelengkapan:**
Pastikan setiap lampiran yang ditemukan di Langkah 3 masuk ke output sections.
Jika ada yang terlewat, tambahkan sebelum finalisasi output.

## Normalization Rules
- Gunakan JSON null (bukan string "null") untuk nilai yang tidak ditemukan
- title: salin persis dari dokumen sumber — jangan ubah huruf besar/kecil
- Nilai bool: true atau false (bukan string)
- required: true = wajib ada; false = opsional (sertakan jika ada konten)

## Output Fields (top-level)
- sections: daftar section berurutan (lihat format di bawah)
- format_nama_file: format nama file untuk pengumpulan (string)
- lampiran_heading_separator: separator antara nomor dan judul lampiran (string atau null)
  Cara menentukan:
  1. **Cari perintah eksplisit** di section sistematika: "penomoran lampiran menggunakan titik", dsb.
  2. **Jika tidak ada perintah eksplisit**, cari contoh penulisan lampiran di daftar lampiran atau sistematika.
     - Contoh "Lampiran 1. Biodata..." → separator = `"."`
     - Contoh "Lampiran 1 Biodata..." (tanpa titik) → separator = `""`
  3. Jika tidak ada contoh sama sekali → `null` (sistem akan pakai default `"."`)

## Format sections
Setiap entry di `sections` adalah objek dengan fields berikut:
- type: nama section — gunakan TEPAT salah satu dari nilai berikut (lowercase snake_case, BUKAN Title Case atau UPPERCASE):
  `"daftar_isi"`, `"daftar_gambar"`, `"daftar_tabel"`, `"daftar_lampiran"`, `"bab"`, `"sub_bab"`, `"daftar_pustaka"`, `"lampiran"`, `"item_lampiran"`
  **PENTING**: Jangan gunakan "Daftar Isi", "Daftar Gambar", "DAFTAR ISI", atau variasi lain. Gunakan TEPAT nilai di atas.
- required: true jika wajib ada, false jika opsional — hanya untuk non-bab sections
- number: nomor BAB (integer) — hanya untuk type "bab"
- sub_number: nomor sub-BAB seperti "4.1" (string) — hanya untuk type "sub_bab"
- title: salin persis dari dokumen sumber — jangan ubah huruf besar/kecil; untuk type "daftar_isi", "daftar_gambar", "daftar_tabel", "daftar_lampiran", "daftar_pustaka": jika tidak ada judul eksplisit di sumber, gunakan nama standar (mis. "Daftar Isi", "Daftar Pustaka")
- lampiran_number: nomor lampiran seperti "Lampiran 1" (string) — hanya untuk type "lampiran" atau "item_lampiran"

## Aturan Sub-BAB
- **WAJIB ekstrak SEMUA sub-BAB** yang disebutkan dalam dokumen sumber (misal: "4.1 Anggaran Biaya", "4.2 Jadwal Kegiatan")
- Sub-BAB muncul setelah BAB atasannya dalam sections
- Format: `{"type": "sub_bab", "sub_number": "4.1", "title": "Anggaran Biaya"}`

## Aturan LAMPIRAN
- **WAJIB ekstrak SEMUA lampiran** yang disebutkan dalam dokumen sumber — ikuti dokumen sumber, bukan asumsi angka tetap
- Jumlah lampiran **ditentukan oleh dokumen sumber**, bukan nilai hardcode. Panduan PKM yang berbeda versi/tahun dapat memiliki jumlah lampiran yang berbeda.
- Lampiran berikut adalah **referensi lampiran standar PKM-GFT** (bukan daftar final — dokumen sumber adalah otoritas tertinggi):
  - Lampiran 1: Biodata Ketua dan Anggota, serta Dosen Pendamping
  - Lampiran 2: Susunan Tim Pengusul dan Pembagian Tugas
  - Lampiran 3: Surat Pernyataan Ketua Tim Pengusul
  - Lampiran 4: Hasil Uji Periksa Similaritas Proposal
  - *(Lampiran tambahan mungkin ada tergantung versi panduan — selalu ikuti dokumen sumber)*
- **JANGAN skip lampiran** yang ada di dokumen sumber hanya karena tidak ada di daftar referensi di atas
- Format item lampiran: `{"type": "item_lampiran", "lampiran_number": "Lampiran 1", "title": "Biodata Ketua dan Anggota, serta Dosen Pendamping"}`

## Aturan Kelengkapan BAB
- **WAJIB sertakan SEMUA BAB** yang disebutkan dalam dokumen sumber. Jangan lewatkan satu pun BAB.
- Proposal PKM-GFT memiliki 3 BAB: BAB 1 sampai BAB 3. Pastikan semua 3 BAB hadir dalam sections.
- Nomor BAB harus berurutan dan tidak ada yang terlewat (BAB 1, BAB 2, BAB 3).

## Aturan DAFTAR PUSTAKA
- Cek apakah dokumen sumber menyebutkan adanya DAFTAR PUSTAKA untuk proposal.
- Jika ada, WAJIB sertakan `{"type": "daftar_pustaka", "required": true, "title": "Daftar Pustaka"}` setelah BAB terakhir.
- Jika tidak ada referensi eksplisit, tetap sertakan dengan `required: true` (standar akademik PKM).

Contoh sections untuk proposal:
```json
[
  {"type": "daftar_isi", "required": true, "title": "Daftar Isi"},
  {"type": "daftar_gambar", "required": false, "title": "Daftar Gambar"},
  {"type": "daftar_tabel", "required": false, "title": "Daftar Tabel"},
  {"type": "daftar_lampiran", "required": false, "title": "Daftar Lampiran"},
  {"type": "bab", "number": 1, "title": "PENDAHULUAN"},
  {"type": "bab", "number": 2, "title": "GAGASAN"},
  {"type": "bab", "number": 3, "title": "KESIMPULAN"},
  {"type": "daftar_pustaka", "required": true, "title": "Daftar Pustaka"},
  {"type": "lampiran", "title": "Lampiran"},
  {"type": "item_lampiran", "lampiran_number": "Lampiran 1", "title": "Biodata Ketua dan Anggota, serta Dosen Pendamping"},
  {"type": "item_lampiran", "lampiran_number": "Lampiran 2", "title": "SUSUNAN TIM PENGUSUL DAN PEMBAGIAN TUGAS"},
  {"type": "item_lampiran", "lampiran_number": "Lampiran 3", "title": "SURAT PERNYATAAN KETUA TIM PENGUSUL"},
  {"type": "item_lampiran", "lampiran_number": "Lampiran 4", "title": "HASIL UJI PERIKSA SIMILARITAS PROPOSAL"}
]

> **Catatan contoh di atas:** Jumlah `item_lampiran` di output HARUS mengikuti dokumen sumber.
> Jika dokumen sumber hanya menyebut 3 lampiran, output hanya 3. Jika lebih, ikuti semua.
```
