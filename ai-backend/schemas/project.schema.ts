/**
 * Shared Project Schema - Source of Truth
 * Dipakai oleh: Express Backend, FastAPI AI Backend, Frontend
 */

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
  judul: string
}

export interface Project {
  id: string
  skema: string
  tahun: string
  judul: string
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
  judul: string
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