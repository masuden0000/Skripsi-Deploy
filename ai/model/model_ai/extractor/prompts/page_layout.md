---
queries:
  - "margin halaman batas tepi atas bawah kiri kanan ukuran cm penulisan"
  - "ukuran kertas A4 portrait margin format halaman ketentuan penulisan"
  - "batas tepi kiri 4 kanan 3 atas 3 bawah 3 margin penulisan"
  - "ketentuan format halaman kertas orientasi portrait landscape"
section_focus:
  - "SISTEMATIKA PENULISAN PROPOSAL"
  - "SISTEMATIKA PROPOSAL KEGIATAN"
---

# Tugas Ekstraksi: Tata Letak Halaman

## Konteks
{context}

## Tugas
Ekstrak informasi tata letak halaman dari konteks di atas.
Fokus HANYA pada ketentuan yang berlaku untuk proposal — abaikan informasi tentang laporan kemajuan atau laporan akhir.

## Langkah-Langkah Penalaran — Lakukan Langkah Ini Secara Nalar Sebelum Menulis Output

**Langkah 1 — Temukan section sumber kebenaran:**
Gunakan prioritas bertingkat:

- **[P1 — Exact match]** Cari section dengan judul persis:   - `"Susunan Proposal"`
  - `"Sistematika Proposal Kegiatan"`
  - `"Sistematika Penulisan Proposal"`
  - `"Isi utama proposal"`
  - `"Format Penulisan Proposal"`
  → Jika ditemukan, gunakan section itu sebagai sumber utama.

- **[P2 — Keyword fallback]** Jika tidak ada, cari section yang judulnya mengandung kata **"penulisan"** atau **"format"** (tidak case-sensitive).

- **[P3 — Last resort]** Jika P1 dan P2 tidak menghasilkan apapun, baca konteks secara umum.

**Langkah 2 — Ekstrak nilai margin:**
Dari section yang ditemukan, identifikasi nilai margin untuk setiap sisi halaman.
Istilah yang mungkin digunakan:
- Atas (`margin_top_cm`): "batas atas", "tepi atas", "margin atas"
- Bawah (`margin_bottom_cm`): "batas bawah", "tepi bawah", "margin bawah"
- Kiri (`margin_left_cm`): "batas kiri", "tepi kiri", "margin kiri"
- Kanan (`margin_right_cm`): "batas kanan", "tepi kanan", "margin kanan"

Perhatikan satuan — jika dokumen menyebutkan dalam mm, konversi ke cm (bagi 10).
Jika salah satu sisi tidak disebutkan eksplisit → `null` untuk sisi tersebut.

**Langkah 3 — Tentukan ukuran dan orientasi kertas:**
Cari penyebutan ukuran kertas (A4, Letter, Kuarto, dsb.) dan orientasi (Portrait/tegak, Landscape/mendatar).
Jika tidak disebutkan → gunakan default (lihat Langkah 4).

**Langkah 4 — Terapkan default jika tidak ditemukan:**
- `paper_size` tidak disebutkan → `"A4"` (standar PKM)
- `orientation` tidak disebutkan → `"Portrait"` (standar PKM)
- Nilai margin tidak disebutkan → `null`

## Normalization Rules
- Semua margin dalam satuan cm sebagai float
- `paper_size`: default `"A4"`
- `orientation`: `"Portrait"` atau `"Landscape"` — default `"Portrait"` jika tidak disebutkan eksplisit
- Gunakan JSON null (bukan string "null") untuk nilai yang tidak ditemukan

## Output Fields
- `margin_top_cm`: margin atas dalam cm (float)
- `margin_bottom_cm`: margin bawah dalam cm (float)
- `margin_left_cm`: margin kiri dalam cm (float)
- `margin_right_cm`: margin kanan dalam cm (float)
- `paper_size`: ukuran kertas (contoh: `"A4"`)
- `orientation`: orientasi halaman (contoh: `"Portrait"`)
