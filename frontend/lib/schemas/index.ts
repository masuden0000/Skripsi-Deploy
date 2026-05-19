import { z } from "zod"

// ============================================================================
// Periode Review
// ============================================================================
export const reviewPeriodSchema = z.object({
  id: z.string(),
  nama: z.string(),
  tanggalMulai: z.string(),
  tanggalSelesai: z.string(),
  createdAt: z.string(),
  updatedAt: z.string(),
})

export const reviewPeriodFormSchema = z.object({
  nama: z.string().min(1, "Nama periode wajib diisi"),
  tanggalMulai: z.string().min(1, "Tanggal mulai wajib diisi"),
  tanggalSelesai: z.string().min(1, "Tanggal selesai wajib diisi"),
}).refine(
  (data) => data.tanggalSelesai >= data.tanggalMulai,
  { message: "Tanggal selesai tidak boleh sebelum tanggal mulai", path: ["tanggalSelesai"] }
)

export const reviewPeriodResponseSchema = z.object({
  data: reviewPeriodSchema,
})

export type ReviewPeriod = z.infer<typeof reviewPeriodSchema>
export type ReviewPeriodFormData = z.infer<typeof reviewPeriodFormSchema>

// ============================================================================
// Auth
// ============================================================================
export const authLoginSchema = z.object({
  email: z.string().email("Format email tidak valid"),
  password: z.string().min(1, "Password wajib diisi"),
  role: z.enum(["admin", "reviewer"], {
    message: "Role harus admin atau reviewer",
  }),
})

export const authLoginResponseSchema = z.object({
  user: z.object({
    id: z.string(),
    email: z.string(),
    role: z.string(),
  }),
  destination: z.string().optional(),
})

export type AuthLoginInput = z.infer<typeof authLoginSchema>
export type AuthLoginResponse = z.infer<typeof authLoginResponseSchema>

// ============================================================================
// Fakultas
// ============================================================================
export const facultySchema = z.object({
  id: z.string(),
  nama: z.string(),
  createdAt: z.string(),
  updatedAt: z.string(),
})

export const facultyFormSchema = z.object({
  nama: z.string().min(1, "Nama fakultas wajib diisi"),
})

export type Faculty = z.infer<typeof facultySchema>
export type FacultyFormData = z.infer<typeof facultyFormSchema>

// ============================================================================
// Reviewer
// ============================================================================
export const reviewerSchema = z.object({
  id: z.string(),
  nama: z.string(),
  email: z.string(),
  noTelp: z.string().nullable(),
  fakultasId: z.string(),
  createdAt: z.string(),
  updatedAt: z.string(),
})

export const reviewerFormSchema = z.object({
  nama: z.string().min(1, "Nama reviewer wajib diisi"),
  email: z.string().email("Format email tidak valid"),
  noTelp: z.string().optional(),
  fakultasId: z.string().min(1, "Fakultas wajib dipilih"),
})

export type Reviewer = z.infer<typeof reviewerSchema>
export type ReviewerFormData = z.infer<typeof reviewerFormSchema>