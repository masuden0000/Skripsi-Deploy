/**
 * Modul API client untuk fitur PKM (validasi dokumen dan skema).
 *
 * Alur pemanggilan dalam pipeline validasi:
 *   getPkmSchemas()       → GET  /api/pkm/schemas        (Express → Supabase)
 *   runDocumentValidation() → POST /api/pkm/validation/run (Express → FastAPI → Python validator)
 *
 * Digunakan oleh: frontend/components/reviewer/DocumentValidator.tsx
 */
import { apiRequest } from "./client"
import { z } from "zod"

// ============================================================================
// Schema Definitions
// ============================================================================
export const pkmSchemaSchema = z.object({
  id: z.string(),
  nama: z.string(),
  singkatan: z.string(),
  createdAt: z.string(),
  updatedAt: z.string(),
})

export const activePeriodSchema = z.object({
  id: z.string(),
  nama: z.string(),
  tanggalMulai: z.string(),
  tanggalSelesai: z.string(),
  status: z.string(),
  createdAt: z.string(),
  updatedAt: z.string(),
})

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

export const validationSummarySchema = z.object({
  total_checks: z.number().optional(),
  passed: z.number().optional(),
  failed: z.number().optional(),
  warnings: z.number().optional(),
  errors: z.number().optional(),
})

// Schema untuk satu hasil pengecekan (passed/failed/skipped) dari backend.
// `expected` dan `actual` bisa berupa string/number/boolean dari Python,
// dikonversi ke string via transform agar konsisten di frontend.
const _coerceStr = z.union([z.string(), z.number(), z.boolean()])
  .transform((v) => String(v))
  .nullable()
  .optional()

export const validationCheckSchema = z.object({
  category: z.string(),
  field: z.string(),
  status: z.enum(["passed", "failed", "warning", "skipped"]),
  message: z.string().optional().default(""),
  expected: _coerceStr,
  actual: _coerceStr,
  location: z.string().nullable().optional(),
  skip_reason: z.string().nullable().optional(),
  occurrences: z.array(z.object({
    page      : z.number().nullable().optional(),
    bab       : z.string().nullable().optional(),
    para_idx  : z.number().nullable().optional(),
    style     : z.string().nullable().optional(),
    text      : z.string().optional().default(""),
    actual    : z.string().nullable().optional(),
    expected  : z.string().nullable().optional(),
  })).nullable().optional(),
})

export const validationResultSchema = z.object({
  valid: z.boolean(),
  status: z.enum(["pass", "fail", "warning"]),
  issues: z.array(validationIssueSchema).optional().default([]),
  summary: validationSummarySchema.optional(),
  validated_at: z.string().optional(),
  // report: hasil lengkap semua pengecekan dikelompokkan per kategori.
  // Dipakai untuk menampilkan daftar pengecekan yang lulus di panel "Lulus".
  report: z.record(z.string(), z.array(validationCheckSchema)).optional(),
})

// ============================================================================
// Types
// ============================================================================
export type PkmSchema = z.infer<typeof pkmSchemaSchema>
export type ActivePeriod = z.infer<typeof activePeriodSchema>
export type ValidationIssue = z.infer<typeof validationIssueSchema>
export type ValidationOccurrence = z.infer<typeof validationOccurrenceSchema>
export type ValidationCheck = z.infer<typeof validationCheckSchema>
export type ValidationResult = z.infer<typeof validationResultSchema>

// ============================================================================
// Active Period
// ============================================================================
export async function getActivePeriod(): Promise<{
  data: ActivePeriod | null
  error: string | null
}> {
  return apiRequest("GET", "/pkm/active-period", undefined, activePeriodSchema)
}

// ============================================================================
// PKM Schemas
// ============================================================================
export async function getPkmSchemas(): Promise<{
  data: PkmSchema[] | null
  error: string | null
}> {
  const result = await apiRequest<{ data: PkmSchema[] }>(
    "GET",
    "/pkm/schemas",
    undefined,
    undefined
  )

  if (result.error) return { data: null, error: result.error }

  const raw = result.data as { data?: unknown } | null
  if (!raw || !Array.isArray(raw?.data)) {
    return { data: [], error: null }
  }

  return { data: raw.data as PkmSchema[], error: null }
}

// ============================================================================
// Document Validation
// ============================================================================
export interface ValidationPayload {
  schemaId: string
  year: string
  file: File
}

