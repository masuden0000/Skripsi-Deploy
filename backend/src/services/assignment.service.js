import { adminClient } from "../config/supabase.js"
import { AppError } from "../utils/app-error.js"

function mapAssignmentRow(row, reviewerEmail) {
  const reviewStatus = row.review_status ?? null
  return {
    id: row.id,
    periodId: row.period_id,
    reviewerId: row.reviewer_id,
    proposalLink: row.proposal_link ?? "",
    assessmentLink: row.assessment_link ?? "",
    isCompleted: reviewStatus === "selesai",
    reviewStatus,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    reviewer: row.reviewer?.profiles?.full_name ?? "",
    reviewerEmail: reviewerEmail ?? "",
    period: row.period?.nama ?? "",
    periodMulai: row.period?.tanggal_mulai ?? "",
    periodSelesai: row.period?.tanggal_selesai ?? "",
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
      review_status,
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

  const { data: incomplete, error: incompleteError } = await adminClient
    .from("assignments")
    .select("id")
    .eq("reviewer_id", values.reviewer_id)
    .or("review_status.is.null,review_status.eq.menunggu_validasi")
    .limit(1)

  if (incompleteError) {
    throw new AppError("Gagal memeriksa status tugas reviewer.", 500)
  }

  if (incomplete && incomplete.length > 0) {
    throw new AppError("Reviewer masih memiliki tugas yang belum selesai.", 409)
  }

  const { data, error } = await adminClient
    .from("assignments")
    .insert(values)
    .select(`
      id,
      period_id,
      reviewer_id,
      proposal_link,
      assessment_link,
      review_status,
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
      review_status,
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

// ============================================================================
// Reviewer-specific queries
// ============================================================================
export async function getAssignmentsByReviewerId(reviewerId) {
  const { data, error } = await adminClient
    .from("assignments")
    .select(`
      id,
      period_id,
      reviewer_id,
      proposal_link,
      assessment_link,
      review_status,
      is_completed,
      created_at,
      updated_at,
      period:pkm_review_periods!inner(id, nama, tanggal_mulai, tanggal_selesai),
      reviewer:reviewer_profiles!inner(
        id,
        profiles!inner(full_name),
        faculties!inner(id, name, code)
      )
    `)
    .eq("reviewer_id", reviewerId)
    .order("created_at", { ascending: false })

  if (error) {
    throw new AppError("Gagal mengambil penugasan reviewer.", 500)
  }

  const rows = data ?? []
  const emailById = await buildEmailMap([reviewerId])

  return rows.map((row) => mapAssignmentRow(row, emailById.get(row.reviewer_id)))
}

export async function completeAssignment(id, reviewerId) {
  const { data: existing, error: fetchError } = await adminClient
    .from("assignments")
    .select("id, reviewer_id, review_status")
    .eq("id", id)
    .eq("reviewer_id", reviewerId)
    .single()

  if (fetchError || !existing) {
    throw new AppError("Tugas tidak ditemukan.", 404)
  }

  if (existing.review_status === "menunggu_validasi" || existing.review_status === "selesai") {
    throw new AppError("Tugas sudah ditandai selesai atau sedang menunggu validasi.", 409)
  }

  const { data, error } = await adminClient
    .from("assignments")
    .update({ review_status: "menunggu_validasi" })
    .eq("id", id)
    .eq("reviewer_id", reviewerId)
    .select(`
      id,
      period_id,
      reviewer_id,
      proposal_link,
      assessment_link,
      review_status,
      is_completed,
      created_at,
      updated_at,
      period:pkm_review_periods!inner(id, nama, tanggal_mulai, tanggal_selesai),
      reviewer:reviewer_profiles!inner(
        id,
        profiles!inner(full_name),
        faculties!inner(id, name, code)
      )
    `)
    .single()

  if (error) {
    throw new AppError("Gagal menandai tugas selesai.", 500)
  }

  const emailById = await buildEmailMap([data.reviewer_id])
  return mapAssignmentRow(data, emailById.get(data.reviewer_id))
}

export async function validateAssignment(id, approved) {
  const { data: existing, error: fetchError } = await adminClient
    .from("assignments")
    .select("id, review_status")
    .eq("id", id)
    .single()

  if (fetchError || !existing) {
    throw new AppError("Tugas tidak ditemukan.", 404)
  }

  if (existing.review_status !== "menunggu_validasi") {
    throw new AppError("Tugas tidak dalam status menunggu validasi.", 409)
  }

  const updateData = approved
    ? { review_status: "selesai", is_completed: true }
    : { review_status: null, is_completed: false }

  const { data, error } = await adminClient
    .from("assignments")
    .update(updateData)
    .eq("id", id)
    .select(`
      id,
      period_id,
      reviewer_id,
      proposal_link,
      assessment_link,
      review_status,
      is_completed,
      created_at,
      updated_at,
      period:pkm_review_periods!inner(id, nama, tanggal_mulai, tanggal_selesai),
      reviewer:reviewer_profiles!inner(
        id,
        profiles!inner(full_name),
        faculties!inner(id, name, code)
      )
    `)
    .single()

  if (error) {
    throw new AppError("Gagal memvalidasi tugas.", 500)
  }

  const emailById = await buildEmailMap([data.reviewer_id])
  return mapAssignmentRow(data, emailById.get(data.reviewer_id))
}

export async function getActiveAssignmentsByReviewerId(reviewerId) {
  // PostgREST doesn't support filtering on nested relations, so we:
  // 1. Get all assignments for this reviewer
  // 2. Filter in JS to only include active periods
  const { data, error } = await adminClient
    .from("assignments")
    .select(`
      id,
      period_id,
      reviewer_id,
      proposal_link,
      assessment_link,
      review_status,
      is_completed,
      created_at,
      updated_at,
      period:pkm_review_periods!inner(id, nama, tanggal_mulai, tanggal_selesai),
      reviewer:reviewer_profiles!inner(
        id,
        profiles!inner(full_name),
        faculties!inner(id, name, code)
      )
    `)
    .eq("reviewer_id", reviewerId)
    .order("created_at", { ascending: false })

  if (error) {
    throw new AppError("Gagal mengambil penugasan aktif.", 500)
  }

  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())

  // Include assignment if period masih aktif ATAU tugas belum selesai (periode kedaluwarsa tapi belum ditandai selesai)
  const activeRows = (data ?? []).filter((row) => {
    const mulai = new Date(row.period.tanggal_mulai)
    const selesai = new Date(row.period.tanggal_selesai)
    const inActivePeriod = today >= mulai && today <= selesai
    const isIncomplete = row.review_status !== "selesai"
    return inActivePeriod || isIncomplete
  })

  const emailById = await buildEmailMap([reviewerId])

  return activeRows.map((row) => mapAssignmentRow(row, emailById.get(row.reviewer_id)))
}