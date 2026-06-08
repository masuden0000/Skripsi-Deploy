# Alignment TOC/TOF Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Daftarkan style `"table of figures"` dan `"TOC 1"–"TOC 5"` secara eksplisit ke requirements validasi agar entri Daftar Isi, Daftar Gambar, Daftar Tabel, dan Daftar Lampiran terdeteksi dalam hasil validasi alignment.

**Architecture:** Tambah helper `_make_toc_tof_style()` di `validocx_adapter.py` yang menghasilkan requirements identik dengan Normal tetapi tanpa `exclude` pattern. Style TOC/TOF kemudian didaftarkan menggunakan helper ini di dalam `metadata_to_requirements()`.

**Tech Stack:** Python 3.11, python-docx, pytest

---

## File Structure

| File | Aksi | Keterangan |
|---|---|---|
| `ai/model/model_ai/validation/validocx_adapter.py` | Modify (baris 162–167) | Tambah helper + pendaftaran style TOC/TOF |
| `ai/model/tests/test_alignment_toc_tof.py` | Create | Unit test untuk style TOC/TOF di requirements |

---

### Task 1: Tulis test yang gagal

**Files:**
- Create: `ai/model/tests/test_alignment_toc_tof.py`

- [ ] **Step 1: Buat file test baru**

```python
# ai/model/tests/test_alignment_toc_tof.py
"""Test bahwa style TOC dan table of figures terdaftar di requirements validasi."""
from unittest.mock import MagicMock

from model_ai.validation.validocx_adapter import metadata_to_requirements


def _make_metadata(alignment="JUSTIFY", font="Times New Roman", size=12, spacing=1.15):
    """Buat mock DocumentMetadata minimal."""
    meta = MagicMock()
    meta.spacing.paragraph_alignment = alignment
    meta.spacing.heading_alignment = "CENTER"
    meta.spacing.line_spacing = spacing
    meta.spacing.line_spacing_rule = None
    meta.typography.font_family = font
    meta.typography.font_size_body_pt = size
    meta.typography.font_size_heading_pt = size
    meta.page_layout = None
    return meta


_TOC_TOF_STYLES = [
    "table of figures",
    "TOC 1",
    "TOC 2",
    "TOC 3",
    "TOC 4",
    "TOC 5",
]

_ALIGNMENT_JUSTIFY = 3  # WD_ALIGN_PARAGRAPH.JUSTIFY


def test_toc_tof_styles_registered_in_requirements():
    """Setiap style TOC/TOF harus ada di requirements dict."""
    req = metadata_to_requirements(_make_metadata())
    styles = req["styles"]
    for name in _TOC_TOF_STYLES:
        assert name in styles, f"Style '{name}' tidak ditemukan di requirements"


def test_toc_tof_styles_have_no_exclude_pattern():
    """Style TOC/TOF tidak boleh punya exclude pattern (berbeda dari Normal)."""
    req = metadata_to_requirements(_make_metadata())
    styles = req["styles"]
    for name in _TOC_TOF_STYLES:
        assert "exclude" not in styles[name], (
            f"Style '{name}' punya exclude pattern — entri TOC/TOF akan ter-skip"
        )


def test_toc_tof_alignment_is_justify():
    """Alignment style TOC/TOF harus JUSTIFY (sama seperti Normal)."""
    req = metadata_to_requirements(_make_metadata())
    styles = req["styles"]
    for name in _TOC_TOF_STYLES:
        actual = styles[name]["paragraph"]["attributes"]["alignment"]
        assert actual == _ALIGNMENT_JUSTIFY, (
            f"Style '{name}' alignment={actual}, seharusnya {_ALIGNMENT_JUSTIFY} (JUSTIFY)"
        )


def test_normal_exclude_pattern_still_present():
    """Normal harus tetap punya exclude pattern (tidak boleh dihapus)."""
    req = metadata_to_requirements(_make_metadata())
    normal = req["styles"]["Normal"]
    assert "exclude" in normal, "Normal kehilangan exclude pattern"
    assert "Gambar" in normal["exclude"]["text_regex"], (
        "Exclude pattern Normal tidak lagi menyaring caption Gambar"
    )
```

- [ ] **Step 2: Jalankan test — pastikan GAGAL**

```bash
cd ai/model && python -m pytest tests/test_alignment_toc_tof.py -v
```

Expected output:
```
FAILED tests/test_alignment_toc_tof.py::test_toc_tof_styles_registered_in_requirements
FAILED tests/test_alignment_toc_tof.py::test_toc_tof_styles_have_no_exclude_pattern
FAILED tests/test_alignment_toc_tof.py::test_toc_tof_alignment_is_justify
PASSED tests/test_alignment_toc_tof.py::test_normal_exclude_pattern_still_present
```

