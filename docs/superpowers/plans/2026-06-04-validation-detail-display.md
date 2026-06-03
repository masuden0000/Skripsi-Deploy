# Validation Detail Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tampilkan lokasi spesifik (Halaman, BAB, Paragraf, cuplikan teks, nilai salah vs benar) untuk setiap masalah validasi dalam UI dua-panel yang interaktif.

**Architecture:** Backend (`debug_report.py`) diperkaya dengan deteksi nomor halaman dari page-break marker di XML DOCX dan deteksi nama BAB dari Heading 1. Data ini dikemas ke field baru `occurrences` di `ValidationIssue` dan dikirim ke frontend. Frontend diganti dengan layout dua panel: panel kiri daftar masalah per kategori, panel kanan detail lokasi saat satu masalah diklik.

**Tech Stack:** Python 3.x + python-docx (backend), TypeScript + React + Zod + Tailwind CSS (frontend Next.js)

---

## File Map

| File | Aksi | Tanggung Jawab |
|------|------|----------------|
| `ai/model/model_ai/validation/validocx/debug_report.py` | Modify | Tambah field `page` dan `bab` di `_get_para_details()` |
| `ai/model/model_ai/validation/models.py` | Modify | Tambah field `occurrences` ke `ValidationIssue` |
| `ai/model/model_ai/validation/validocx_runner.py` | Modify | Isi `occurrences` dari `paragraph_details` di `_build_issues_checks()` |
| `ai/model/tests/test_validation_location.py` | Create | Unit test untuk semua perubahan backend |
| `frontend/lib/api/pkm.ts` | Modify | Tambah `occurrences` ke Zod schema `validationIssueSchema` |
| `frontend/components/reviewer/DocumentValidator.tsx` | Modify | Redesign ke two-panel layout dengan kartu lokasi |

---

## Task 1: Deteksi `page` dan `bab` di `_get_para_details()`

**Files:**
- Modify: `ai/model/model_ai/validation/validocx/debug_report.py`
- Create: `ai/model/tests/test_validation_location.py`

**Penjelasan:** `_get_para_details()` adalah fungsi yang sudah ada — dia membaca seluruh paragraf dari file DOCX dan mengembalikan dict berisi info per paragraf (style, teks, font, dll.). Kita tambahkan dua field baru: `page` (nomor halaman dari page-break marker di XML) dan `bab` (teks Heading 1 terakhir yang ditemukan sebelum paragraf ini).

- [ ] **Step 1.1 — Tulis test yang gagal**

  Buat file `ai/model/tests/test_validation_location.py`:

  ```python
  """Test deteksi page dan bab di _get_para_details()."""
  import os
  import tempfile

  import pytest
  from docx import Document as DocxDocument
  from docx.oxml import OxmlElement
  from docx.oxml.ns import qn

  # Impor fungsi yang akan diuji
  from model_ai.validation.validocx.debug_report import _get_para_details


  def _make_test_docx_with_pages() -> str:
      """Buat DOCX sementara: 2 halaman, 2 BAB, masing-masing 1 paragraf isi."""
      doc = DocxDocument()

      # Halaman 1 — BAB 1
      doc.add_heading("BAB 1 PENDAHULUAN", level=1)
      doc.add_paragraph("Paragraf isi BAB 1.")

      # Explicit page break → halaman 2
      para_break = doc.add_paragraph()
      run_break = para_break.add_run()
      br = OxmlElement("w:br")
      br.set(qn("w:type"), "page")
      run_break._r.append(br)

      # Halaman 2 — BAB 2
      doc.add_heading("BAB 2 TINJAUAN PUSTAKA", level=1)
      doc.add_paragraph("Paragraf isi BAB 2.")

      tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
      doc.save(tmp.name)
      tmp.close()
      return tmp.name


  def test_page_and_bab_are_detected():
      path = _make_test_docx_with_pages()
      try:
          result = _get_para_details(path)

          # Cari paragraf isi BAB 1
          bab1_para = next(
              v for v in result.values() if v.get("text") == "Paragraf isi BAB 1."
          )
          assert bab1_para["page"] == 1, "Paragraf BAB 1 harus di halaman 1"
          assert bab1_para["bab"] == "BAB 1 PENDAHULUAN"

          # Cari paragraf isi BAB 2
          bab2_para = next(
              v for v in result.values() if v.get("text") == "Paragraf isi BAB 2."
          )
          assert bab2_para["page"] == 2, "Paragraf BAB 2 harus di halaman 2"
          assert bab2_para["bab"] == "BAB 2 TINJAUAN PUSTAKA"
      finally:
          os.unlink(path)


  def test_bab_is_none_before_first_heading():
      doc = DocxDocument()
      doc.add_paragraph("Paragraf sebelum BAB manapun.")
      tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
      doc.save(tmp.name)
      tmp.close()
      try:
          result = _get_para_details(tmp.name)
          first = next(
              v for v in result.values()
              if v.get("text") == "Paragraf sebelum BAB manapun."
          )
          assert first["bab"] is None
          assert first["page"] == 1
      finally:
          os.unlink(tmp.name)
  ```

- [ ] **Step 1.2 — Jalankan test, pastikan GAGAL**

  ```bash
  cd "ai/model"
  python -m pytest tests/test_validation_location.py::test_page_and_bab_are_detected -v
  ```

  Hasil yang diharapkan: `FAILED` — karena field `page` dan `bab` belum ada di `_get_para_details()`.

