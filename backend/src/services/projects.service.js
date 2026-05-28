/**
 * Projects Service
 * Berkomunikasi dengan AI Backend (FastAPI)
 *
 * Keyword: automated document generation
 */
import { env } from "../config/env.js"

export const AI_BACKEND_URL = env.AI_BACKEND_URL || "http://127.0.0.1:8000"

async function callAiBackend(endpoint, options = {}) {
  try {
    const response = await fetch(`${AI_BACKEND_URL}${endpoint}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    })

    const contentType = response.headers.get("content-type") || ""
    if (!contentType.includes("application/json")) {
      // AI backend returned HTML error page (e.g., 500 Internal Server Error)
      const text = await response.text()
      console.error(`[ProjectsService] AI backend returned non-JSON (${response.status}):`, text.slice(0, 200))
      return {
        success: false,
        error: `AI backend error (${response.status})`,
      }
    }

    const data = await response.json()
    return data
  } catch (error) {
    console.error(`[ProjectsService] Error calling AI backend:`, error)
    return {
      success: false,
      error: error instanceof Error ? error.message : "Failed to connect to AI backend",
    }
  }
}

export async function createProject(request, file) {
  const formData = new FormData()
  formData.append("skema", request.skema)
  formData.append("tahun", request.tahun)
  formData.append("judul", request.judul)

  if (file) {
    formData.append("file", file)
  }

  try {
    const response = await fetch(`${AI_BACKEND_URL}/api/projects/`, {
      method: "POST",
      body: formData,
      // Do NOT set Content-Type header - browser will set multipart/form-data with boundary
    })

    const data = await response.json()
    return data
  } catch (error) {
    console.error(`[ProjectsService] Error creating project:`, error)
    return {
      success: false,
      error: error instanceof Error ? error.message : "Failed to create project",
    }
  }
}

export async function getProject(projectId) {
  return callAiBackend(`/api/projects/${projectId}`)
}

export async function listProjects() {
  return callAiBackend("/api/projects")
}

export async function deleteProject(projectId) {
  return callAiBackend(`/api/projects/${projectId}`, {
    method: "DELETE",
  })
}