- [ ] **Step 3: Commit test**

```bash
git add ai/model/tests/test_alignment_toc_tof.py
git commit -m "test: tambah failing test untuk deteksi alignment TOC/TOF"
```

---

### Task 2: Implementasi

**Files:**
- Modify: `ai/model/model_ai/validation/validocx_adapter.py:162-167`

- [ ] **Step 1: Buka file dan cari bagian Style Lampiran (sekitar baris 162)**

Temukan blok ini:

```python
    # ── Style Lampiran ────────────────────────────────────────────────────────
    # Divalidasi sama seperti body (TNR, 12pt, 1.15, JUSTIFY).
    # Alignment bisa diwarisi dari Normal — wrapper.py akan resolve via Normal fallback
    # sehingga tidak memunculkan false-positive "inherited" warning.
    lampiran_style = {k: v for k, v in normal_style.items() if k != "exclude"}
    styles["Lampiran"] = lampiran_style

    # Caption tidak lagi divalidasi via style name — terlalu dinamis (Gambar, Gambar (Lampiran), dll).
    # Validasi caption dilakukan di runner via text-pattern detection (_check_caption_format).
```

- [ ] **Step 2: Tambahkan blok TOC/TOF tepat setelah blok Lampiran**

Ganti blok di atas dengan ini (tambahkan blok TOC/TOF, blok Lampiran dan komentar Caption tetap):

```python
    # ── Style Lampiran ────────────────────────────────────────────────────────
    # Divalidasi sama seperti body (TNR, 12pt, 1.15, JUSTIFY).
    # Alignment bisa diwarisi dari Normal — wrapper.py akan resolve via Normal fallback
    # sehingga tidak memunculkan false-positive "inherited" warning.
    lampiran_style = {k: v for k, v in normal_style.items() if k != "exclude"}
    styles["Lampiran"] = lampiran_style

    # ── Style TOC & TOF ───────────────────────────────────────────────────────
    # "table of figures" → entri Daftar Gambar, Daftar Tabel, Daftar Lampiran
    # "TOC 1"–"TOC 5"    → entri Daftar Isi per level
    #
    # Aturan: identik dengan Normal (JUSTIFY, 12pt, TNR, 1.15) TANPA exclude.
    # Exclude Normal sengaja tidak dipakai agar entri "Gambar N." / "Tabel N."
    # di halaman Daftar Gambar/Tabel tidak ter-skip (exclude itu untuk caption
    # inline di BAB yang sudah dicek terpisah via _check_caption_format).
    toc_tof_style = {k: v for k, v in normal_style.items() if k != "exclude"}
    for _toc_tof_name in (
        "table of figures",
        "TOC 1", "TOC 2", "TOC 3", "TOC 4", "TOC 5",
    ):
        styles[_toc_tof_name] = toc_tof_style

    # Caption tidak lagi divalidasi via style name — terlalu dinamis (Gambar, Gambar (Lampiran), dll).
    # Validasi caption dilakukan di runner via text-pattern detection (_check_caption_format).
```

- [ ] **Step 3: Jalankan test — pastikan LULUS**

```bash
cd ai/model && python -m pytest tests/test_alignment_toc_tof.py -v
```

Expected output:
```
PASSED tests/test_alignment_toc_tof.py::test_toc_tof_styles_registered_in_requirements
PASSED tests/test_alignment_toc_tof.py::test_toc_tof_styles_have_no_exclude_pattern
PASSED tests/test_alignment_toc_tof.py::test_toc_tof_alignment_is_justify
PASSED tests/test_alignment_toc_tof.py::test_normal_exclude_pattern_still_present
```

- [ ] **Step 4: Jalankan semua test untuk memastikan tidak ada yang rusak**

```bash
cd ai/model && python -m pytest tests/ -v
```

Expected: semua test PASS (tidak ada regresi).

- [ ] **Step 5: Commit implementasi**

```bash
git add ai/model/model_ai/validation/validocx_adapter.py
git commit -m "feat(validation): daftarkan style TOC/TOF eksplisit di requirements alignment

Style 'table of figures' dan 'TOC 1'-'TOC 5' kini terdaftar di
requirements validocx dengan aturan identik Normal (JUSTIFY, 12pt,
TNR, 1.15) tanpa exclude pattern.

Sebelumnya, entri Daftar Gambar/Tabel di-skip karena exclude Normal
menangkap pola 'Gambar N' / 'Tabel N'. Entri Daftar Isi (TOC) tidak
muncul jelas karena alignment INHERITED tidak masuk check summary.

Fixes: deteksi alignment TOC/TOF tidak terdeteksi di hasil validasi."
```
