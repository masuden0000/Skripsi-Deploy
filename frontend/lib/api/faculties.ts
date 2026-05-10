import { apiRequest } from "./client"
import {
  facultySchema,
  facultyFormSchema,
  type Faculty,
  type FacultyFormData,
} from "@/lib/schemas"

const endpoint = "/api/faculties"

export async function getFaculties(): Promise<{
  data: Faculty[] | null
  error: string | null
}> {
  const result = await apiRequest<{ data: Faculty[] }>(
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

  return { data: raw.data as Faculty[], error: null }
}

export async function createFaculty(
  data: FacultyFormData
): Promise<{ data: Faculty | null; error: string | null }> {
  const validated = facultyFormSchema.safeParse(data)
  if (!validated.success) {
    return {
      data: null,
      error: validated.error.issues.map((e: { message: string }) => e.message).join(", "),
    }
  }

  return apiRequest("POST", endpoint, validated.data, facultySchema)
}

export async function updateFaculty(
  id: string,
  data: FacultyFormData
): Promise<{ data: Faculty | null; error: string | null }> {
  const validated = facultyFormSchema.safeParse(data)
  if (!validated.success) {
    return {
      data: null,
      error: validated.error.issues.map((e: { message: string }) => e.message).join(", "),
    }
  }

  return apiRequest("PUT", `${endpoint}/${id}`, validated.data, facultySchema)
}

export async function deleteFaculty(
  id: string
): Promise<{ data: null; error: string | null }> {
  return apiRequest("DELETE", `${endpoint}/${id}`)
}