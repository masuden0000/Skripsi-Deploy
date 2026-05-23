# Validator Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mengintegrasikan pipeline validator AI (`ai/model_ai/validation/`) ke menu "Validasi Dokumen" reviewer melalui stack Next.js → Express → FastAPI.

**Architecture:** Reviewer upload DOCX + pilih skema PKM → Next.js API route proxy ke Express → Express proxy ke FastAPI → FastAPI query Supabase untuk rules (active period + document_metadata) → jalankan `validate_document()` dari Python → return ValidationResult JSON → tampil di UI.

**Tech Stack:** FastAPI (Python), Express.js (Node.js), Next.js 15 (TypeScript), Supabase, python-docx

---

## File Map

| File | Aksi | Tanggung Jawab |
|------|------|----------------|
| `ai-backend/routers/validation.py` | CREATE | FastAPI endpoint POST /api/validation/run |
| `ai-backend/main.py` | EDIT | Register validation router |
| `backend/src/routes/pkm.routes.js` | CREATE | Express: GET /schemas, POST /validation/run proxy |
| `backend/src/app.js` | EDIT | Register pkm routes + raw middleware |
| `frontend/app/api/pkm/validation/run/route.ts` | CREATE | Next.js API route proxy → Express |
| `frontend/app/api/pkm/schemas/route.ts` | CREATE | Next.js API route proxy → Express |
| `frontend/lib/api/pkm.ts` | EDIT | Update ValidationResult schema → issues[] |
| `frontend/components/reviewer/DocumentValidator.tsx` | EDIT | Accept DOCX, tampilkan issues baru |
| `frontend/app/(dashboard)/reviewer/validation/page.tsx` | CREATE | Halaman reviewer/validation |

---

## Task 1: FastAPI Validation Router

**Files:**
- Create: `ai-backend/routers/validation.py`
- Modify: `ai-backend/main.py`

- [ ] **Step 1.1: Buat file `ai-backend/routers/validation.py`**

```python
import os
import sys
import tempfile
from datetime import date

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from services.database import get_supabase

# Tambah ai/ ke sys.path agar bisa import model_ai.validation
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_AI_DIR = os.path.join(_PROJECT_ROOT, "ai")
if _AI_DIR not in sys.path:
    sys.path.insert(0, _AI_DIR)

router = APIRouter()

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.post("/run")
async def run_validation(
    schema_id: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Validasi format DOCX proposal mahasiswa terhadap aturan yang tersimpan
    di document_metadata untuk skema dan tahun periode review aktif.
    """
    # Validasi tipe file
    if not (file.filename or "").lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="File harus berformat DOCX (.docx).")

    supabase = get_supabase()
    today = date.today().isoformat()

    # 1. Fetch active review period → ambil tahun dari tanggal_mulai
    period_result = (
        supabase.table("pkm_review_periods")
        .select("id, nama, tanggal_mulai")
        .lte("tanggal_mulai", today)
        .gte("tanggal_selesai", today)
        .limit(1)
        .execute()
    )
    if not period_result.data:
        raise HTTPException(
            status_code=422,
            detail="Tidak ada periode review yang aktif saat ini.",
        )
    year = period_result.data[0]["tanggal_mulai"][:4]

    # 2. Fetch singkatan skema dari pkm_schemas
    schema_result = (
        supabase.table("pkm_schemas")
        .select("singkatan")
        .eq("id", schema_id)
        .limit(1)
        .execute()
    )
    if not schema_result.data:
        raise HTTPException(status_code=404, detail="Skema PKM tidak ditemukan.")
    singkatan = schema_result.data[0]["singkatan"]

    # 3. Cari project untuk skema + tahun (ambil yang terbaru)
    project_result = (
        supabase.table("projects")
        .select("id")
        .eq("skema", singkatan)
        .eq("tahun", year)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not project_result.data:
        raise HTTPException(
            status_code=404,
            detail=f"Data referensi untuk {singkatan} tahun {year} belum tersedia.",
        )
    project_id = project_result.data[0]["id"]

    # 4. Ambil payload document_metadata
    metadata_result = (
        supabase.table("document_metadata")
        .select("payload")
        .eq("project_id", project_id)
        .limit(1)
        .execute()
    )
    if not metadata_result.data:
        raise HTTPException(
            status_code=404,
            detail="Metadata format dokumen belum tersedia. Pastikan pipeline ekstraksi sudah selesai.",
        )
    payload = metadata_result.data[0]["payload"]

    # 5. Simpan DOCX ke temp file, jalankan validator, hapus temp
    content = await file.read()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        from model_ai.validation import validate_document
        result = validate_document(tmp_path, payload)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # 6. Ubah ValidationResult ke dict dengan field `valid` tambahan
    result_dict = result.to_dict()
    result_dict["valid"] = result_dict.get("status") == "pass"
    return result_dict
```