// ── Tipe untuk validasi bulk (banyak dokumen sekaligus) ──────────────────────

export interface BulkValidationItem {
  schemaId: string
  year: string
  file: File
}

export interface ValidationResultItem {
  id: string
  position: number
  file_name: string
  schema_id: string
  tahun: string
  status: "pending" | "processing" | "completed" | "failed"
  result: ValidationResult | null
  error_message: string | null
}

export interface ValidationSession {
  id: string
  type: "single" | "bulk"
  status: "pending" | "processing" | "completed" | "failed"
  total_items: number
  completed_items: number
  created_at: string
  updated_at: string
  items: ValidationResultItem[]
}

export async function runDocumentValidation(
  payload: ValidationPayload
): Promise<{
  data: ValidationResult | null
  error: string | null
}> {
  const formData = new FormData()
  formData.append("schema_id", payload.schemaId)
  formData.append("tahun", payload.year)
  formData.append("file", payload.file)

  // Use apiFetch directly for FormData (bypass JSON content-type)
  const url = "/api/pkm/validation/run"

  try {
    const response = await fetch(url, {
      method: "POST",
      body: formData,
      credentials: "include",
    })

    const json = await response.json()

    if (!response.ok) {
      return {
        data: null,
        error: json.error || `Request gagal (${response.status})`,
      }
    }

    // Parse with schema
    const result = validationResultSchema.safeParse(json)
    if (!result.success) {
      return {
        data: null,
        error: result.error.issues.map((e) => e.message).join(", "),
      }
    }

    return { data: result.data, error: null }
  } catch (err) {
    const message =
      err instanceof TypeError && err.message.includes("fetch")
        ? "Tidak dapat menjangkau server."
        : "Terjadi kesalahan tidak terduga."

    return { data: null, error: message }
  }
}

// ── runBulkValidation ────────────────────────────────────────────────────────
export async function runBulkValidation(
  items: BulkValidationItem[]
): Promise<{ data: { session_id: string } | null; error: string | null }> {
  const formData = new FormData()
  formData.append("count", String(items.length))

  for (let i = 0; i < items.length; i++) {
    formData.append(`schema_id_${i}`, items[i].schemaId)
    formData.append(`tahun_${i}`,     items[i].year)
    formData.append(`file_${i}`,      items[i].file, items[i].file.name)
  }

  try {
    const response = await fetch("/api/pkm/validation/bulk", {
      method:      "POST",
      body:        formData,
      credentials: "include",
    })

    const json = await response.json()

    if (!response.ok) {
      return { data: null, error: json.error || `Request gagal (${response.status})` }
    }

    if (!json.session_id) {
      return { data: null, error: "Response tidak mengandung session_id." }
    }

    return { data: { session_id: json.session_id }, error: null }
  } catch (err) {
    const message =
      err instanceof TypeError && err.message.includes("fetch")
        ? "Tidak dapat menjangkau server."
        : "Terjadi kesalahan tidak terduga."
    return { data: null, error: message }
  }
}

// ── checkSessionStatus ───────────────────────────────────────────────────────
export async function checkSessionStatus(
  sessionId: string
): Promise<{ data: ValidationSession | null; error: string | null }> {
  try {
    const response = await fetch(`/api/pkm/validation/sessions/${encodeURIComponent(sessionId)}`, {
      credentials: "include",
    })

    const json = await response.json()

    if (!response.ok) {
      return { data: null, error: json.error || `Request gagal (${response.status})` }
    }

    // Pastikan result di setiap item di-parse dengan validationResultSchema
    const items: ValidationResultItem[] = (json.items ?? []).map((item: ValidationResultItem) => {
      if (item.result) {
        const parsed = validationResultSchema.safeParse(item.result)
        return { ...item, result: parsed.success ? parsed.data : item.result }
      }
      return item
    })

    return {
      data: {
        id:              json.id,
        type:            json.type ?? "bulk",
        status:          json.status,
        total_items:     json.total_items,
        completed_items: json.completed_items,
        created_at:      json.created_at,
        updated_at:      json.updated_at,
        items,
      },
      error: null,
    }
  } catch (err) {
    const message =
      err instanceof TypeError && err.message.includes("fetch")
        ? "Tidak dapat menjangkau server."
        : "Terjadi kesalahan tidak terduga."
    return { data: null, error: message }
  }
}