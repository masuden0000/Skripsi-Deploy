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
Isi bab_list dengan semua BAB proposal beserta judulnya (dalam urutan).

## Aturan false vs null
- **false**: dokumen secara eksplisit menyatakan elemen TIDAK ADA atau DILARANG untuk proposal
- **null**: informasi benar-benar tidak disebutkan dalam konteks
- Jangan output null untuk elemen yang sudah jelas ada/tidak ada dari konteks

## Normalization Rules
- Gunakan JSON null (bukan string "null") untuk nilai yang tidak ditemukan
- bab_number WAJIB dalam format "BAB 1", "BAB 2", dst. (BUKAN hanya angka "1", "2")
- Judul BAB WAJIB ALL CAPS: "PENDAHULUAN", "BIAYA DAN JADWAL KEGIATAN", dst.
- Nilai bool: true atau false (bukan string)

## Output Fields
- halaman_sampul: apakah ada halaman sampul (bool)
- halaman_pengesahan: apakah ada halaman pengesahan (bool)
- ringkasan: apakah ada ringkasan atau abstrak (bool) — untuk proposal ini false
- daftar_isi: apakah ada daftar isi (bool)
- daftar_gambar: keterangan daftar gambar (string atau null)
- daftar_tabel: keterangan daftar tabel (string atau null)
- daftar_lampiran: keterangan daftar lampiran (string atau null)
- bab_list: daftar BAB dalam format [{bab_number: "BAB 1", title: "JUDUL ALL CAPS"}]
- daftar_pustaka: apakah ada daftar pustaka (bool)
- lampiran: apakah ada lampiran (bool)
- max_halaman_inti: batas maksimum halaman inti (integer)
- format_nama_file: format nama file untuk pengumpulan (string)
