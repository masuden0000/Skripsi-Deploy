/**
 * Fungsi: Mengelola data penugasan reviewer terhadap proyek.
 * Digunakan oleh: routes/reviewer-assignments.routes.js, controllers terkait
 * Tujuan: Mengambil dan memproses data assignment reviewer dari database Supabase.
 */

import cookieParser from "cookie-parser"
import { adminClient } from "../config/supabase.js"
import { AppError } from "../utils/app-error.js"
import { formatDateForPostgres, toTitleCase } from "../utils/string-formatters.js"
import { PROPOSAL_STATUS_LABELS, ASSIGNMENT_STATUS_LABELS } from "../constants/status.js"

export const AI_BACKEND_URL = process.env.AI_BACKEND_URL || "http://127.0.0.1:8000"

function mapAssignmentRow(row) {
  return {
    id: row.id,
    projectId: row.project_id,
    reviewerId: row.reviewer_id,
    status: row.status,
    assignedAt: row.assigned_at,
    startedAt: row.started_at,
    deadline: row.deadline,
    completedAt: row.completed_at,
    project: {
      id: row.projects?.id,
      judul: row.projects?.judul,
      tahun: row.projects?.tahun,
      skema: row.projects?.skema,
      status: row.projects?.status,
      createdAt: row.projects?.created_at,
      reviewPeriod: row.projects?.pkm_review_periods
        ? {
            id: row.projects.pkm_review_periods.id,
            name: row.projects.pkm_review_periods.name,
            startDate: formatDateForPostgres(row.projects.pkm_review_periods.start_date),
            endDate: formatDateForPostgres(row.projects.pkm_review_periods.end_date),
          }
        : null,
    },
    reviewer: row.reviewer_profiles
      ? {
          id: row.reviewer_profiles.id,
          fullName: row.reviewer_profiles.profiles?.full_name ?? "",
          facultyCode: row.reviewer_profiles.faculties?.code ?? "",
          facultyName: row.reviewer_profiles.faculties?.name ?? "",
        }
      : null,
    proposal: row.projects?.proposals
      ? {
          id: row.projects.proposals.id,
          fileName: row.projects.proposals.file_name,
          fileUrl: row.projects.proposals.file_url,
          uploadedAt: row.projects.proposals.uploaded_at,
          status: row.projects.proposals.status,
        }
      : null,
  }
}

export async function getAssignmentsByReviewerId(reviewerId) {
  const { data, error } = await adminClient
    .from("assignments")
    .select(
      `
      id,
      project_id,
      reviewer_id,
      status,
      assigned_at,
      started_at,
      deadline,
      completed_at,
      projects!inner(
        id,
        judul,
        tahun,
        skema,
        status,
        created_at,
        proposals(id, file_name, file_url, uploaded_at, status),
        pkm_review_periods!inner(id, name, start_date, end_date)
      ),
      reviewer_profiles!inner(
        id,
        profiles!inner(full_name),
        faculties!inner(code, name)
      )
    `
    )
    .eq("reviewer_id", reviewerId)
    .order("assigned_at", { ascending: false })

  if (error) {
    throw new AppError("Gagal mengambil daftar penugasan.", 500)
  }

  return (data ?? []).map(mapAssignmentRow)
}

export async function getActiveAssignmentsByReviewerId(reviewerId) {
  const { data, error } = await adminClient
    .from("assignments")
    .select(
      `
      id,
      project_id,
      reviewer_id,
      status,
      assigned_at,
      started_at,
      deadline,
      completed_at,
      projects!inner(
        id,
        judul,
        tahun,
        skema,
        status,
        created_at,
        proposals(id, file_name, file_url, uploaded_at, status),
        pkm_review_periods!inner(id, name, start_date, end_date)
      ),
      reviewer_profiles!inner(
        id,
        profiles!inner(full_name),
        faculties!inner(code, name)
      )
    `
    )
    .eq("reviewer_id", reviewerId)
    .in("status", ["assigned", "in_progress"])
    .order("deadline", { ascending: true })

  if (error) {
    throw new AppError("Gagal mengambil penugasan aktif.", 500)
  }

  return (data ?? []).map(mapAssignmentRow)
}