- [ ] **Step 1.3 — Implementasi perubahan di `debug_report.py`**

  Buka `ai/model/model_ai/validation/validocx/debug_report.py`. Ganti seluruh fungsi `_get_para_details()` (baris 70–105) dengan versi baru berikut:

  ```python
  def _get_para_details(docx_path):
      """Muat semua paragraf dari docx, kembalikan dict {idx: detail}.

      Setiap entri sekarang menyertakan:
        - page : nomor halaman (dihitung dari page-break marker di XML)
        - bab  : teks Heading 1 terakhir sebelum paragraf ini (atau None)
      """
      try:
          from docx import Document
          from docx.oxml.ns import qn

          doc = Document(docx_path)
          result = {}
          current_page = 1
          current_bab = None

          for idx, para in enumerate(doc.paragraphs):
              para_xml = para._p

              # ── Deteksi page break ───────────────────────────────────────
              # w:lastRenderedPageBreak → page break dari hasil render Word
              # w:br w:type="page"      → explicit manual page break
              has_page_break = bool(
                  para_xml.findall(".//" + qn("w:lastRenderedPageBreak"))
              ) or any(
                  br.get(qn("w:type")) == "page"
                  for br in para_xml.findall(".//" + qn("w:br"))
              )

              if has_page_break and idx > 0:
                  current_page += 1

              # ── Deteksi nama BAB dari Heading 1 ─────────────────────────
              style_name = para.style.name
              text = para.text.strip()
              if style_name == "Heading 1" and text:
                  current_bab = text

              # ── Data paragraf (sama seperti sebelumnya + page + bab) ────
              pf    = para.paragraph_format
              ls    = pf.line_spacing
              rule  = str(pf.line_spacing_rule) if pf.line_spacing_rule else "inherited"
              align = str(pf.alignment) if pf.alignment else "inherited"

              runs = []
              for r in para.runs:
                  size  = round(r.font.size.pt, 1) if r.font.size else None
                  name  = r.font.name or None
                  attrs = [a for a in ("bold", "italic", "underline", "all_caps")
                           if getattr(r.font, a)]
                  runs.append({
                      "text"      : r.text[:60],
                      "font_size" : size,
                      "font_name" : name,
                      "attributes": attrs,
                  })

              result[idx] = {
                  "style"       : style_name,
                  "alignment"   : align,
                  "line_spacing": float(ls) if ls is not None else None,
                  "spacing_rule": rule,
                  "text"        : text[:100],
                  "runs"        : runs,
                  "page"        : current_page,   # BARU
                  "bab"         : current_bab,    # BARU
              }

          return result
      except Exception:
          return {}
  ```

- [ ] **Step 1.4 — Jalankan test, pastikan LULUS**

  ```bash
  cd "ai/model"
  python -m pytest tests/test_validation_location.py -v
  ```

  Hasil yang diharapkan: `PASSED` untuk kedua test.

- [ ] **Step 1.5 — Commit**

  ```bash
  git add ai/model/model_ai/validation/validocx/debug_report.py
  git add ai/model/tests/test_validation_location.py
  git commit -m "feat(validation): detect page number and BAB name per paragraph in debug_report"
  ```

---

## Task 2: Tambah Field `occurrences` ke `ValidationIssue`

**Files:**
- Modify: `ai/model/model_ai/validation/models.py`
- Modify: `ai/model/tests/test_validation_location.py` (tambah test)

**Penjelasan:** `ValidationIssue` adalah class yang merepresentasikan satu jenis masalah validasi (misal: "Font mismatch"). Sekarang kita tambahkan field `occurrences` — sebuah list yang berisi semua lokasi spesifik di mana masalah ini terjadi di dalam dokumen.

- [ ] **Step 2.1 — Tambah test untuk field baru**

  Tambahkan test ini di akhir file `ai/model/tests/test_validation_location.py`:

  ```python
  from model_ai.validation.models import ValidationIssue


  def test_validation_issue_accepts_occurrences():
      issue = ValidationIssue(
          category="typography",
          field="font_per_paragraph",
          severity="error",
          message="Font mismatch",
          occurrences=[
              {
                  "page": 3,
                  "bab": "BAB 1 PENDAHULUAN",
                  "para_idx": 4,
                  "style": "Normal",
                  "text": "Latar belakang...",
                  "actual": "11.0pt, Times New Roman",
                  "expected": "12pt, Times New Roman",
              }
          ],
      )
      assert issue.occurrences is not None
      assert len(issue.occurrences) == 1
      assert issue.occurrences[0]["page"] == 3
      assert issue.occurrences[0]["bab"] == "BAB 1 PENDAHULUAN"


  def test_validation_issue_occurrences_defaults_to_none():
      issue = ValidationIssue(
          category="typography",
          field="font_per_paragraph",
          severity="error",
          message="Font mismatch",
      )
      assert issue.occurrences is None
  ```

- [ ] **Step 2.2 — Jalankan test, pastikan GAGAL**

  ```bash
  cd "ai/model"
  python -m pytest tests/test_validation_location.py::test_validation_issue_accepts_occurrences -v
  ```

  Hasil yang diharapkan: `FAILED` — field `occurrences` belum ada.

