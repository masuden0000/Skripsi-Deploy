import { adminClient } from "../config/supabase.js"
import { AppError } from "../utils/app-error.js"

function mapAssignmentRow(row, reviewerEmail) {
  return {
    id: row.id,
    periodId: row.period_id,
    reviewerId: row.reviewer_id,
    proposalLink: row.proposal_link ?? "",
    assessmentLink: row.assessment_link ?? "",
    isCompleted: Boolean(row.is_completed),
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    reviewer: row.reviewer?.profiles?.full_name ?? "",
    reviewerEmail: reviewerEmail ?? "",
    period: row.period?.nama ?? "",
    fakultasId: row.reviewer?.faculties?.id ?? "",
    fakultas: row.reviewer?.faculties?.name ?? "",
    fakultasKode: row.reviewer?.faculties?.code ?? "",
  }
}

function normalizePayload(payload) {
  const periodId = typeof payload.periodId === "string" ? payload.periodId : ""
  const reviewerId = typeof payload.reviewerId === "string" ? payload.reviewerId : ""
  const proposalLink = typeof payload.proposalLink === "string" ? payload.proposalLink.trim() : ""
  const assessmentLink = typeof payload.assessmentLink === "string" ? payload.assessmentLink.trim() : ""

  if (!periodId) {
    throw new AppError("Periode review wajib dipilih.", 400)
  }

  if (!reviewerId) {
    throw new AppError("Reviewer wajib dipilih.", 400)
  }

  if (!proposalLink && !assessmentLink) {
    throw new AppError("Minimal satu link (proposal atau pengumpulan) wajib diisi.", 400)
  }

  return {
    period_id: periodId,
    reviewer_id: reviewerId,
    proposal_link: proposalLink || null,
    assessment_link: assessmentLink || null,
  }
}

async function buildEmailMap(userIds) {
  if (userIds.length === 0) {
    return new Map()
  }

  const { data, error } = await adminClient.auth.admin.listUsers({
    page: 1,
    perPage: 1000,
  })

  if (error) {
    throw new AppError("Gagal mengambil email reviewer dari auth.", 500)
  }

  const userIdSet = new Set(userIds)
  const emailById = new Map()

  for (const user of data.users ?? []) {
    if (userIdSet.has(user.id)) {
      emailById.set(user.id, user.email ?? "")
    }
  }

  return emailById
}

export async function listAssignments() {
  const { data, error } = await adminClient
    .from("assignments")
    .select(`
      id,
      period_id,
      reviewer_id,
      proposal_link,
      assessment_link,
      is_completed,
      created_at,
      updated_at,
      period:pkm_review_periods!inner(id, nama),
      reviewer:reviewer_profiles!inner(
        id,
        profiles!inner(full_name),
        faculties!inner(id, name, code)
      )
    `)
    .order("created_at", { ascending: false })

  if (error) {
    throw new AppError("Gagal mengambil daftar tugas.", 500)
  }

  const rows = data ?? []
  const reviewerIds = rows.map((r) => r.reviewer_id)
  const emailById = await buildEmailMap(reviewerIds)

  return rows.map((row) => mapAssignmentRow(row, emailById.get(row.reviewer_id)))
}

export async function createAssignment(payload) {
  const values = normalizePayload(payload)

  const { data, error } = await adminClient
    .from("assignments")
    .insert(values)
    .select(`
      id,
      period_id,
      reviewer_id,
      proposal_link,
      assessment_link,
      is_completed,
      created_at,
      updated_at,
      period:pkm_review_periods!inner(id, nama),
      reviewer:reviewer_profiles!inner(
        id,
        profiles!inner(full_name),
        faculties!inner(id, name, code)
      )
    `)
    .single()

  if (error) {
    if (error.code === "23505") {
      throw new AppError("Reviewer ini sudah ditugaskan ke periode yang dipilih.", 409)
    }
    throw new AppError(error.message || "Gagal membuat tugas baru.", 500)
  }

  const emailById = await buildEmailMap([data.reviewer_id])
  return mapAssignmentRow(data, emailById.get(data.reviewer_id))
}

export async function updateAssignment(id, payload) {
  const proposalLink =
    typeof payload.proposalLink === "string" ? payload.proposalLink.trim() : ""
  const assessmentLink =
    typeof payload.assessmentLink === "string" ? payload.assessmentLink.trim() : ""

  if (!proposalLink && !assessmentLink) {
    throw new AppError("Minimal satu link wajib diisi.", 400)
  }

  const { data, error } = await adminClient
    .from("assignments")
    .update({
      proposal_link: proposalLink || null,
      assessment_link: assessmentLink || null,
    })
    .eq("id", id)
    .select(`
      id,
      period_id,
      reviewer_id,
      proposal_link,
      assessment_link,
      is_completed,
      created_at,
      updated_at,
      period:pkm_review_periods!inner(id, nama),
      reviewer:reviewer_profiles!inner(
        id,
        profiles!inner(full_name),
        faculties!inner(id, name, code)
      )
    `)
    .single()

  if (error) {
    if (error.code === "PGRST116") {
      throw new AppError("Tugas tidak ditemukan.", 404)
    }
    throw new AppError(error.message || "Gagal memperbarui tugas.", 500)
  }

  const emailById = await buildEmailMap([data.reviewer_id])
  return mapAssignmentRow(data, emailById.get(data.reviewer_id))
}

export async function deleteAssignment(id) {
  const { error } = await adminClient.from("assignments").delete().eq("id", id)

  if (error) {
    throw new AppError(error.message || "Gagal menghapus tugas.", 500)
  }
}