export async function getAssignmentById(assignmentId) {
  const { data, error } = await adminClient
    .from("assignments")
    .select(
      `
      id,
      project_id,
      reviewer_id,
      status,
      assigned_at,
      started_at,
      deadline,
      completed_at,
      projects!inner(
        id,
        judul,
        tahun,
        skema,
        status,
        created_at,
        proposals(id, file_name, file_url, uploaded_at, status),
        pkm_review_periods!inner(id, name, start_date, end_date)
      ),
      reviewer_profiles!inner(
        id,
        profiles!inner(full_name),
        faculties!inner(code, name)
      )
    `
    )
    .eq("id", assignmentId)
    .single()

  if (error) {
    throw new AppError("Penugasan tidak ditemukan.", 404)
  }

  return mapAssignmentRow(data)
}

export async function startAssignment(assignmentId, reviewerId) {
  const assignment = await getAssignmentById(assignmentId)

  if (assignment.reviewerId !== reviewerId) {
    throw new AppError("Anda tidak ditugaskan pada penugasan ini.", 403)
  }

  if (assignment.status !== "assigned") {
    throw new AppError(`Tidak dapat memulai penugasan dengan status '${ASSIGNMENT_STATUS_LABELS[assignment.status] ?? assignment.status}'.`, 400)
  }

  const { data, error } = await adminClient
    .from("assignments")
    .update({ status: "in_progress", started_at: new Date().toISOString() })
    .eq("id", assignmentId)
    .select()
    .single()

  if (error) {
    throw new AppError("Gagal memulai penugasan.", 500)
  }

  return mapAssignmentRow(data)
}

export async function completeAssignment(assignmentId, reviewerId, validationResult) {
  const assignment = await getAssignmentById(assignmentId)

  if (assignment.reviewerId !== reviewerId) {
    throw new AppError("Anda tidak ditugaskan pada penugasan ini.", 403)
  }

  if (assignment.status !== "in_progress") {
    throw new AppError(`Tidak dapat menyelesaikan penugasan dengan status '${ASSIGNMENT_STATUS_LABELS[assignment.status] ?? assignment.status}'.`, 400)
  }

  const { data, error } = await adminClient
    .from("assignments")
    .update({
      status: "completed",
      completed_at: new Date().toISOString(),
    })
    .eq("id", assignmentId)
    .select()
    .single()

  if (error) {
    throw new AppError("Gagal menyelesaikan penugasan.", 500)
  }

  return mapAssignmentRow(data)
}

export async function getAssignmentsByProjectId(projectId) {
  const { data, error } = await adminClient
    .from("assignments")
    .select(
      `
      id,
      project_id,
      reviewer_id,
      status,
      assigned_at,
      started_at,
      deadline,
      completed_at,
      projects!inner(
        id,
        judul,
        tahun,
        skema,
        status,
        created_at,
        proposals(id, file_name, file_url, uploaded_at, status),
        pkm_review_periods!inner(id, name, start_date, end_date)
      ),
      reviewer_profiles!inner(
        id,
        profiles!inner(full_name),
        faculties!inner(code, name)
      )
    `
    )
    .eq("project_id", projectId)
    .order("assigned_at", { ascending: false })

  if (error) {
    throw new AppError("Gagal mengambil penugasan untuk proyek ini.", 500)
  }

  return (data ?? []).map(mapAssignmentRow)
}

export async function createAssignment(projectId, reviewerId, deadline) {
  const { data, error } = await adminClient
    .from("assignments")
    .insert({
      project_id: projectId,
      reviewer_id: reviewerId,
      deadline,
    })
    .select(
      `
      id,
      project_id,
      reviewer_id,
      status,
      assigned_at,
      started_at,
      deadline,
      completed_at,
      projects!inner(
        id,
        judul,
        tahun,
        skema,
        status,
        created_at,
        proposals(id, file_name, file_url, uploaded_at, status),
        pkm_review_periods!inner(id, name, start_date, end_date)
      ),
      reviewer_profiles!inner(
        id,
        profiles!inner(full_name),
        faculties!inner(code, name)
      )
    `
    )
    .single()

  if (error) {
    throw new AppError("Gagal membuat penugasan baru.", 500)
  }

  return mapAssignmentRow(data)
}