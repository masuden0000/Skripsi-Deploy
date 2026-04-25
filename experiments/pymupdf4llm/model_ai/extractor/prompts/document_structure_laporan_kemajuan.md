---
queries:
  - "sistematika penulisan laporan kemajuan PKM halaman sampul pengesahan ringkasan daftar isi format nama file"
  - "BAB laporan kemajuan target luaran hasil dicapai potensi rencana tahapan berikutnya PKM-KC"
  - "batas halaman inti laporan kemajuan PKM maksimum jumlah halaman lampiran tidak dihitung"
top_k: 10
---

# Extraction Task: Document Structure (Laporan Kemajuan PKM)

## Context
{context}

## PERINGATAN: Batas Jenis Dokumen
Dokumen sumber membahas TIGA jenis dokumen PKM: Proposal, Laporan Kemajuan, dan Laporan Akhir.
**HANYA ekstrak informasi yang berlaku untuk LAPORAN KEMAJUAN.**
- Abaikan informasi berlabel "Proposal" atau "Laporan Akhir"
- Laporan Kemajuan PKM **TIDAK memiliki ringkasan** — jika konteks menyebut ringkasan, periksa apakah itu berlaku untuk laporan kemajuan atau laporan akhir. Untuk laporan kemajuan, `ringkasan` = **false**

## Task
Ekstrak struktur dokumen untuk jenis LAPORAN KEMAJUAN dari konteks di atas.
Isi bab_list dengan semua BAB laporan kemajuan beserta judulnya (dalam urutan).

## Aturan false vs null
- **false**: dokumen secara eksplisit menyatakan elemen TIDAK ADA atau tidak diperlukan
- **null**: informasi benar-benar tidak disebutkan dalam konteks
- Jangan output null untuk elemen yang sudah jelas ada/tidak ada dari konteks

## Normalization Rules
- Gunakan JSON null (bukan string "null") untuk nilai yang tidak ditemukan
- bab_number WAJIB dalam format "BAB 1", "BAB 2", dst. (BUKAN hanya angka "1", "2")
- Judul BAB WAJIB ALL CAPS: "PENDAHULUAN", "TARGET LUARAN", "HASIL YANG DICAPAI", dst.
- Nilai bool: true atau false (bukan string)

## Output Fields
- halaman_sampul: apakah ada halaman sampul (bool)
- halaman_pengesahan: apakah ada halaman pengesahan (bool)
- ringkasan: apakah ada ringkasan atau abstrak (bool) — untuk laporan kemajuan ini false
- daftar_isi: apakah ada daftar isi (bool)
- daftar_gambar: keterangan daftar gambar (string atau null)
- daftar_tabel: keterangan daftar tabel (string atau null)
- daftar_lampiran: keterangan daftar lampiran (string atau null)
- bab_list: daftar BAB dalam format [{bab_number: "BAB 1", title: "JUDUL ALL CAPS"}]
- daftar_pustaka: apakah ada daftar pustaka (bool)
- lampiran: apakah ada lampiran (bool)
- max_halaman_inti: batas maksimum halaman inti (integer)
- format_nama_file: format nama file untuk pengumpulan (string)
