import { ZodSchema, ZodError } from "zod"

// ============================================================================
// Tipe error
// ============================================================================
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly data?: unknown
  ) {
    super(message)
    this.name = "ApiError"
  }
}

export class ValidationError extends ApiError {
  constructor(
    message: string,
    public readonly issues: ZodError["issues"]
  ) {
    super(message, 422, issues)
    this.name = "ValidationError"
  }
}

// ============================================================================
// Parser respons
// ============================================================================
export interface ApiResponse<T> {
  data: T | null
  error: string | null
}

export async function parseApiResponse<T>(
  response: Response,
  schema: ZodSchema<T> | null = null
): Promise<ApiResponse<T>> {
  const text = await response.text()

  if (!text) {
    return { data: null, error: null }
  }

  try {
    const json = JSON.parse(text)

    // Jika schema diberikan, validasi dan kembalikan
    if (schema) {
      const result = schema.safeParse(json)
      if (!result.success) {
        return {
          data: json as T,
          error: result.error.issues.map((e: { message: string }) => e.message).join(", "),
        }
      }
      return { data: result.data, error: null }
    }

    // Jika tidak, kembalikan JSON mentah (untuk backward compatibility)
    return { data: json as T, error: null }
  } catch {
    return { data: null, error: "Respons server tidak valid." }
  }
}

// ============================================================================
// Core fetch wrapper - menggunakan relative URL untuk Next.js API routes
// ============================================================================
export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {},
  schema: ZodSchema<T> | null = null
): Promise<ApiResponse<T>> {
  // Gunakan relative URL untuk Next.js API routes (bukan backend langsung)
  const url = endpoint.startsWith("/api") ? endpoint : `/api${endpoint}`

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      credentials: "include",
      cache: "no-store",
    })

    const { data, error } = await parseApiResponse(response, schema)

    if (!response.ok) {
      const errorMessage =
        typeof data === "object" && data !== null && "error" in data
          ? String((data as Record<string, unknown>).error)
          : `Request gagal (${response.status})`

      return { data: null, error: errorMessage }
    }

    return { data, error }
  } catch (err) {
    const message =
      err instanceof TypeError && err.message.includes("fetch")
        ? "Tidak dapat menjangkau server."
        : "Terjadi kesalahan tidak terduga."

    return { data: null, error: message }
  }
}

// ============================================================================
// Fungsi request API yang sudah typed
// ============================================================================
export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE"

export async function apiRequest<T>(
  method: HttpMethod,
  endpoint: string,
  body?: unknown,
  schema?: ZodSchema<T>
): Promise<ApiResponse<T>> {
  return apiFetch<T>(
    endpoint,
    {
      method,
      body: body ? JSON.stringify(body) : undefined,
    },
    schema ?? null
  )
}