- [ ] **Step 2.3 — Tambah field `occurrences` ke `ValidationIssue` di `models.py`**

  Buka `ai/model/model_ai/validation/models.py`. Cari class `ValidationIssue` (sekitar baris 47). Tambahkan satu field baru tepat sebelum method `__str__`:

  ```python
  occurrences: list[dict] | None = Field(
      default=None,
      description=(
          "List lokasi spesifik setiap kejadian masalah ini. "
          "Setiap item berisi: page (int), bab (str|None), para_idx (int), "
          "style (str), text (str), actual (str|None), expected (str|None)."
      ),
  )
  ```

  Hasil akhir bagian bawah class `ValidationIssue` akan terlihat seperti ini:

  ```python
  location: str | None = Field(
      default=None,
      description="Lokasi issue dalam dokumen (e.g., 'Seluruh dokumen', 'BAB 1 PENDAHULUAN', 'Paragraf ke-5')"
  )
  occurrences: list[dict] | None = Field(
      default=None,
      description=(
          "List lokasi spesifik setiap kejadian masalah ini. "
          "Setiap item berisi: page (int), bab (str|None), para_idx (int), "
          "style (str), text (str), actual (str|None), expected (str|None)."
      ),
  )

  def __str__(self) -> str:
      return f"[{self.severity.upper()}] {self.category}.{self.field}: {self.message}"
  ```

- [ ] **Step 2.4 — Jalankan test, pastikan LULUS**

  ```bash
  cd "ai/model"
  python -m pytest tests/test_validation_location.py -v
  ```

  Hasil yang diharapkan: semua test `PASSED`.

- [ ] **Step 2.5 — Commit**

  ```bash
  git add ai/model/model_ai/validation/models.py
  git add ai/model/tests/test_validation_location.py
  git commit -m "feat(validation): add occurrences field to ValidationIssue model"
  ```

---

## Task 3: Isi `occurrences` di `_build_issues_checks()`

**Files:**
- Modify: `ai/model/model_ai/validation/validocx_runner.py`
- Modify: `ai/model/tests/test_validation_location.py` (tambah test)

**Penjelasan:** `_build_issues_checks()` adalah fungsi yang mengubah `report` (dict dari `build_report`) menjadi list `ValidationIssue`. Kita perlu mengisi field `occurrences` yang baru kita buat. Setiap `paragraph_details` di dalam `report` sekarang sudah punya `page` dan `bab` dari Task 1 — kita tinggal ambil dan format menjadi list occurrence.

- [ ] **Step 3.1 — Tambah helper `_build_occurrences()` dan test-nya**

  Tambahkan test ini di akhir `ai/model/tests/test_validation_location.py`:

  ```python
  from model_ai.validation.validocx_runner import _build_occurrences


  def test_build_occurrences_from_paragraph_details():
      para_details = [
          {
              "para_idx": 4,
              "page": 3,
              "bab": "BAB 1 PENDAHULUAN",
              "style": "Normal",
              "text": "Latar belakang penelitian...",
              "runs": [{"font_size": 11.0, "font_name": "Times New Roman", "text": "", "attributes": []}],
          },
          {
              "para_idx": 22,
              "page": 7,
              "bab": "BAB 2 TINJAUAN PUSTAKA",
              "style": "Normal",
              "text": "Menurut teori...",
              "runs": [{"font_size": 11.0, "font_name": "Times New Roman", "text": "", "attributes": []}],
          },
      ]
      result = _build_occurrences(
          para_details=para_details,
          actual_str="11.0pt, Times New Roman",
          expected_str="12pt, Times New Roman",
      )
      assert len(result) == 2
      assert result[0]["page"] == 3
      assert result[0]["bab"] == "BAB 1 PENDAHULUAN"
      assert result[0]["para_idx"] == 4
      assert result[0]["actual"] == "11.0pt, Times New Roman"
      assert result[0]["expected"] == "12pt, Times New Roman"
      assert result[1]["page"] == 7
  ```

- [ ] **Step 3.2 — Jalankan test, pastikan GAGAL**

  ```bash
  cd "ai/model"
  python -m pytest tests/test_validation_location.py::test_build_occurrences_from_paragraph_details -v
  ```

  Hasil yang diharapkan: `FAILED` — fungsi `_build_occurrences` belum ada.

- [ ] **Step 3.3 — Tambah fungsi `_build_occurrences()` di `validocx_runner.py`**

  Buka `ai/model/model_ai/validation/validocx_runner.py`. Tambahkan fungsi baru ini tepat sebelum fungsi `_build_issues_checks()` (sekitar baris 76):

  ```python
  def _build_occurrences(
      para_details: list[dict],
      actual_str: str | None = None,
      expected_str: str | None = None,
  ) -> list[dict]:
      """Bangun list occurrence dari paragraph_details.

      Setiap occurrence berisi: page, bab, para_idx, style, text, actual, expected.
      para_details adalah list dict hasil _inject_para_details() yang sudah
      menyertakan field 'page' dan 'bab' dari Task 1.
      """
      result = []
      for detail in para_details:
          if not isinstance(detail, dict):
              continue
          result.append({
              "page"     : detail.get("page"),
              "bab"      : detail.get("bab"),
              "para_idx" : detail.get("para_idx"),
              "style"    : detail.get("style"),
              "text"     : (detail.get("text") or "")[:100],
              "actual"   : actual_str,
              "expected" : expected_str,
          })
      return result
  ```

