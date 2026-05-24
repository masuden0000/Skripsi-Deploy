/**
 * Fungsi: Mengelola logika bisnis CRUD proyek dan komunikasi dengan AI backend.
 * Digunakan oleh: controllers/projects.controller.js
 * Tujuan: Menangani operasi proyek serta proxy request ke FastAPI ai-backend.
 */

import { adminClient } from "../config/supabase.js"
import { AppError } from "../utils/app-error.js"
import { formatDateForPostgres, toTitleCase } from "../utils/string-formatters.js"
import { PROPOSAL_STATUS_LABELS } from "../constants/status.js"

export const AI_BACKEND_URL = process.env.AI_BACKEND_URL || "http://127.0.0.1:8000"

function mapProjectRow(row) {
  return {
    id: row.id,
    judul: row.judul,
    tahun: row.tahun,
    skema: row.skema,
    status: row.status,
    userId: row.user_id,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    reviewPeriod: row.pkm_review_periods
      ? {
          id: row.pkm_review_periods.id,
          name: row.pkm_review_periods.name,
          startDate: formatDateForPostgres(row.pkm_review_periods.start_date),
          endDate: formatDateForPostgres(row.pkm_review_periods.end_date),
        }
      : null,
    proposal: row.proposals
      ? {
          id: row.proposals.id,
          fileName: row.proposals.file_name,
          fileUrl: row.proposals.file_url,
          uploadedAt: row.proposals.uploaded_at,
          status: row.proposals.status,
        }
      : null,
  }
}

export async function getProjectsByUserId(userId) {
  const { data, error } = await adminClient
    .from("projects")
    .select("*, pkm_review_periods(id, name, start_date, end_date), proposals(id, file_name, file_url, uploaded_at, status)")
    .eq("user_id", userId)
    .order("created_at", { ascending: false })

  if (error) {
    throw new AppError("Gagal mengambil daftar proyek.", 500)
  }

  return (data ?? []).map(mapProjectRow)
}

export async function getProjectById(projectId) {
  const { data, error } = await adminClient
    .from("projects")
    .select("*, pkm_review_periods(id, name, start_date, end_date), proposals(id, file_name, file_url, uploaded_at, status)")
    .eq("id", projectId)
    .single()

  if (error) {
    if (error.code === "PGRST116") {
      throw new AppError("Proyek tidak ditemukan.", 404)
    }
    throw new AppError("Gagal mengambil detail proyek.", 500)
  }

  return mapProjectRow(data)
}

export async function getAllProjects({ page = 1, limit = 20, search = "", status = "", periodId = "" } = {}) {
  let query = adminClient
    .from("projects")
    .select("*, pkm_review_periods(id, name, start_date, end_date), proposals(id, file_name, file_url, uploaded_at, status)", {
      count: "exact",
    })
    .order("created_at", { ascending: false })
    .range((page - 1) * limit, page * limit - 1)

  if (search) {
    query = query.ilike("judul", `%${search}%`)
  }
  if (status) {
    query = query.eq("status", status)
  }
  if (periodId) {
    query = query.eq("period_id", periodId)
  }

  const { data, error, count } = await query

  if (error) {
    throw new AppError("Gagal mengambil daftar proyek.", 500)
  }

  return {
    data: (data ?? []).map(mapProjectRow),
    total: count ?? 0,
    page,
    limit,
  }
}

export async function createProject(userId, payload) {
  const { judul, tahun, skema, periodId } = payload

  const { data, error } = await adminClient
    .from("projects")
    .insert({
      user_id: userId,
      judul: toTitleCase(judul),
      tahun,
      skema,
      status: "draft",
      period_id: periodId ?? null,
    })
    .select("*, pkm_review_periods(id, name, start_date, end_date), proposals(id, file_name, file_url, uploaded_at, status)")
    .single()

  if (error) {
    throw new AppError("Gagal membuat proyek baru.", 500)
  }

  return mapProjectRow(data)
}

