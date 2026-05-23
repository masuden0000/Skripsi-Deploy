# Validator Integration Design

**Date:** 2026-05-23  
**Feature:** Integrasi pipeline validator AI ke menu "Validasi Dokumen" reviewer  
**Status:** Approved

---

## Overview

Mengintegrasikan pipeline validator yang sudah ada di `ai/model_ai/validation/` ke dalam frontend reviewer melalui menu "Validasi Dokumen". Reviewer dapat mengupload DOCX proposal mahasiswa, memilih skema PKM, dan sistem akan memvalidasi format dokumen terhadap aturan yang tersimpan di database.

---

## Architecture

```
Browser (Reviewer)
  → POST /api/pkm/validation/run  (Next.js API route)
  → POST /api/pkm/validation/run  (Express backend proxy)
  → POST /api/validation/run      (FastAPI AI backend)
  → validate_document()           (ai/model_ai/validation)
  → ValidationResult JSON
  → Tampil di DocumentValidator UI
```

**Schema dropdown flow:**
```
Browser → GET /api/pkm/schemas (Next.js) → GET /api/pkm/schemas (Express) → Supabase pkm_schemas
```

---

## Key Decisions

1. **Schema selection**: Reviewer memilih jenis skema PKM (PKM-K, PKM-M, dll.). Tahun otomatis dari active review period di Supabase.
2. **Proxy pattern**: Mengikuti pola yang ada — Next.js → Express → FastAPI.
3. **File format**: DOCX (bukan PDF). `DocumentValidator.tsx` diupdate agar accept `.docx`.
4. **ValidationResult format**: Menggunakan format kaya dari Python — tiap issue punya `category`, `severity`, `field`, `message`, `expected`, `actual`. TypeScript schema diupdate.

---

## Files

### Frontend (5 file)

| File | Aksi |
|------|------|
| `frontend/app/(dashboard)/reviewer/validation/page.tsx` | CREATE — halaman wrapper `DocumentValidator` |
| `frontend/app/api/pkm/validation/run/route.ts` | CREATE — Next.js proxy POST → Express |
| `frontend/app/api/pkm/schemas/route.ts` | CREATE — Next.js proxy GET → Express |
| `frontend/components/reviewer/DocumentValidator.tsx` | EDIT — ganti accept PDF → DOCX |
| `frontend/lib/api/pkm.ts` | EDIT — update `validationResultSchema` |

### Express (2 file)

| File | Aksi |
|------|------|
| `backend/src/routes/pkm.routes.js` | CREATE — GET schemas, POST validation proxy |
| `backend/src/app.js` | EDIT — register pkm routes |

### FastAPI (2 file)

| File | Aksi |
|------|------|
| `ai-backend/routers/validation.py` | CREATE — endpoint POST /api/validation/run |
| `ai-backend/main.py` | EDIT — register validation router |

---

## Data Contracts

### POST /api/validation/run (FastAPI)

**Request:** `multipart/form-data`
- `file`: DOCX file
- `schema_id`: string (UUID pkm_schemas.id)

**Response:** JSON
```json
{
  "valid": true,
  "status": "pass",
  "summary": { "total": 12, "passed": 12, "failed": 0, "warnings": 0 },
  "issues": [
    {
      "severity": "error",
      "category": "typography",
      "field": "font_family",
      "message": "Font tidak sesuai: ditemukan Arial, diharapkan Times New Roman",
      "expected": "Times New Roman",
      "actual": "Arial"
    }
  ]
}
```

### GET /api/pkm/schemas (Express)

**Response:** JSON
```json
{
  "data": [
    { "id": "uuid", "nama": "PKM Kewirausahaan", "singkatan": "PKM-K", "createdAt": "...", "updatedAt": "..." }
  ]
}
```

---

## FastAPI Validation Logic

```python
# ai-backend/routers/validation.py
@router.post("/run")
async def run_validation(file: UploadFile, schema_id: str):
    # 1. Fetch active review period → get year
    active_period = await db.fetch_active_period()
    year = active_period["tahun"]

    # 2. Fetch document_metadata for schema + year
    metadata = await db.fetch_document_metadata(schema_id=schema_id, year=year)
    if not metadata:
        raise HTTPException(404, "Metadata tidak ditemukan untuk skema ini")

    # 3. Save DOCX to temp file
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # 4. Run validation
    try:
        from model_ai.validation import validate_document
        result = validate_document(tmp_path, metadata["payload"])
    finally:
        os.unlink(tmp_path)

    # 5. Return result
    return result.to_dict()
```

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Metadata tidak ditemukan untuk skema + tahun | 404 dari FastAPI, pesan jelas di UI |
| Tidak ada active review period | 422 dari FastAPI |
| File bukan DOCX | 400 dari FastAPI (validasi MIME type) |
| File > 10MB | Ditolak di frontend sebelum upload |
| FastAPI tidak bisa dijangkau | Error message di UI |

---

## Scope Exclusion

- Tidak ada penyimpanan hasil validasi ke database (stateless per-request)
- Tidak ada riwayat validasi
- Tidak ada notifikasi/email setelah validasi
