import { apiRequest } from "./client"
import {
  reviewPeriodResponseSchema,
  reviewPeriodFormSchema,
  type ReviewPeriod,
  type ReviewPeriodFormData,
} from "@/lib/schemas"

const endpoint = "/api/review-periods"

export async function getReviewPeriods(): Promise<{
  data: ReviewPeriod[] | null
  error: string | null
}> {
  const result = await apiRequest<{ data: ReviewPeriod[] }>(
    "GET",
    endpoint,
    undefined,
    undefined // Parse mentah untuk respons list
  )

  // Handle respons array secara manual
  if (result.error) return { data: null, error: result.error }

  const raw = result.data as { data?: unknown } | null
  if (!raw || !Array.isArray(raw?.data)) {
    return { data: [], error: null }
  }

  return { data: raw.data as ReviewPeriod[], error: null }
}

export async function createReviewPeriod(
  data: ReviewPeriodFormData
): Promise<{ data: ReviewPeriod | null; error: string | null }> {
  const validated = reviewPeriodFormSchema.safeParse(data)
  if (!validated.success) {
    return {
      data: null,
      error: validated.error.issues.map((e: { message: string }) => e.message).join(", "),
    }
  }

  const result = await apiRequest("POST", endpoint, validated.data, reviewPeriodResponseSchema)
  if (result.error) return { data: null, error: result.error }
  return { data: result.data?.data ?? null, error: null }
}

export async function updateReviewPeriod(
  id: string,
  data: ReviewPeriodFormData
): Promise<{ data: ReviewPeriod | null; error: string | null }> {
  const validated = reviewPeriodFormSchema.safeParse(data)
  if (!validated.success) {
    return {
      data: null,
      error: validated.error.issues.map((e: { message: string }) => e.message).join(", "),
    }
  }

  const result = await apiRequest("PUT", `${endpoint}/${id}`, validated.data, reviewPeriodResponseSchema)
  if (result.error) return { data: null, error: result.error }
  return { data: result.data?.data ?? null, error: null }
}

export async function deleteReviewPeriod(
  id: string
): Promise<{ data: null; error: string | null }> {
  return apiRequest("DELETE", `${endpoint}/${id}`)
}