- [ ] **Step 3.4 — Update `_build_issues_checks()` untuk mengisi `occurrences`**

  Di dalam `_build_issues_checks()`, ada empat blok: font_mismatch, value_mismatch, undefined_styles, attr_inherited. Kita update masing-masing untuk mengisi `occurrences`.

  **Blok font_mismatch** (sekitar baris 117–134) — ubah menjadi:

  ```python
  for item in report["errors"].get("font_mismatch", []):
      key = item.get("key", "")
      count = item.get("count", 1)
      examples = item.get("examples", [])
      paras = item.get("paragraph_details", []) or item.get("paragraphs", [])
      location = _para_location(paras) if isinstance(paras, list) and paras and isinstance(paras[0], dict) else None

      example_str = f' Contoh: "{examples[0]}"' if examples else ""
      msg = f"Font mismatch: {key} ({count}x).{example_str}"

      # Pisahkan "actual=[X] expected=[Y]" dari key untuk label occurrence
      actual_str = None
      expected_str = None
      m = re.search(r"actual=\[([^\]]+)\]", key)
      if m:
          actual_str = m.group(1)
      m = re.search(r"expected=\[([^\]]+)\]", key)
      if m:
          expected_str = m.group(1)

      occurrences = _build_occurrences(paras if isinstance(paras, list) and paras and isinstance(paras[0], dict) else [], actual_str, expected_str)

      issues.append(ValidationIssue(
          category="typography", field="font_per_paragraph",
          severity="error", message=msg, location=location,
          occurrences=occurrences or None,
      ))
      checks.append(ValidationCheckResult(
          category="typography", field="font_per_paragraph",
          status="failed", message=msg, location=location,
      ))
  ```

  **Blok value_mismatch** (sekitar baris 96–114) — ubah menjadi:

  ```python
  for item in report["errors"].get("value_mismatch", []):
      key = item.get("key", "")
      count = item.get("count", 1)
      examples = item.get("examples", [])
      paras = item.get("paragraph_details", []) or item.get("paragraphs", [])
      category, field = _vm_category(key)
      location = _para_location(paras) if isinstance(paras, list) and paras and isinstance(paras[0], dict) else None

      example_str = f' Contoh: "{examples[0]}"' if examples else ""
      msg = f"{key} ({count}x mismatch).{example_str}"

      # Parse actual/expected dari format key: "Style.attr: actual=X expected=Y"
      actual_str = None
      expected_str = None
      m = re.search(r"actual=(\S+)", key)
      if m:
          actual_str = m.group(1)
      m = re.search(r"expected=(\S+)", key)
      if m:
          expected_str = m.group(1)

      occurrences = _build_occurrences(paras if isinstance(paras, list) and paras and isinstance(paras[0], dict) else [], actual_str, expected_str)

      issues.append(ValidationIssue(
          category=category, field=field,
          severity="error", message=msg, location=location,
          occurrences=occurrences or None,
      ))
      checks.append(ValidationCheckResult(
          category=category, field=field,
          status="failed", message=msg, location=location,
      ))
  ```

  **Blok undefined_styles** (sekitar baris 137–148) — ubah menjadi:

  ```python
  for item in report["warnings"].get("undefined_styles", []):
      style = item.get("style", "?")
      count = item.get("count", 1)
      paras = item.get("paragraph_details", []) or []
      msg = f"Style tidak terdefinisi di requirements: '{style}' ({count}x paragraf)"

      occurrences = _build_occurrences(
          paras if isinstance(paras, list) and paras and isinstance(paras[0], dict) else [],
          actual_str=style,
          expected_str=None,
      )

      issues.append(ValidationIssue(
          category="typography", field="undefined_style",
          severity="warning", message=msg,
          occurrences=occurrences or None,
      ))
      checks.append(ValidationCheckResult(
          category="typography", field="undefined_style",
          status="warning", message=msg,
      ))
  ```

  **Blok attr_inherited** (sekitar baris 150–162) — ubah menjadi:

  ```python
  for item in report["warnings"].get("attr_inherited", []):
      attr = item.get("attribute", "?")
      count = item.get("count", 1)
      paras = item.get("paragraph_details", []) or []
      msg = f"Atribut '{attr}' tidak di-set eksplisit (diwarisi dari Word default), {count}x"

      occurrences = _build_occurrences(
          paras if isinstance(paras, list) and paras and isinstance(paras[0], dict) else [],
          actual_str="inherited",
          expected_str="explicit",
      )

      issues.append(ValidationIssue(
          category="spacing", field="paragraph_inherited",
          severity="warning", message=msg,
          occurrences=occurrences or None,
      ))
      checks.append(ValidationCheckResult(
          category="spacing", field="paragraph_inherited",
          status="warning", message=msg,
      ))
  ```

  > **Catatan:** Blok `_check_heading_case()` di bawah `_build_issues_checks()` tidak diubah di sini — fungsi itu sudah mencatat contoh teks heading yang salah langsung di `message`. Penambahan `occurrences` untuk heading case bisa dilakukan di iterasi berikutnya jika diperlukan.

- [ ] **Step 3.5 — Jalankan semua test**

  ```bash
  cd "ai/model"
  python -m pytest tests/test_validation_location.py -v
  ```

  Hasil yang diharapkan: semua test `PASSED`.

