import { apiRequest } from "./client"
import {
  reviewerSchema,
  reviewerFormSchema,
  type Reviewer,
  type ReviewerFormData,
} from "@/lib/schemas"

const endpoint = "/api/reviewers"

export async function getReviewers(): Promise<{
  data: Reviewer[] | null
  error: string | null
}> {
  const result = await apiRequest<{ data: Reviewer[] }>(
    "GET",
    endpoint,
    undefined,
    undefined
  )

  if (result.error) return { data: null, error: result.error }

  const raw = result.data as { data?: unknown } | null
  if (!raw || !Array.isArray(raw?.data)) {
    return { data: [], error: null }
  }

  return { data: raw.data as Reviewer[], error: null }
}

export async function createReviewer(
  data: ReviewerFormData
): Promise<{ data: Reviewer | null; error: string | null }> {
  const validated = reviewerFormSchema.safeParse(data)
  if (!validated.success) {
    return {
      data: null,
      error: validated.error.issues.map((e: { message: string }) => e.message).join(", "),
    }
  }

  return apiRequest("POST", endpoint, validated.data, reviewerSchema)
}

export async function updateReviewer(
  id: string,
  data: ReviewerFormData
): Promise<{ data: Reviewer | null; error: string | null }> {
  const validated = reviewerFormSchema.safeParse(data)
  if (!validated.success) {
    return {
      data: null,
      error: validated.error.issues.map((e: { message: string }) => e.message).join(", "),
    }
  }

  return apiRequest("PUT", `${endpoint}/${id}`, validated.data, reviewerSchema)
}

export async function deleteReviewer(
  id: string
): Promise<{ data: null; error: string | null }> {
  return apiRequest("DELETE", `${endpoint}/${id}`)
}