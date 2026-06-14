---
queries:
  - "margin halaman batas tepi atas bawah kiri kanan ukuran cm artikel ilmiah PKM"
  - "ukuran kertas A4 portrait margin format halaman artikel ilmiah PKM-AI"
  - "batas tepi kiri kanan atas bawah margin artikel PKM-AI ketentuan penulisan"
  - "ketentuan format halaman kertas orientasi artikel ilmiah PKM"
section_focus:
  - "Lampiran 7"
  - "Sistematika Penulisan Isi Utama Artikel Ilmiah"
  - "FORMAT ARTIKEL ILMIAH"
  - "SISTEMATIKA PENULISAN ARTIKEL"
  - "FORMAT PENULISAN ARTIKEL"
---

# Tugas Ekstraksi: Tata Letak Halaman Artikel Ilmiah PKM-AI

## Konteks
{context}

## Tugas
Ekstrak informasi tata letak halaman untuk **artikel ilmiah PKM-AI** dari konteks di atas.
Jangan gunakan pengetahuan umum — hanya berdasarkan konteks yang diberikan.

## Langkah-Langkah Penalaran — Lakukan Langkah Ini Secara Nalar Sebelum Menulis Output

**Langkah 1 — Temukan section sumber kebenaran:**
Aturan format artikel ilmiah PKM-AI dapat berada di berbagai lokasi tergantung tahun panduan.
Gunakan prioritas bertingkat:

- **[P1 — Exact match]** Cari section dengan judul eksplisit seperti:
  - `"Lampiran 7"` (panduan 2023–2025)
  - `"Sistematika Penulisan Isi Utama Artikel Ilmiah"` (panduan 2026+)
  - `"FORMAT ARTIKEL ILMIAH"` atau `"SISTEMATIKA PENULISAN ARTIKEL"`
  → Jika ditemukan, gunakan section itu sebagai sumber utama.

- **[P2 — Keyword fallback]** Jika tidak ada, cari section yang membahas:
  margin/batas tepi artikel, ukuran kertas artikel ilmiah PKM-AI.

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
