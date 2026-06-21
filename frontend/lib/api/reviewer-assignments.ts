import { apiRequest } from "./client"
import { z } from "zod"

// ============================================================================
// Schema Definitions
// ============================================================================
export const assignmentSchema = z.object({
  id: z.string(),
  periodId: z.string(),
  reviewerId: z.string(),
  proposalLink: z.string().nullable(),
  assessmentLink: z.string().nullable(),
  isCompleted: z.boolean(),
  createdAt: z.string(),
  updatedAt: z.string(),
  reviewer: z.string(),
  reviewerEmail: z.string(),
  period: z.string(),
  periodMulai: z.string().nullable().optional(),
  periodSelesai: z.string().nullable().optional(),
  fakultasId: z.string(),
  fakultas: z.string(),
  fakultasKode: z.string(),
})

// Extended schema with period details from backend
export const assignmentWithPeriodSchema = assignmentSchema.extend({
  periodData: z.object({
    id: z.string(),
    nama: z.string(),
    tanggalMulai: z.string(),
    tanggalSelesai: z.string(),
  }).optional(),
}).transform((data) => ({
  ...data,
  period: data.periodData?.nama ?? data.period,
  periodId: data.periodData?.id ?? data.periodId,
}))

// ============================================================================
// Types
// ============================================================================
export type Assignment = z.infer<typeof assignmentSchema>

// ============================================================================
// Get Reviewer Assignments (all assignments for current reviewer)
// ============================================================================
export async function getReviewerAssignments(): Promise<{
  data: Assignment[] | null
  error: string | null
}> {
  const result = await apiRequest<{ data: Assignment[] }>(
    "GET",
    "/reviewer-assignments",
    undefined,
    undefined
  )

  if (result.error) return { data: null, error: result.error }

  const raw = result.data as { data?: unknown } | null
  if (!raw || !Array.isArray(raw?.data)) {
    return { data: [], error: null }
  }

  // Transform backend response to include period info
  const assignments = (raw.data as Assignment[]).map((a) => ({
    ...a,
    period: a.period,
    periodId: a.periodId,
  }))

  return { data: assignments, error: null }
}

// ============================================================================
// Complete Assignment (reviewer marks task as done)
// ============================================================================
export async function completeReviewerAssignment(id: string): Promise<{
  data: Assignment | null
  error: string | null
}> {
  const result = await apiRequest<{ data: Assignment }>(
    "PATCH",
    `/reviewer-assignments/${id}/complete`,
  )

  if (result.error) return { data: null, error: result.error }

  const raw = result.data as { data?: unknown } | null
  if (!raw?.data) return { data: null, error: "Gagal mendapatkan data tugas." }

  return { data: raw.data as Assignment, error: null }
}

// ============================================================================
// Get Active Assignments (assignments for active periods)
// ============================================================================
export async function getActiveAssignments(): Promise<{
  data: Assignment[] | null
  error: string | null
}> {
  const result = await apiRequest<{ data: Assignment[] }>(
    "GET",
    "/reviewer-assignments/active",
    undefined,
    undefined
  )

  if (result.error) return { data: null, error: result.error }

  const raw = result.data as { data?: unknown } | null
  if (!raw || !Array.isArray(raw?.data)) {
    return { data: [], error: null }
  }

  return { data: raw.data as Assignment[], error: null }
}