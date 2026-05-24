"""
Fungsi: Mendefinisikan TypeScript schema dan tipe data untuk Project
Digunakan oleh: Express Backend, FastAPI AI Backend, Frontend
Tujuan: Menyediakan type definitions yang konsisten antar service
"""

export enum ProjectStatus {
  PENDING = "pending",
  UPLOADING = "uploading",
  EXTRACTING = "extracting",
  EXTRACTED = "extracted",
  GENERATING = "generating",
  COMPLETED = "completed",
  FAILED = "failed",
}

export interface ProjectCreateRequest {
  skema: string
  tahun: string
}

export interface Project {
  id: string
  skema: string
  tahun: string
  source_file: string | null
  source_url: string | null
  status: ProjectStatus
  error_message: string | null
  result_url: string | null
  created_at: string
  updated_at: string
}

export interface ProjectCreateResponse {
  id: string
  skema: string
  tahun: string
  source_file: string | null
  source_url: string | null
  status: ProjectStatus
  error_message: string | null
  result_url: string | null
  created_at: string
  updated_at: string
}

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface ProjectListResponse {
  success: boolean
  data: Project[]
  error?: string
}

export interface ProjectDetailResponse {
  success: boolean
  data: Project | null
  error?: string
}

export type { Project as ProjectType }