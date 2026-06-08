# Design: Perbaikan Deteksi Alignment TOC & TOF

**Tanggal:** 2026-06-08
**Status:** Disetujui
**File terdampak:** `ai/model/model_ai/validation/validocx_adapter.py`

---

## Latar Belakang

Sistem validasi alignment saat ini bekerja dengan mencocokkan nama style Word tiap paragraf ke daftar requirements. Untuk style yang tidak terdaftar, digunakan fallback ke aturan Normal (JUSTIFY, 12pt, TNR, 1.15).

Ditemukan dua masalah:

1. **TOF Gambar & Tabel tidak terdeteksi** — Style `"table of figures"` memang jatuh ke fallback Normal, namun Normal memiliki pola pengecualian `^(Gambar|Tabel)\s+\d+` yang dirancang untuk melewati caption inline di dalam BAB. Pola ini secara tidak sengaja juga menyaring entri di halaman Daftar Gambar dan Daftar Tabel yang format teksnya sama persis.

2. **TOC tidak muncul jelas di hasil** — Style `"TOC 1"`, `"TOC 2"`, `"TOC 3"` juga jatuh ke fallback Normal dan dicek, namun karena alignment-nya sering `INHERITED` (tidak di-set eksplisit di paragraf, mewarisi dari style chain), hasilnya masuk ke bucket `attr_inherited` bukan ke check summary yang bisa dibaca dengan jelas.

## Keputusan Desain

TOC dan TOF tidak memerlukan aturan khusus — cukup mengikuti aturan Normal: **JUSTIFY, 12pt, TNR, 1.15**. Oleh karena itu, solusi yang dipilih adalah mendaftarkan style TOC/TOF secara eksplisit di requirements dengan aturan yang identik dengan Normal tetapi **tanpa `exclude` pattern**.

## Solusi

### Perubahan di `validocx_adapter.py`

Tambah helper `_make_toc_tof_style(normal_font_attrs, body_alignment, line_spacing)` yang menghasilkan requirements sama seperti Normal tanpa field `exclude`. Daftarkan style-style berikut menggunakan helper ini:

| Style Name | Keterangan |
|---|---|
| `"table of figures"` | Entri Daftar Gambar, Daftar Tabel, Daftar Lampiran |
| `"TOC 1"` | Entri Daftar Isi level 1 (BAB) |
| `"TOC 2"` | Entri Daftar Isi level 2 (Sub-bab) |
| `"TOC 3"` | Entri Daftar Isi level 3 |
| `"TOC 4"` | Entri Daftar Isi level 4 |
| `"TOC 5"` | Entri Daftar Isi level 5 |

### Mengapa Exclude Pattern Normal Tetap Ada

Pola `^(Gambar|Tabel)\s+\d+` di Normal **tidak dihapus**. Pola ini tetap diperlukan untuk melewati caption gambar/tabel di dalam isi BAB (yang alignment-nya CENTER, dicek terpisah oleh `_check_caption_format`). Dengan mendaftarkan `"table of figures"` secara eksplisit, paragraf TOF tidak lagi jatuh ke Normal — sehingga tidak kena exclude.

## Alur Setelah Perbaikan

```
Paragraph "Gambar 1. Grafik..5" (style: table of figures)
  → cocok "table of figures" di requirements (eksplisit)
  → dicek JUSTIFY, tanpa exclude
  → muncul di hasil validasi ✓

Paragraph "Gambar 1. Grafik" (caption di BAB, style: Normal)
  → cocok "Normal" di requirements
  → exclude aktif → di-skip
  → dicek terpisah oleh _check_caption_format ✓

Paragraph "BAB 1 PENDAHULUAN.....1" (style: TOC 1)
  → cocok "TOC 1" di requirements (eksplisit)
  → dicek JUSTIFY, tanpa exclude
  → muncul di hasil validasi ✓

Style lain yang tidak terdaftar
  → fallback ke Normal (perilaku existing tidak berubah)
```

## Batasan

- Style TOC/TOF yang menggunakan **nama kustom** (bukan nama bawaan Word) tidak akan tercakup oleh pendaftaran eksplisit ini. Mereka tetap jatuh ke fallback Normal, yang sudah cukup untuk tujuan validasi saat ini.
- Karena style TOC/TOF didaftarkan menggunakan template Normal secara penuh, validasi font dan line spacing juga ikut aktif untuk style ini (bukan hanya alignment). Ini adalah efek samping yang diinginkan — semua atribut format akan dicek sekaligus.

## File yang Diubah

| File | Jenis Perubahan |
|---|---|
| `ai/model/model_ai/validation/validocx_adapter.py` | Tambah helper + pendaftaran style TOC/TOF |

## File yang Tidak Diubah

- `validocx/validator.py` — tidak perlu diubah
- `validocx/wrapper.py` — tidak perlu diubah (perubahan fallback font terpisah)
- `validocx_runner.py` — tidak perlu diubah
- Frontend — tidak perlu diubah
