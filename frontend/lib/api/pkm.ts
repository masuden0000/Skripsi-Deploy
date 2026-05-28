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

// ============================================================================
// Types
// ============================================================================
export type PkmSchema = z.infer<typeof pkmSchemaSchema>
export type ActivePeriod = z.infer<typeof activePeriodSchema>
export type ValidationIssue = z.infer<typeof validationIssueSchema>
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
  file: File
}

// Kirim DOCX + schema_id ke Express proxy → FastAPI validation.py → ValidationResult
// Menggunakan FormData (bukan JSON) karena payload berisi file binary
export async function runDocumentValidation(
  payload: ValidationPayload
): Promise<{
  data: ValidationResult | null
  error: string | null
}> {
  const formData = new FormData()
  formData.append("schema_id", payload.schemaId)  // singkatan skema (misal: PKM-K, PKM-T)
  formData.append("file", payload.file)            // file DOCX yang divalidasi

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