---
queries:
  - "Sistematika Penulisan Proposal PKM lampiran daftar isi daftar pustaka"
  - "format nama file PKM pengumpulan sistematika proposal"
  - "4.1 anggaran biaya 4.2 jadwal kegiatan sub bab BAB 4 proposal PKM-KC rekapitulasi"
---

# Extraction Task: Document Structure (Proposal PKM)

## Context
{context}

## Task
Ekstrak struktur dokumen untuk jenis **PROPOSAL PKM** dari konteks di atas.
Susun `sections` dengan urutan munculnya section dalam dokumen.

## Chain of Thought — Lakukan Langkah Ini Secara Mental Sebelum Menulis Output

**Langkah 1 — Temukan section sumber kebenaran (targeted scan):**
Jangan scan seluruh konteks secara acak. Gunakan prioritas bertingkat berikut:

- **[P1 — Exact match]** Cari section dengan judul persis:
  - `"Sistematika Proposal Kegiatan"`, atau
  - `"Sistematika Penulisan Proposal"`
  → Jika ditemukan, gunakan section itu sebagai **satu-satunya sumber kebenaran** untuk struktur dokumen.

- **[P2 — Keyword fallback]** Jika tidak ada judul persis, cari section yang judulnya mengandung **kedua kata** `"sistematika"` DAN `"proposal"` (tidak harus persis, tidak case-sensitive).
  → Gunakan section paling relevan yang ditemukan.

- **[P3 — Last resort]** Jika P1 dan P2 tidak menghasilkan apapun, baru baca konteks secara umum.

Contoh mental: *"Saya menemukan section 'Sistematika Penulisan Proposal' → saya gunakan section itu."*

**Langkah 2 — Identifikasi semua sub-BAB dari section yang ditemukan:**
Catat sub-BAB yang disebutkan beserta nomor dan judulnya.
Contoh mental: *"Saya menemukan sub-BAB: 4.1 Anggaran Biaya, 4.2 Jadwal Kegiatan."*

**Langkah 3 — Hitung dan daftarkan SEMUA lampiran dari section yang ditemukan:**
Buat daftar semua lampiran yang disebutkan, terurut dari Lampiran 1 sampai lampiran terakhir.
Contoh penalaran: *"Saya menemukan 6 lampiran: Lampiran 1 ... Lampiran 6."*
**JANGAN berhenti di Lampiran 5 jika dokumen sumber menyebutkan lebih.**

**Langkah 4 — Validasi kelengkapan:**
Pastikan setiap lampiran yang ditemukan di Langkah 3 masuk ke output sections.
Jika ada yang terlewat, tambahkan sebelum finalisasi output.

## Normalization Rules
- Gunakan JSON null (bukan string "null") untuk nilai yang tidak ditemukan
- Judul BAB WAJIB ALL CAPS: "PENDAHULUAN", "BIAYA DAN JADWAL KEGIATAN", dst.
- Judul sub-BAB menggunakan Title Case (huruf awal tiap kata besar): "Anggaran Biaya", "Jadwal Kegiatan"
- Nilai bool: true atau false (bukan string)
- required: true = wajib ada; false = opsional (sertakan jika ada konten)

## Output Fields (top-level)
- sections: daftar section berurutan (lihat format di bawah)
- max_halaman_inti: batas maksimum halaman inti (integer)
- format_nama_file: format nama file untuk pengumpulan (string)

## Format sections
Setiap entry di `sections` adalah objek dengan fields berikut:
- type: nama section — gunakan TEPAT salah satu dari nilai berikut (lowercase snake_case, BUKAN Title Case atau UPPERCASE):
  `"daftar_isi"`, `"daftar_gambar"`, `"daftar_tabel"`, `"daftar_lampiran"`, `"bab"`, `"sub_bab"`, `"daftar_pustaka"`, `"lampiran"`, `"item_lampiran"`
  **PENTING**: Jangan gunakan "Daftar Isi", "Daftar Gambar", "DAFTAR ISI", atau variasi lain. Gunakan TEPAT nilai di atas.
- required: true jika wajib ada, false jika opsional — hanya untuk non-bab sections
- number: nomor BAB (integer) — hanya untuk type "bab"
- sub_number: nomor sub-BAB seperti "4.1" (string) — hanya untuk type "sub_bab"
- title: untuk type "bab" gunakan ALL CAPS; untuk type "sub_bab" gunakan Title Case (contoh: "Anggaran Biaya"); untuk type "lampiran" gunakan ALL CAPS
- lampiran_number: nomor lampiran seperti "Lampiran 1" (string) — hanya untuk type "lampiran" atau "item_lampiran"

