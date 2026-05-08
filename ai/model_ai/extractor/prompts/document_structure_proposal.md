---
queries:
  - "sistematika penulisan proposal PKM halaman sampul pengesahan daftar isi daftar pustaka lampiran"
  - "BAB 1 pendahuluan BAB 2 tinjauan pustaka BAB 3 tahap pelaksanaan BAB 4 biaya jadwal kegiatan proposal PKM-KC"
  - "format nama file PKM pengumpulan batas halaman inti proposal maksimum sistematika"
top_k: 10
---

# Extraction Task: Document Structure (Proposal PKM)

## Context
{context}

## PERINGATAN: Batas Jenis Dokumen
Dokumen sumber membahas TIGA jenis dokumen PKM: Proposal, Laporan Kemajuan, dan Laporan Akhir.
Konteks di atas mungkin mencampur ketiga jenis ini dalam satu section.

**HANYA ekstrak informasi yang berlaku untuk PROPOSAL PKM.**
- Abaikan semua informasi yang berlabel "Laporan Kemajuan" atau "Laporan Akhir"
- Jika ada konflik antara informasi proposal dan laporan, prioritaskan yang berlabel "Proposal"
- Proposal PKM **TIDAK memiliki ringkasan** — jika konteks menyebut ringkasan, itu milik laporan akhir, bukan proposal. Untuk proposal, `ringkasan` = **false**
- BAB 4 proposal adalah "BIAYA DAN JADWAL KEGIATAN", BUKAN "HASIL YANG DICAPAI" (itu milik laporan kemajuan)

## Task
Ekstrak struktur dokumen untuk jenis PROPOSAL PKM dari konteks di atas.
Susun `sections` dengan urutan munculnya section dalam dokumen.

## Normalization Rules
- Gunakan JSON null (bukan string "null") untuk nilai yang tidak ditemukan
- Judul BAB WAJIB ALL CAPS: "PENDAHULUAN", "BIAYA DAN JADWAL KEGIATAN", dst.
- Nilai bool: true atau false (bukan string)
- required: true = wajib ada; false = opsional (sertakan jika ada konten)

## Output Fields (top-level)
- halaman_sampul: apakah ada halaman sampul (bool)
- halaman_pengesahan: apakah ada halaman pengesahan (bool)
- ringkasan: apakah ada ringkasan atau abstrak (bool) — untuk proposal ini **false**
- sections: daftar section berurutan (lihat format di bawah)
- max_halaman_inti: batas maksimum halaman inti (integer)
- format_nama_file: format nama file untuk pengumpulan (string)

## Format sections
Setiap entry di `sections` adalah objek dengan fields berikut:
- type: nama section — gunakan TEPAT salah satu dari nilai berikut (lowercase snake_case, BUKAN Title Case atau UPPERCASE):
  `"daftar_isi"`, `"daftar_gambar"`, `"daftar_tabel"`, `"daftar_lampiran"`, `"bab"`, `"daftar_pustaka"`, `"lampiran"`
  **PENTING**: Jangan gunakan "Daftar Isi", "Daftar Gambar", "DAFTAR ISI", atau variasi lain. Gunakan TEPAT nilai di atas.
- required: true jika wajib ada, false jika opsional — hanya untuk non-bab sections
- number: nomor BAB (integer) — hanya untuk type "bab"
- title: judul BAB dalam ALL CAPS (string) — hanya untuk type "bab"

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
  {"type": "daftar_pustaka", "required": true},
  {"type": "lampiran", "required": true}
]
```