- [ ] **Step 3.6 — Commit**

  ```bash
  git add ai/model/model_ai/validation/validocx_runner.py
  git add ai/model/tests/test_validation_location.py
  git commit -m "feat(validation): populate occurrences field in _build_issues_checks"
  ```

---

## Task 4: Update Zod Schema di `pkm.ts` (Frontend)

**Files:**
- Modify: `frontend/lib/api/pkm.ts`

**Penjelasan:** `validationIssueSchema` adalah "cetakan" yang dipakai untuk mem-validasi dan membentuk tipe data response dari API. Kalau kita tidak tambahkan `occurrences` ke sini, data yang dikirim backend akan dibuang saat parsing. Zod adalah library validasi yang dipakai proyek ini — mirip seperti "guard" yang memastikan data dari server sesuai dengan yang diharapkan.

- [ ] **Step 4.1 — Update `validationIssueSchema` di `pkm.ts`**

  Buka `frontend/lib/api/pkm.ts`. Cari `validationIssueSchema` dan tambahkan field `occurrences`:

  ```typescript
  const validationOccurrenceSchema = z.object({
    page: z.number().nullable().optional(),
    bab: z.string().nullable().optional(),
    para_idx: z.number().nullable().optional(),
    style: z.string().nullable().optional(),
    text: z.string().nullable().optional(),
    actual: z.string().nullable().optional(),
    expected: z.string().nullable().optional(),
  })

  export const validationIssueSchema = z.object({
    severity: z.enum(["error", "warning", "info"]),
    category: z.string(),
    field: z.string().optional().nullable(),
    message: z.string(),
    expected: z.string().optional().nullable(),
    actual: z.string().optional().nullable(),
    occurrences: z.array(validationOccurrenceSchema).optional().nullable(),
  })
  ```

  Letakkan `validationOccurrenceSchema` tepat di atas `validationIssueSchema`.

- [ ] **Step 4.2 — Export type baru `ValidationOccurrence`**

  Di bagian `// Types`, tambahkan satu baris baru:

  ```typescript
  export type ValidationOccurrence = z.infer<typeof validationOccurrenceSchema>
  ```

- [ ] **Step 4.3 — Verifikasi tidak ada TypeScript error**

  ```bash
  cd frontend
  npx tsc --noEmit
  ```

  Hasil yang diharapkan: tidak ada error.

- [ ] **Step 4.4 — Commit**

  ```bash
  git add frontend/lib/api/pkm.ts
  git commit -m "feat(frontend): add occurrences field to validationIssueSchema"
  ```

---

## Task 5: Redesign `DocumentValidator.tsx` ke Two-Panel Layout

**Files:**
- Modify: `frontend/components/reviewer/DocumentValidator.tsx`

**Penjelasan:** Komponen ini adalah seluruh halaman validasi. Kita ganti bagian "daftar masalah" dari layout flat/lama ke layout dua panel baru. State baru `selectedIssueIdx` menyimpan index masalah yang sedang diklik di panel kiri — dipakai untuk menentukan apa yang tampil di panel kanan.