export async function updateProject(projectId, userId, payload) {
  const { judul, tahun, skema, status, periodId } = payload

  const existing = await getProjectById(projectId)

  if (existing.userId !== userId) {
    throw new AppError("Anda tidak memiliki akses ke proyek ini.", 403)
  }

  const updates = {}
  if (judul !== undefined) updates.judul = toTitleCase(judul)
  if (tahun !== undefined) updates.tahun = tahun
  if (skema !== undefined) updates.skema = skema
  if (status !== undefined) updates.status = status
  if (periodId !== undefined) updates.period_id = periodId

  const { data, error } = await adminClient
    .from("projects")
    .update(updates)
    .eq("id", projectId)
    .select("*, pkm_review_periods(id, name, start_date, end_date), proposals(id, file_name, file_url, uploaded_at, status)")
    .single()

  if (error) {
    throw new AppError("Gagal memperbarui proyek.", 500)
  }

  return mapProjectRow(data)
}

export async function deleteProject(projectId, userId) {
  const existing = await getProjectById(projectId)

  if (existing.userId !== userId) {
    throw new AppError("Anda tidak memiliki akses ke proyek ini.", 403)
  }

  const { error } = await adminClient.from("projects").delete().eq("id", projectId)

  if (error) {
    throw new AppError("Gagal menghapus proyek.", 500)
  }
}

async function callAiBackend(path, body, options = {}) {
  const url = `${AI_BACKEND_URL}${path}`
  const response = await fetch(url, {
    method: options.method || "POST",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    body: body ? JSON.stringify(body) : undefined,
    ...options,
  })

  const contentType = response.headers.get("content-type") || ""
  const isJson = contentType.includes("application/json")

  if (!response.ok) {
    let message = `AI backend error: ${response.status}`
    if (isJson) {
      const errorData = await response.json()
      message = errorData.detail || errorData.error || message
    } else {
      const text = await response.text()
      message = text || message
    }
    throw new AppError(message, response.status)
  }

  if (isJson) {
    return response.json()
  }

  return response.arrayBuffer()
}

export async function getUploadUrl(projectId, userId) {
  const project = await getProjectById(projectId)

  if (project.userId !== userId) {
    throw new AppError("Anda tidak memiliki akses ke proyek ini.", 403)
  }

  const { data, error } = await adminClient.storage
    .from("proposals")
    .createSignedUploadUrl(`${projectId}/${Date.now()}.pdf`)

  if (error) {
    throw new AppError("Gagal membuat URL upload.", 500)
  }

  return data
}

export async function createProjectAndUpload(userId, body) {
  const { fields, fileBuffer } = body

  const project = await createProject(userId, {
    judul: fields.judul,
    tahun: fields.tahun,
    skema: fields.skema,
    periodId: fields.period_id,
  })

  const fileName = `${project.id}/${Date.now()}-proposal.pdf`

  const { data: uploadData, error: uploadError } = await adminClient.storage
    .from("proposals")
    .upload(fileName, fileBuffer, {
      contentType: "application/pdf",
      upsert: false,
    })

  if (uploadError) {
    await adminClient.from("projects").delete().eq("id", project.id)
    throw new AppError("Gagal mengunggah file proposal.", 500)
  }

  const { data: urlData } = adminClient.storage.from("proposals").getPublicUrl(uploadData.path)

  const { error: proposalError } = await adminClient
    .from("proposals")
    .insert({
      project_id: project.id,
      file_name: fileBuffer.originalname || "proposal.pdf",
      file_url: urlData.publicUrl,
      status: "pending",
    })

  if (proposalError) {
    await adminClient.storage.from("proposals").remove([fileName])
    await adminClient.from("projects").delete().eq("id", project.id)
    throw new AppError("Gagal menyimpan data proposal.", 500)
  }

  return await getProjectById(project.id)
}

export async function validateDocument(projectId, userId) {
  const project = await getProjectById(projectId)

  if (project.userId !== userId) {
    throw new AppError("Anda tidak memiliki akses ke proyek ini.", 403)
  }

  if (!project.proposal) {
    throw new AppError("Proposal belum diunggah.", 400)
  }

  try {
    const result = await callAiBackend(`/api/validation/run?schema_id=${project.skema}`, {
      document_url: project.proposal.fileUrl,
      judul: project.judul,
    })
    return result
  } catch (err) {
    if (err instanceof AppError) throw err
    throw new AppError("Gagal terhubung ke AI backend.", 500)
  }
}

export async function getDocumentTypes() {
  try {
    return await callAiBackend("/api/schemas/document-types", {})
  } catch (err) {
    console.error("Failed to fetch document types:", err)
    return []
  }
}

export async function getSchemas() {
  try {
    return await callAiBackend("/api/schemas", {})
  } catch (err) {
    console.error("Failed to fetch schemas:", err)
    return []
  }
}