---
queries:
  - "sistematika penulisan laporan akhir PKM halaman sampul pengesahan ringkasan daftar isi format nama file"
  - "BAB laporan akhir pendahuluan tinjauan pustaka tahap pelaksanaan hasil dicapai potensi khusus penutup PKM-KC"
  - "batas halaman inti laporan akhir PKM maksimum jumlah halaman lampiran tidak dihitung"
top_k: 10
---

# Extraction Task: Document Structure (Laporan Akhir PKM)

## Context
{context}

## PERINGATAN: Batas Jenis Dokumen
Dokumen sumber membahas TIGA jenis dokumen PKM: Proposal, Laporan Kemajuan, dan Laporan Akhir.
**HANYA ekstrak informasi yang berlaku untuk LAPORAN AKHIR.**
- Abaikan informasi berlabel "Proposal" atau "Laporan Kemajuan"

## Task
Ekstrak struktur dokumen untuk jenis LAPORAN AKHIR dari konteks di atas.
Susun `sections` dengan urutan munculnya section dalam dokumen.

## Normalization Rules
- Gunakan JSON null (bukan string "null") untuk nilai yang tidak ditemukan
- Judul BAB WAJIB ALL CAPS: "PENDAHULUAN", "TINJAUAN PUSTAKA", "PENUTUP", dst.
- Nilai bool: true atau false (bukan string)
- required: true = wajib ada; false = opsional (sertakan jika ada konten)

## Output Fields (top-level)
- halaman_sampul: apakah ada halaman sampul (bool)
- halaman_pengesahan: apakah ada halaman pengesahan (bool)
- ringkasan: apakah ada ringkasan atau abstrak (bool)
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
- Laporan Akhir PKM-KC memiliki 5 BAB: BAB 1 sampai BAB 5. Pastikan semua 5 BAB hadir dalam sections.
- Nomor BAB harus berurutan dan tidak ada yang terlewat.

## Aturan DAFTAR PUSTAKA
- Cek apakah dokumen sumber menyebutkan adanya DAFTAR PUSTAKA untuk laporan akhir.
- Jika ada, WAJIB sertakan `{"type": "daftar_pustaka", "required": true}` setelah BAB terakhir.
- Jika tidak ada referensi eksplisit, tetap sertakan dengan `required: true` (standar akademik PKM).

Contoh sections untuk laporan akhir:
```json
[
  {"type": "daftar_isi", "required": true},
  {"type": "daftar_gambar", "required": false},
  {"type": "daftar_tabel", "required": false},
  {"type": "daftar_lampiran", "required": false},
  {"type": "bab", "number": 1, "title": "PENDAHULUAN"},
  {"type": "bab", "number": 2, "title": "TINJAUAN PUSTAKA"},
  {"type": "bab", "number": 3, "title": "TAHAP PELAKSANAAN"},
  {"type": "bab", "number": 4, "title": "HASIL YANG DICAPAI DAN POTENSI KHUSUS"},
  {"type": "bab", "number": 5, "title": "PENUTUP"},
  {"type": "daftar_pustaka", "required": true},
  {"type": "lampiran", "required": true}
]
```