- [ ] **Step 1.2: Register router di `ai-backend/main.py`**

Tambahkan dua baris berikut ke file yang sudah ada:

```python
# Tambah import (letakkan bersama import routers lain)
from routers import projects, health, validation

# Tambah include_router (letakkan setelah router yang sudah ada)
app.include_router(validation.router, prefix="/api/validation")
```

File `main.py` setelah edit:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import projects, health, validation

app = FastAPI(
    title="AI Proposal Backend",
    description="Backend for PKM Proposal Generator",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(projects.router, prefix="/api/projects")
app.include_router(validation.router, prefix="/api/validation")


@app.get("/")
async def root():
    return {"message": "AI Proposal Backend is running", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

- [ ] **Step 1.3: Verifikasi endpoint tersedia**

Jalankan FastAPI (dari direktori `ai-backend/`):
```bash
cd ai-backend
uvicorn main:app --reload --port 8000
```

Buka `http://localhost:8000/docs` dan pastikan endpoint `POST /api/validation/run` muncul di Swagger UI.

- [ ] **Step 1.4: Commit**

```bash
git add ai-backend/routers/validation.py ai-backend/main.py
git commit -m "feat: add FastAPI validation endpoint POST /api/validation/run"
```

---

## Task 2: Express PKM Routes

**Files:**
- Create: `backend/src/routes/pkm.routes.js`
- Modify: `backend/src/app.js`

- [ ] **Step 2.1: Buat `backend/src/routes/pkm.routes.js`**

```js
import { Router } from "express"
import { adminClient } from "../config/supabase.js"
import { env } from "../config/env.js"

const router = Router()

async function parseAiResponse(aiResponse) {
  const text = await aiResponse.text()
  try {
    return { data: JSON.parse(text), status: aiResponse.status }
  } catch {
    return {
      data: { error: text || "AI backend returned non-JSON response" },
      status: aiResponse.status || 502,
    }
  }
}

// GET /api/pkm/schemas - Daftar skema PKM dari Supabase
router.get("/schemas", async (req, res, next) => {
  try {
    const { data, error } = await adminClient
      .from("pkm_schemas")
      .select("id, nama, singkatan, created_at, updated_at")
      .order("nama", { ascending: true })

    if (error) {
      return res.status(500).json({ error: "Gagal mengambil daftar skema PKM." })
    }

    const mapped = (data ?? []).map((row) => ({
      id: row.id,
      nama: row.nama,
      singkatan: row.singkatan,
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    }))

    res.json({ data: mapped })
  } catch (error) {
    next(error)
  }
})

// POST /api/pkm/validation/run - Proxy ke FastAPI
router.post("/validation/run", async (req, res, next) => {
  try {
    const rawBody = req.body
    const contentType = req.headers["content-type"] || ""

    const aiResponse = await fetch(`${env.AI_BACKEND_URL}/api/validation/run`, {
      method: "POST",
      body: rawBody,
      headers: { "Content-Type": contentType },
    })

    const { data, status } = await parseAiResponse(aiResponse)
    res.status(status).json(data)
  } catch (error) {
    console.error("[PkmRoute] Error proxying validation:", error)
    res.status(500).json({
      error: error instanceof Error ? error.message : "Gagal terhubung ke AI backend.",
    })
  }
})

export default router
```

- [ ] **Step 2.2: Edit `backend/src/app.js`**

Tambahkan 3 bagian ke file yang ada:

1. Import di bagian atas (tambah bersama import routes lain):
```js
import pkmRoutes from "./routes/pkm.routes.js"
```

2. Middleware raw untuk multipart validation (tambah setelah baris middleware projects):
```js
// Letakkan setelah: app.use("/api/projects", express.raw(...))
app.use("/api/pkm/validation/run", express.raw({ type: "multipart/form-data", limit: "20mb" }))
```

3. Route (tambah bersama route lain):
```js
app.use("/api/pkm", pkmRoutes)
```

File `app.js` lengkap setelah semua perubahan:
```js
import cookieParser from "cookie-parser"
import cors from "cors"
import express from "express"
import { env } from "./config/env.js"
import assignmentsRoutes from "./routes/assignments.routes.js"
import reviewerAssignmentsRoutes from "./routes/reviewer-assignments.routes.js"
import authRoutes from "./routes/auth.routes.js"
import facultyRoutes from "./routes/faculty.routes.js"
import pkmRoutes from "./routes/pkm.routes.js"
import projectsRoutes from "./routes/projects.routes.js"
import reviewPeriodRoutes from "./routes/review-period.routes.js"
import reviewerRoutes from "./routes/reviewer.routes.js"
import { errorHandler, notFoundHandler } from "./middlewares/error-handler.js"

const app = express()
const allowedOrigins = new Set(env.FRONTEND_URLS)

app.use(
  cors({
    origin(origin, callback) {
      if (!origin || allowedOrigins.has(origin)) {
        callback(null, true)
        return
      }
      callback(new Error(`Origin tidak diizinkan oleh CORS: ${origin}`))
    },
    credentials: true,
  })
)
app.use(express.json())
app.use(cookieParser())

app.use("/api/projects", express.raw({ type: "multipart/form-data", limit: "50mb" }))
app.use("/api/pkm/validation/run", express.raw({ type: "multipart/form-data", limit: "20mb" }))

app.get("/", (_req, res) => {
  res.status(200).json({
    ok: true,
    service: "backend",
    message: "Backend aktif. Gunakan /api/health untuk health check.",
  })
})

app.get("/api/health", (_req, res) => {
  res.status(200).json({ ok: true, service: "backend" })
})

app.use("/api/assignments", assignmentsRoutes)
app.use("/api/reviewer-assignments", reviewerAssignmentsRoutes)
app.use("/api/auth", authRoutes)
app.use("/api/faculties", facultyRoutes)
app.use("/api/pkm", pkmRoutes)
app.use("/api/projects", projectsRoutes)
app.use("/api/review-periods", reviewPeriodRoutes)
app.use("/api/reviewers", reviewerRoutes)

app.use(notFoundHandler)
app.use(errorHandler)

export default app
```

- [ ] **Step 2.3: Test Express schemas endpoint**

Jalankan Express backend dan test:
```bash
# Di terminal, jalankan backend
cd backend && node src/server.js

# Di terminal lain, test endpoint
curl http://localhost:4000/api/pkm/schemas
```

Expected response:
```json
{ "data": [ { "id": "...", "nama": "PKM Kewirausahaan", "singkatan": "PKM-K", ... } ] }
```

Jika tabel `pkm_schemas` kosong, response: `{ "data": [] }` — tetap OK.

- [ ] **Step 2.4: Commit**

```bash
git add backend/src/routes/pkm.routes.js backend/src/app.js
git commit -m "feat: add Express PKM routes for schemas and validation proxy"
```

---

## Task 3: Next.js API Routes

**Files:**
- Create: `frontend/app/api/pkm/schemas/route.ts`
- Create: `frontend/app/api/pkm/validation/run/route.ts`

- [ ] **Step 3.1: Buat direktori dan file schemas route**

Buat `frontend/app/api/pkm/schemas/route.ts`:

```typescript
import { NextResponse } from "next/server"
import { getBackendBaseUrl } from "@/lib/backend-api"

function buildResponse(backendResponse: Response, responseText: string) {
  return new NextResponse(responseText, {
    status: backendResponse.status,
    headers: {
      "content-type": backendResponse.headers.get("content-type") ?? "application/json",
    },
  })
}

export async function GET() {
  const backendResponse = await fetch(`${getBackendBaseUrl()}/api/pkm/schemas`, {
    method: "GET",
    headers: { "content-type": "application/json" },
    cache: "no-store",
  })

  const responseText = await backendResponse.text()
  return buildResponse(backendResponse, responseText)
}
```

- [ ] **Step 3.2: Buat validation run route**

Buat `frontend/app/api/pkm/validation/run/route.ts`:

```typescript
import { NextResponse } from "next/server"
import { getBackendBaseUrl } from "@/lib/backend-api"

function buildResponse(backendResponse: Response, responseText: string) {
  return new NextResponse(responseText, {
    status: backendResponse.status,
    headers: {
      "content-type": backendResponse.headers.get("content-type") ?? "application/json",
    },
  })
}

export async function POST(request: Request) {
  const formData = await request.formData()

  const backendResponse = await fetch(
    `${getBackendBaseUrl()}/api/pkm/validation/run`,
    {
      method: "POST",
      body: formData,
      cache: "no-store",
    }
  )

  const responseText = await backendResponse.text()
  return buildResponse(backendResponse, responseText)
}
```

- [ ] **Step 3.3: Test schemas endpoint dari Next.js**

Jalankan Next.js dev server dan test:
```bash
cd frontend && npm run dev
```

Akses `http://localhost:3000/api/pkm/schemas` di browser.

Expected: JSON dengan daftar skema PKM (atau `{"data":[]}` jika tabel kosong).

- [ ] **Step 3.4: Commit**

```bash
git add frontend/app/api/pkm/schemas/route.ts frontend/app/api/pkm/validation/run/route.ts
git commit -m "feat: add Next.js API proxy routes for PKM schemas and validation"
```

---

## Task 4: Update ValidationResult Schema di pkm.ts

**Files:**
- Modify: `frontend/lib/api/pkm.ts`

- [ ] **Step 4.1: Update `validationResultSchema` dan `ValidationResult` type**

Di `frontend/lib/api/pkm.ts`, ganti bagian schema validation:

```typescript
// Ganti validationResultSchema yang lama dengan ini:
export const validationIssueSchema = z.object({
  severity: z.enum(["error", "warning", "info"]),
  category: z.string(),
  field: z.string().optional().nullable(),
  message: z.string(),
  expected: z.string().optional().nullable(),
  actual: z.string().optional().nullable(),
})

export const validationSummarySchema = z.object({
  total_checks: z.number().optional(),
  passed: z.number().optional(),
  failed: z.number().optional(),
  warnings: z.number().optional(),
  errors: z.number().optional(),
})

export const validationResultSchema = z.object({
  valid: z.boolean(),
  status: z.enum(["pass", "fail", "warning"]),
  issues: z.array(validationIssueSchema).optional().default([]),
  summary: validationSummarySchema.optional(),
  validated_at: z.string().optional(),
})
```

Dan update type exports:
```typescript
export type ValidationIssue = z.infer<typeof validationIssueSchema>
export type ValidationResult = z.infer<typeof validationResultSchema>
```

- [ ] **Step 4.2: Verifikasi tidak ada TypeScript error**

```bash
cd frontend && npx tsc --noEmit
```

Expected: Tidak ada error yang berhubungan dengan `pkm.ts` atau `ValidationResult`.

- [ ] **Step 4.3: Commit**

```bash
git add frontend/lib/api/pkm.ts
git commit -m "feat: update ValidationResult schema to match Python validator output"
```

---

## Task 5: Update DocumentValidator Component

**Files:**
- Modify: `frontend/components/reviewer/DocumentValidator.tsx`

- [ ] **Step 5.1: Ubah file accept dari PDF ke DOCX**

Di `frontend/components/reviewer/DocumentValidator.tsx`, buat 3 perubahan:

**Perubahan 1** — input accept attribute (cari `accept=".pdf,application/pdf"`):
```tsx
// Sebelum:
accept=".pdf,application/pdf"

// Sesudah:
accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
```

**Perubahan 2** — validasi tipe file (cari `selected.type !== "application/pdf"`):
```tsx
// Sebelum:
if (selected.type !== "application/pdf") {
  setError("Hanya file PDF yang diterima.")

// Sesudah:
const isDocx =
  selected.type === "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ||
  selected.name.toLowerCase().endsWith(".docx")
if (!isDocx) {
  setError("Hanya file DOCX yang diterima.")
```

**Perubahan 3** — hint text (cari `Format: PDF, maks 10MB`):
```tsx
// Sebelum:
Format: PDF, maks 10MB

// Sesudah:
Format: DOCX, maks 10MB
```

- [ ] **Step 5.2: Update tampilan hasil validasi agar pakai schema baru**

Ganti seluruh blok `{result && (...)}` di bagian bawah component:

```tsx
{result && (
  <div className="space-y-3">
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
          {result.issues?.filter((i) => i.severity === "error").length ?? 0} error,{" "}
          {result.issues?.filter((i) => i.severity === "warning").length ?? 0} peringatan ditemukan.
        </AlertDescription>
      </Alert>
    )}

    {result.issues && result.issues.length > 0 && (
      <div className="rounded-lg border bg-card">
        <div className="px-4 py-3 border-b bg-muted/50">
          <h4 className="text-sm font-medium">
            Detail Masalah ({result.issues.length})
          </h4>
        </div>
        <div className="divide-y">
          {result.issues.map((issue, idx) => (
            <div key={idx} className="px-4 py-3 flex items-start gap-3">
              <div
                className={[
                  "shrink-0 size-5 rounded-full flex items-center justify-center text-xs font-medium mt-0.5",
                  issue.severity === "error"
                    ? "bg-red-100 text-red-700"
                    : issue.severity === "warning"
                    ? "bg-yellow-100 text-yellow-700"
                    : "bg-blue-100 text-blue-700",
                ].join(" ")}
              >
                {issue.severity === "error" ? "!" : "i"}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    {issue.category}
                  </span>
                  {issue.field && (
                    <span className="text-xs text-muted-foreground">· {issue.field}</span>
                  )}
                </div>
                <p className="text-sm">{issue.message}</p>
                {(issue.expected || issue.actual) && (
                  <div className="mt-1 flex gap-3 text-xs text-muted-foreground">
                    {issue.expected && <span>Diharapkan: <span className="font-medium text-foreground">{issue.expected}</span></span>}
                    {issue.actual && <span>Ditemukan: <span className="font-medium text-foreground">{issue.actual}</span></span>}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    )}
  </div>
)}
```

- [ ] **Step 5.3: Verifikasi TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Expected: Tidak ada type error baru.

- [ ] **Step 5.4: Commit**

```bash
git add frontend/components/reviewer/DocumentValidator.tsx
git commit -m "feat: update DocumentValidator to accept DOCX and display rich validation issues"
```

---

## Task 6: Buat Halaman Reviewer Validation

**Files:**
- Create: `frontend/app/(dashboard)/reviewer/validation/page.tsx`

- [ ] **Step 6.1: Buat file halaman**

Buat `frontend/app/(dashboard)/reviewer/validation/page.tsx`:

```tsx
import { DocumentValidator } from "@/components/reviewer/DocumentValidator"

export default function ReviewerValidationPage() {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Validasi Dokumen</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Validasi format dokumen DOCX proposal PKM terhadap aturan yang berlaku pada periode aktif
        </p>
      </div>

      <div className="max-w-2xl">
        <DocumentValidator />
      </div>
    </div>
  )
}
```

- [ ] **Step 6.2: Test navigasi**

Jalankan Next.js dev server dan akses `http://localhost:3000/reviewer/validation` sebagai user dengan role reviewer.

Expected:
- Halaman "Validasi Dokumen" muncul
- Dropdown skema PKM ter-load (atau tampil kosong jika tabel belum ada data)
- Area upload file DOCX tersedia dengan hint "Format: DOCX, maks 10MB"
- Nav item "Validasi Dokumen" di sidebar sudah aktif (highlight)

- [ ] **Step 6.3: Commit**

```bash
git add "frontend/app/(dashboard)/reviewer/validation/page.tsx"
git commit -m "feat: add reviewer validation page at /reviewer/validation"
```

---

## Task 7: End-to-End Integration Test

- [ ] **Step 7.1: Jalankan semua service**

Jalankan di 3 terminal terpisah:
```bash
# Terminal 1 - FastAPI
cd ai-backend && uvicorn main:app --reload --port 8000

# Terminal 2 - Express
cd backend && node src/server.js

# Terminal 3 - Next.js
cd frontend && npm run dev
```

- [ ] **Step 7.2: Test alur lengkap**

1. Buka `http://localhost:3000/reviewer/validation`
2. Pilih skema PKM dari dropdown
3. Upload file DOCX (sediakan file test `.docx`)
4. Klik "Validasi Dokumen"
5. Tunggu hasil

Expected sukses:
- Alert hijau "Dokumen Valid" atau alert merah "Ditemukan Masalah Format"
- Jika ada masalah: list issues dengan category, field, message, expected, actual

Expected error cases:
- File PDF diupload → error "Hanya file DOCX yang diterima."
- Tidak ada period aktif → error dari server "Tidak ada periode review yang aktif saat ini."
- Schema tidak punya data referensi → error "Data referensi untuk [skema] tahun [tahun] belum tersedia."

- [ ] **Step 7.3: Commit final**

```bash
git add .
git commit -m "feat: complete validator integration - reviewer can validate DOCX proposals"
```

---

## Catatan Implementasi

### Jika tabel `pkm_schemas` belum ada di Supabase

Buat tabel dengan SQL berikut di Supabase SQL editor:
```sql
CREATE TABLE pkm_schemas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nama TEXT NOT NULL,
  singkatan TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed data
INSERT INTO pkm_schemas (nama, singkatan) VALUES
  ('PKM Kewirausahaan', 'PKM-K'),
  ('PKM Pengabdian Masyarakat', 'PKM-M'),
  ('PKM Penelitian', 'PKM-P'),
  ('PKM Penerapan IPTEK', 'PKM-PI'),
  ('PKM Karsa Cipta', 'PKM-KC');
```

### Jika skema kolom `skema` di tabel `projects` berbeda format

Pastikan nilai `singkatan` di `pkm_schemas` persis sama dengan nilai `skema` di tabel `projects`. Cek dengan:
```sql
SELECT DISTINCT skema FROM projects;
```

### Import `model_ai.validation` di FastAPI

Jika ada `ImportError` saat FastAPI start, pastikan semua dependencies Python sudah terinstall di environment yang digunakan FastAPI:
```bash
cd ai
pip install python-docx pydantic
```