## Aturan Sub-BAB
- **WAJIB ekstrak SEMUA sub-BAB** yang disebutkan dalam dokumen sumber (misal: "4.1 Anggaran Biaya", "4.2 Jadwal Kegiatan")
- Sub-BAB muncul setelah BAB atasannya dalam sections
- Format: `{"type": "sub_bab", "sub_number": "4.1", "title": "Anggaran Biaya"}`

## Aturan LAMPIRAN
- **WAJIB ekstrak SEMUA lampiran** yang disebutkan dalam dokumen sumber — ikuti dokumen sumber, bukan asumsi angka tetap
- Jumlah lampiran **ditentukan oleh dokumen sumber**, bukan nilai hardcode. Panduan PKM yang berbeda versi/tahun dapat memiliki jumlah lampiran yang berbeda.
- Lampiran berikut adalah **referensi lampiran standar PKM-KC** (bukan daftar final — dokumen sumber adalah otoritas tertinggi):
  - Lampiran 1: Biodata Ketua dan Anggota, serta Dosen Pendamping
  - Lampiran 2: Justifikasi Anggaran Kegiatan
  - Lampiran 3: Susunan Tim Pengusul dan Pembagian Tugas
  - Lampiran 4: Surat Pernyataan Ketua Tim Pengusul
  - Lampiran 5: Gambaran Teknologi yang akan Dikembangkan
  - *(Lampiran tambahan mungkin ada tergantung versi panduan — selalu ikuti dokumen sumber)*
- **JANGAN skip lampiran** yang ada di dokumen sumber hanya karena tidak ada di daftar referensi di atas
- Format item lampiran: `{"type": "item_lampiran", "lampiran_number": "Lampiran 1", "title": "BIODATA KETUA DAN ANGGOTA, SERTA DOSEN PENDAMPING"}`

## Aturan Kelengkapan BAB
- **WAJIB sertakan SEMUA BAB** yang disebutkan dalam dokumen sumber. Jangan lewatkan satu pun BAB.
- Proposal PKM-KC memiliki 4 BAB: BAB 1 sampai BAB 4. Pastikan semua 4 BAB hadir dalam sections.
- Nomor BAB harus berurutan dan tidak ada yang terlewat (BAB 1, BAB 2, BAB 3, BAB 4).

## Aturan DAFTAR PUSTAKA
- Cek apakah dokumen sumber menyebutkan adanya DAFTAR PUSTAKA untuk proposal.
- Jika ada, WAJIB sertakan `{"type": "daftar_pustaka", "required": true}` setelah BAB terakhir.
- Jika tidak ada referensi eksplisit, tetap sertakan dengan `required: true` (standar akademik PKM).

Contoh sections untuk proposal:
```json
[
  {"type": "daftar_isi", "required": true},
  {"type": "daftar_gambar", "required": false},
  {"type": "daftar_tabel", "required": false},
  {"type": "daftar_lampiran", "required": false},
  {"type": "bab", "number": 1, "title": "PENDAHULUAN"},
  {"type": "bab", "number": 2, "title": "TINJAUAN PUSTAKA"},
  {"type": "bab", "number": 3, "title": "TAHAP PELAKSANAAN"},
  {"type": "bab", "number": 4, "title": "BIAYA DAN JADWAL KEGIATAN"},
  {"type": "sub_bab", "sub_number": "4.1", "title": "Anggaran Biaya"},
  {"type": "sub_bab", "sub_number": "4.2", "title": "Jadwal Kegiatan"},
  {"type": "daftar_pustaka", "required": true},
  {"type": "lampiran", "title": "LAMPIRAN"},
  {"type": "item_lampiran", "lampiran_number": "Lampiran 1", "title": "BIODATA KETUA DAN ANGGOTA, SERTA DOSEN PENDAMPING"},
  {"type": "item_lampiran", "lampiran_number": "Lampiran 2", "title": "JUSTIFIKASI ANGGARAN KEGIATAN"},
  {"type": "item_lampiran", "lampiran_number": "Lampiran 3", "title": "SUSUNAN TIM PENGUSUL DAN PEMBAGIAN TUGAS"},
  {"type": "item_lampiran", "lampiran_number": "Lampiran 4", "title": "SURAT PERNYATAAN KETUA TIM PENGUSUL"},
  {"type": "item_lampiran", "lampiran_number": "Lampiran 5", "title": "GAMBARAN TEKNOLOGI YANG AKAN DIKEMBANGKAN"},
]

> **Catatan contoh di atas:** Jumlah `item_lampiran` di output HARUS mengikuti dokumen sumber.
> Jika dokumen sumber hanya menyebut 5 lampiran, output hanya 5. Jika 6, output 6. Jika lebih, ikuti semua.
```
