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

export const validationResultSchema = z.object({
  valid: z.boolean(),
  errors: z.array(z.object({
    rule: z.string(),
    message: z.string(),
    severity: z.enum(["error", "warning", "info"]),
    field: z.string().optional(),
  })).optional(),
  metadata: z.record(z.any()).optional(),
})

// ============================================================================
// Types
// ============================================================================
export type PkmSchema = z.infer<typeof pkmSchemaSchema>
export type ActivePeriod = z.infer<typeof activePeriodSchema>
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

export async function runDocumentValidation(
  payload: ValidationPayload
): Promise<{
  data: ValidationResult | null
  error: string | null
}> {
  const formData = new FormData()
  formData.append("schema_id", payload.schemaId)
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