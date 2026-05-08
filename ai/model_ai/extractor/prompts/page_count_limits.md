---
query: "maksimum halaman inti batas halaman proposal laporan kemajuan akhir lampiran"
---

# Extraction Task: Page Count Limits

## Context
{context}

## Task
Ekstrak batas maksimum halaman untuk setiap jenis dokumen PKM dari konteks di atas.
Jika tidak ditemukan, gunakan null.

## Output Fields
- proposal_halaman_inti_maks: batas halaman inti untuk proposal (integer)
- laporan_kemajuan_halaman_inti_maks: batas halaman inti untuk laporan kemajuan (integer)
- laporan_akhir_halaman_inti_maks: batas halaman inti untuk laporan akhir (integer)
- definisi_halaman_inti: rentang section yang dihitung sebagai halaman inti, dalam format "section_awal_to_section_akhir" (contoh: "bab_1_to_daftar_pustaka")
- lampiran_excluded: true jika lampiran tidak dihitung dalam batas halaman inti (bool)
- judul_maks_kata: jumlah maksimum kata pada judul proposal/laporan jika disebutkan (integer atau null)