- [ ] **Step 5.1 — Ganti isi `DocumentValidator.tsx` dengan versi baru**

  Ganti seluruh konten file `frontend/components/reviewer/DocumentValidator.tsx` dengan kode berikut:

  ```tsx
  "use client"

  import { useCallback, useState } from "react"
  import { ReviewerSurfaceCard } from "./shared"
  import { Button } from "@/components/ui/button"
  import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
  } from "@/components/ui/select"
  import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
  import {
    Loader2Icon,
    UploadIcon,
    CheckCircleIcon,
    AlertCircleIcon,
    FileTextIcon,
  } from "@/components/icons/public-icons"
  import {
    runDocumentValidation,
    type ValidationResult,
    type ValidationIssue,
    type ValidationOccurrence,
  } from "@/lib/api/pkm"
  import { PKM_SCHEMES } from "@/lib/constants/pkm-schemes"
  import { YearPicker } from "@/components/ui/year-picker"

  const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

  // ── Konfigurasi label per kategori ──────────────────────────────────────────
  // Setiap kategori dari backend (typography, page_layout, dst.) dipetakan ke
  // label tampilan dan emoji untuk panel kiri.
  const CATEGORY_CONFIG: Record<string, { label: string; icon: string }> = {
    typography        : { label: "Typography",       icon: "🔤" },
    page_layout       : { label: "Page Layout",      icon: "📐" },
    spacing           : { label: "Spacing",          icon: "↕"  },
    document_structure: { label: "Struktur Dokumen", icon: "📋" },
    numbering         : { label: "Penomoran",        icon: "🔢" },
    figures_tables    : { label: "Gambar & Tabel",   icon: "📊" },
  }

  // ── Sub-komponen: Summary bar ────────────────────────────────────────────────
  // Empat kotak angka di atas panel: Error, Peringatan, Lulus, Dilewati.
  function SummaryBar({ result }: { result: ValidationResult }) {
    const errors   = result.issues?.filter((i) => i.severity === "error").length   ?? 0
    const warnings = result.issues?.filter((i) => i.severity === "warning").length ?? 0

    const items = [
      { count: errors,   label: "Error",     color: "text-red-600"   },
      { count: warnings, label: "Peringatan", color: "text-yellow-600" },
      { count: result.summary?.passed  ?? 0, label: "Lulus",    color: "text-green-600" },
      { count: result.summary?.errors  ?? 0, label: "Dilewati", color: "text-slate-400" },
    ]

    return (
      <div className="grid grid-cols-4 border-t border-border">
        {items.map(({ count, label, color }, i) => (
          <div
            key={label}
            className={[
              "flex flex-col items-center py-3",
              i < items.length - 1 ? "border-r border-border" : "",
            ].join(" ")}
          >
            <span className={`text-2xl font-bold ${color}`}>{count}</span>
            <span className="text-xs text-muted-foreground mt-0.5">{label}</span>
          </div>
        ))}
      </div>
    )
  }

  // ── Sub-komponen: Kartu lokasi (panel kanan) ─────────────────────────────────
  // Satu kartu = satu kejadian masalah. Menampilkan halaman, BAB, paragraf,
  // cuplikan teks, dan badge nilai salah vs benar.
  function OccurrenceCard({ occ }: { occ: ValidationOccurrence }) {
    return (
      <div className="rounded-lg border border-border bg-white p-3 space-y-2">
        {/* Baris atas: halaman + BAB + paragraf + style */}
        <div className="flex flex-wrap items-center gap-2">
          {occ.page != null && (
            <span className="text-xs font-semibold bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
              📄 Halaman {occ.page}
            </span>
          )}
          {occ.bab && (
            <span className="text-xs font-semibold bg-green-100 text-green-700 px-2 py-0.5 rounded">
              📂 {occ.bab}
            </span>
          )}
          {occ.para_idx != null && (
            <span className="text-xs text-muted-foreground">
              Paragraf ke-{occ.para_idx + 1}
            </span>
          )}
          {occ.style && (
            <span className="text-xs text-muted-foreground">· Style: {occ.style}</span>
          )}
        </div>

        {/* Cuplikan teks paragraf */}
        {occ.text && (
          <p className="text-xs italic text-slate-600 bg-slate-50 px-3 py-2 rounded border-l-2 border-slate-300">
            &ldquo;{occ.text}&rdquo;
          </p>
        )}

        {/* Badge nilai salah vs benar */}
        {(occ.actual || occ.expected) && (
          <div className="flex flex-wrap gap-2">
            {occ.actual && (
              <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">
                ❌ Ditemukan: {occ.actual}
              </span>
            )}
            {occ.expected && (
              <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">
                ✓ Harus: {occ.expected}
              </span>
            )}
          </div>
        )}
      </div>
    )
  }

  // ── Sub-komponen: Panel kiri (daftar masalah) ────────────────────────────────
  // Menampilkan semua masalah dikelompokkan per kategori.
  // `selectedIdx` = index masalah yang sedang aktif (dari allIssues flat list).
  // `onSelect` = callback saat baris diklik.
  function IssueListPanel({
    issues,
    selectedIdx,
    onSelect,
  }: {
    issues: ValidationIssue[]
    selectedIdx: number | null
    onSelect: (idx: number) => void
  }) {
    // Kelompokkan issues per kategori, pertahankan urutan kemunculan
    const grouped = issues.reduce<Record<string, Array<{ issue: ValidationIssue; idx: number }>>>(
      (acc, issue, idx) => {
        const cat = issue.category ?? "other"
        if (!acc[cat]) acc[cat] = []
        acc[cat].push({ issue, idx })
        return acc
      },
      {}
    )

    return (
      <div className="border-r border-border overflow-y-auto">
        <div className="px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide bg-muted/50 border-b border-border">
          Detail Masalah ({issues.length})
        </div>

        {Object.entries(grouped).map(([cat, items]) => {
          const config = CATEGORY_CONFIG[cat] ?? { label: cat, icon: "•" }
          return (
            <div key={cat}>
              {/* Header kategori */}
              <div className="px-4 py-1.5 text-xs font-bold text-muted-foreground/70 uppercase tracking-widest bg-muted/30 border-b border-border/50">
                {config.icon} {config.label}
              </div>

              {/* Baris per masalah */}
              {items.map(({ issue, idx }) => {
                const isActive = selectedIdx === idx
                const isError  = issue.severity === "error"
                return (
                  <button
                    key={idx}
                    onClick={() => onSelect(idx)}
                    className={[
                      "w-full text-left px-4 py-2.5 border-b border-border/50 flex items-start gap-2.5 transition-colors",
                      isActive
                        ? "bg-blue-50 border-l-2 border-l-blue-500"
                        : "hover:bg-muted/40",
                    ].join(" ")}
                  >
                    {/* Badge severity */}
                    <div
                      className={[
                        "shrink-0 size-4 rounded-full flex items-center justify-center text-[10px] font-bold mt-0.5",
                        isError
                          ? "bg-red-100 text-red-700"
                          : "bg-yellow-100 text-yellow-700",
                      ].join(" ")}
                    >
                      {isError ? "!" : "i"}
                    </div>

                    {/* Nama dan keterangan singkat */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{issue.field ?? issue.category}</p>
                      <p className="text-xs text-muted-foreground truncate mt-0.5">{issue.message}</p>
                    </div>

                    {/* Jumlah kejadian */}
                    {(issue.occurrences?.length ?? 0) > 0 && (
                      <span
                        className={[
                          "shrink-0 text-xs font-semibold px-1.5 py-0.5 rounded-full",
                          isError
                            ? "bg-red-100 text-red-700"
                            : "bg-yellow-100 text-yellow-700",
                        ].join(" ")}
                      >
                        {issue.occurrences!.length}×
                      </span>
                    )}
                  </button>
                )
              })}
            </div>
          )
        })}
      </div>
    )
  }

  // ── Sub-komponen: Panel kanan (detail lokasi) ────────────────────────────────
  // Jika `issue` ada → tampilkan kartu lokasi dari issue.occurrences.
  // Jika null → tampilkan pesan "pilih masalah di kiri".
  function LocationPanel({ issue }: { issue: ValidationIssue | null }) {
    if (!issue) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[300px] text-muted-foreground bg-muted/20">
          <FileTextIcon className="size-8 mb-3 opacity-30" />
          <p className="text-sm">Klik salah satu masalah di kiri untuk melihat lokasi</p>
        </div>
      )
    }

    const occurrences = issue.occurrences ?? []

    return (
      <div className="overflow-y-auto bg-muted/10">
        {/* Header panel kanan */}
        <div className="px-5 py-3 border-b border-border bg-white sticky top-0">
          <p className="text-sm font-semibold">
            {issue.field ?? issue.category}
            {occurrences.length > 0 && (
              <span className="ml-2 text-xs font-normal text-muted-foreground">
                — {occurrences.length} lokasi ditemukan
              </span>
            )}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">{issue.message}</p>
        </div>

        {/* Daftar kartu lokasi */}
        <div className="p-4 space-y-3">
          {occurrences.length > 0 ? (
            occurrences.map((occ, i) => <OccurrenceCard key={i} occ={occ} />)
          ) : (
            // Tidak ada occurrences (masalah level dokumen, misal margin)
            <div className="rounded-lg border border-border bg-white p-4">
              <p className="text-sm text-muted-foreground">
                Masalah ini berlaku untuk seluruh dokumen, bukan paragraf tertentu.
              </p>
              {(issue.expected || issue.actual) && (
                <div className="flex flex-wrap gap-2 mt-3">
                  {issue.actual && (
                    <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">
                      ❌ Ditemukan: {issue.actual}
                    </span>
                  )}
                  {issue.expected && (
                    <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">
                      ✓ Harus: {issue.expected}
                    </span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    )
  }

  // ── Komponen utama ───────────────────────────────────────────────────────────
  export function DocumentValidator() {
    const [selectedSchemaId, setSelectedSchemaId] = useState<string>("")
    const [selectedYear, setSelectedYear]         = useState<string>("")
    const [file, setFile]                         = useState<File | null>(null)
    const [loading, setLoading]                   = useState(false)
    const [result, setResult]                     = useState<ValidationResult | null>(null)
    const [error, setError]                       = useState<string | null>(null)
    // selectedIssueIdx: index masalah yang sedang aktif di panel kiri (null = belum dipilih)
    const [selectedIssueIdx, setSelectedIssueIdx] = useState<number | null>(null)

    const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = e.target.files?.[0]
      if (selected) {
        if (selected.size > MAX_FILE_SIZE) {
          setError("Ukuran file terlalu besar. Maksimal 10MB.")
          setFile(null)
          return
        }
        const isDocx =
          selected.type === "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ||
          selected.name.toLowerCase().endsWith(".docx")
        if (!isDocx) {
          setError("Hanya file DOCX yang diterima.")
          setFile(null)
          return
        }
        setError(null)
        setFile(selected)
        setResult(null)
        setSelectedIssueIdx(null)
      }
    }, [])

    const handleDrop = useCallback((e: React.DragEvent) => {
      e.preventDefault()
      const dropped = e.dataTransfer.files?.[0]
      if (dropped) {
        const fakeEvent = { target: { files: [dropped] } } as unknown as React.ChangeEvent<HTMLInputElement>
        handleFileChange(fakeEvent)
      }
    }, [handleFileChange])

    const handleDragOver = useCallback((e: React.DragEvent) => {
      e.preventDefault()
    }, [])

    const handleValidate = async () => {
      if (!selectedSchemaId || !selectedYear || !file) {
        setError("Pilih skema PKM, tahun, dan upload file proposal terlebih dahulu.")
        return
      }
      setLoading(true)
      setError(null)
      setResult(null)
      setSelectedIssueIdx(null)

      const res = await runDocumentValidation({ schemaId: selectedSchemaId, year: selectedYear, file })
      setLoading(false)

      if (res.error) {
        setError(res.error)
      } else {
        setResult(res.data)
      }
    }

    const handleReset = () => {
      setSelectedSchemaId("")
      setSelectedYear("")
      setFile(null)
      setResult(null)
      setError(null)
      setSelectedIssueIdx(null)
    }

    const allIssues = result?.issues ?? []

    return (
      <ReviewerSurfaceCard>
        {/* ── Header ── */}
        <div className="px-6 pt-6 pb-4">
          <h3 className="text-base font-semibold flex items-center gap-2">
            <FileTextIcon className="size-5 text-primary" />
            Validasi Dokumen Otomatis
          </h3>
        </div>

        {/* ── Form upload ── */}
        <div className="px-6 pb-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">1. Pilih Skema PKM</label>
              <Select value={selectedSchemaId} onValueChange={setSelectedSchemaId}>
                <SelectTrigger>
                  <SelectValue placeholder="Pilih jenis PKM" />
                </SelectTrigger>
                <SelectContent>
                  {PKM_SCHEMES.map((schema) => (
                    <SelectItem key={schema.value} value={schema.value}>
                      {schema.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">2. Pilih Tahun</label>
              <YearPicker
                value={selectedYear}
                onChange={setSelectedYear}
                placeholder="Pilih tahun"
                disabled={loading}
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">3. Upload Proposal</label>
            <div
              className={[
                "relative rounded-lg border-2 border-dashed p-6 transition-colors",
                file
                  ? "border-primary bg-primary/5"
                  : "border-muted-foreground/25 hover:border-muted-foreground/50",
              ].join(" ")}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
            >
              <input
                type="file"
                accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={handleFileChange}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                disabled={loading}
              />
              <div className="flex flex-col items-center text-center">
                {file ? (
                  <>
                    <FileTextIcon className="size-8 text-primary mb-2" />
                    <p className="text-sm font-medium">{file.name}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); setFile(null); setResult(null) }}
                      className="mt-2 text-xs text-destructive hover:underline"
                    >
                      Hapus file
                    </button>
                  </>
                ) : (
                  <>
                    <UploadIcon className="size-8 text-muted-foreground mb-2" />
                    <p className="text-sm text-muted-foreground">
                      Seret file ke sini atau klik untuk memilih
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">Format: DOCX, maks 10MB</p>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button
              onClick={handleValidate}
              disabled={!selectedSchemaId || !selectedYear || !file || loading}
              className="flex-1 sm:flex-none"
            >
              {loading ? (
                <>
                  <Loader2Icon className="size-4 animate-spin" />
                  <span>Memvalidasi...</span>
                </>
              ) : (
                <>
                  <CheckCircleIcon className="size-4" />
                  <span>Validasi Dokumen</span>
                </>
              )}
            </Button>

            {result && (
              <Button variant="outline" onClick={handleReset}>
                Reset
              </Button>
            )}
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertCircleIcon className="size-4" />
              <AlertTitle>Error</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>

        {/* ── Hasil validasi ── */}
        {result && (
          <>
            {/* Alert status */}
            <div className="px-6 pb-4">
              {result.valid ? (
                <Alert className="border-green-200 bg-green-50">
                  <CheckCircleIcon className="size-4 text-green-600" />
                  <AlertTitle className="text-green-800">Dokumen Valid</AlertTitle>
                  <AlertDescription className="text-green-700">
                    Dokumen proposal telah memenuhi semua persyaratan format.
                    {result.summary && (
                      <span className="ml-1">
                        ({result.summary.passed ?? 0} dari {result.summary.total_checks ?? 0} pemeriksaan lulus)
                      </span>
                    )}
                  </AlertDescription>
                </Alert>
              ) : (
                <Alert variant="destructive">
                  <AlertCircleIcon className="size-4" />
                  <AlertTitle>Ditemukan Masalah Format</AlertTitle>
                  <AlertDescription>
                    {allIssues.filter((i) => i.severity === "error").length} error,{" "}
                    {allIssues.filter((i) => i.severity === "warning").length} peringatan ditemukan.
                  </AlertDescription>
                </Alert>
              )}
            </div>

            {/* Summary bar + two-panel */}
            {allIssues.length > 0 && (
              <div className="border-t border-border">
                <SummaryBar result={result} />
                <div className="grid grid-cols-[320px_1fr] border-t border-border min-h-[360px] max-h-[600px]">
                  <IssueListPanel
                    issues={allIssues}
                    selectedIdx={selectedIssueIdx}
                    onSelect={setSelectedIssueIdx}
                  />
                  <LocationPanel
                    issue={selectedIssueIdx !== null ? allIssues[selectedIssueIdx] : null}
                  />
                </div>
              </div>
            )}
          </>
        )}
      </ReviewerSurfaceCard>
    )
  }
  ```

