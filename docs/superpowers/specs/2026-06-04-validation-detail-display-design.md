# Design Spec: Tampilan Validasi Detail dengan Lokasi

**Tanggal:** 2026-06-04  
**Status:** Approved  
**Scope:** Backend enrichment + Frontend two-panel UI

---

## Ringkasan

Tampilan validasi saat ini menampilkan daftar masalah yang flat dan tidak menunjukkan lokasi spesifik (halaman, BAB, paragraf mana). Tujuan perubahan ini: setiap masalah validasi harus bisa dilacak ke lokasi pastinya di dalam dokumen — supaya user (reviewer) bisa langsung buka dokumen di bagian yang bermasalah tanpa harus mencari-cari sendiri.

---

## Bagian 1 — Perubahan Backend (Python)

### 1A. Deteksi nomor halaman dari file DOCX

**File:** `ai/model/model_ai/validation/validocx/debug_report.py`

Fungsi `_get_para_details()` yang sudah ada saat ini mengambil info per paragraf (style, teks, spasi, dll.) tetapi **tidak melacak nomor halaman**. Kita tambahkan logika pelacakan halaman.

**Cara kerjanya:**
- Buka XML mentah DOCX menggunakan `python-docx`
- Scan setiap paragraf dari atas ke bawah
- Setiap kali ditemukan elemen `<w:lastRenderedPageBreak>` atau `<w:br w:type="page">` di dalam paragraf, nomor halaman bertambah 1
- Simpan nomor halaman ke setiap entri paragraf di `result[idx]`

**Contoh hasil yang ditambahkan ke `result[idx]`:**
```python
result[idx]["page"] = 3  # paragraf ini ada di halaman 3
```

### 1B. Deteksi nama BAB dari Heading 1

**File:** `ai/model/model_ai/validation/validocx/debug_report.py`

Saat scan paragraf di `_get_para_details()`, kita lacak Heading 1 terakhir yang ditemukan sebelum paragraf saat ini. Itu adalah nama BAB-nya.

**Cara kerjanya:**
- Variabel `current_bab` dimulai dari `None`
- Setiap paragraf dengan `style.name == "Heading 1"` → update `current_bab` dengan teksnya
- Setiap paragraf lain → simpan `current_bab` sebagai nilai `"bab"` di `result[idx]`

**Contoh hasil:**
```python
result[idx]["bab"] = "BAB 1 PENDAHULUAN"
```

### 1C. Propagasi info halaman & BAB ke `ValidationIssue`

**File:** `ai/model/model_ai/validation/validocx_runner.py`

Fungsi `_para_location()` saat ini hanya mengembalikan string seperti `"Paragraf ke-5 (style: Normal)"`. Kita ubah agar menghasilkan string yang lebih lengkap:

```
"Halaman 3 · BAB 1 PENDAHULUAN · Paragraf ke-5"
```

Dan kita tambahkan field baru `paragraph_details` yang berisi list detail lengkap setiap paragraf bermasalah — ini yang akan dipakai frontend untuk menampilkan kartu lokasi.

**Perubahan pada `ValidationIssue` model:**  
**File:** `ai/model/model_ai/validation/models.py`

Tambah field baru `occurrences` — list lokasi spesifik tempat masalah ini terjadi:

```python
occurrences: list[dict] | None = Field(
    default=None,
    description="List lokasi paragraf bermasalah, masing-masing berisi page, bab, para_idx, style, text, actual, expected"
)
```

Setiap item `occurrences` berisi:
```json
{
  "page": 3,
  "bab": "BAB 1 PENDAHULUAN",
  "para_idx": 4,
  "style": "Normal",
  "text": "Latar belakang penelitian ini...",
  "actual": "11.0pt, Times New Roman",
  "expected": "12pt, Times New Roman"
}
```

---

## Bagian 2 — Perubahan Frontend (TypeScript/React)

### 2A. Update type definisi `ValidationIssue`

**File:** `frontend/lib/api/pkm.ts` (atau file type definitions)

Tambah field `occurrences` ke type `ValidationIssue`:

```typescript
occurrences?: Array<{
  page: number
  bab: string | null
  para_idx: number
  style: string
  text: string
  actual?: string
  expected?: string
}>
```

### 2B. Redesign komponen `DocumentValidator.tsx`

**File:** `frontend/components/reviewer/DocumentValidator.tsx`

**Perubahan struktur UI:**

1. **Summary bar** (baru) — empat kotak kecil di atas: jumlah Error, Peringatan, Lulus, Dilewati
2. **Two-panel layout** — menggantikan daftar flat saat ini:
   - **Panel kiri (lebar 320px):** daftar masalah dikelompokkan per kategori (Typography, Page Layout, Spacing), setiap baris menampilkan nama masalah + jumlah kejadian + badge severity
   - **Panel kanan (sisa lebar):** ketika user klik satu baris di kiri, tampilkan kartu-kartu lokasi

3. **Kartu lokasi** — setiap kartu menampilkan:
   - Badge biru: nomor halaman (`Halaman 3`)
   - Badge hijau: nama BAB (`BAB 1 PENDAHULUAN`)
   - Teks abu: nomor paragraf + nama style
   - Kotak abu: cuplikan teks paragraf (italic)
   - Badge merah: nilai yang ditemukan (`❌ Ditemukan: 11.0pt`)
   - Badge hijau: nilai yang seharusnya (`✓ Harus: 12pt`)

**State baru yang dibutuhkan:**
```typescript
const [selectedIssueIndex, setSelectedIssueIndex] = useState<number | null>(null)
```
— menyimpan index masalah yang sedang diklik di panel kiri. Dipakai untuk menentukan apa yang ditampilkan di panel kanan.

---

## Bagian 3 — Alur Data End-to-End

```
DOCX file
  ↓
_get_para_details()          ← BARU: tambah page + bab per paragraf
  ↓
_inject_para_details()       ← sudah ada, sekarang bawa page+bab juga
  ↓
_build_issues_checks()       ← BARU: isi field occurrences di ValidationIssue
  ↓
ValidationIssue.occurrences  ← field baru berisi list lokasi lengkap
  ↓
API response JSON
  ↓
Frontend: panel kiri + panel kanan ← BARU: two-panel UI
```

---

## Batasan & Catatan

- **Nomor halaman dari `lastRenderedPageBreak`** hanya akurat jika file pernah dibuka/disimpan oleh Microsoft Word. Jika dokumen belum pernah dirender, hanya `<w:br type="page">` (page break manual) yang bisa diandalkan. Dalam kasus dokumen mahasiswa yang dikirim dari Word, ini hampir selalu tersedia.
- **Tidak ada perubahan pada logika validasi** — hanya enrichment data lokasi dan perubahan tampilan.
- **Backward compatible** — field `occurrences` bersifat opsional (`| None`), jadi tidak merusak kode yang sudah ada.