- [ ] **Step 5.2 — Pastikan tidak ada TypeScript error**

  ```bash
  cd frontend
  npx tsc --noEmit
  ```

  Hasil yang diharapkan: tidak ada error.

- [ ] **Step 5.3 — Jalankan dev server dan test manual**

  ```bash
  cd frontend
  npm run dev
  ```

  Buka `http://localhost:3000/reviewer/validation`. Lakukan test manual:
  1. Upload file DOCX proposal PKM yang punya masalah format
  2. Pastikan panel kiri muncul dengan daftar masalah per kategori
  3. Klik satu masalah → panel kanan menampilkan kartu lokasi dengan Halaman, BAB, Paragraf
  4. Klik masalah lain → panel kanan berubah
  5. Pastikan badge merah (ditemukan) dan hijau (harus) muncul di setiap kartu

- [ ] **Step 5.4 — Commit**

  ```bash
  git add frontend/components/reviewer/DocumentValidator.tsx
  git commit -m "feat(frontend): redesign validation UI with two-panel layout and location cards"
  ```

---

## Verifikasi Akhir

- [ ] Jalankan semua backend test sekaligus:

  ```bash
  cd "ai/model"
  python -m pytest tests/test_validation_location.py -v
  ```

  Semua test harus `PASSED`.

- [ ] Jalankan TypeScript check frontend:

  ```bash
  cd frontend
  npx tsc --noEmit
  ```

  Harus 0 error.

- [ ] Test integrasi manual: upload file DOCX nyata, pastikan `occurrences` terisi dan kartu lokasi muncul dengan data yang benar.
