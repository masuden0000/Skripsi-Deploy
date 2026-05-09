import { adminClient } from "../config/supabase.js"
import { AppError } from "../utils/app-error.js"
import { ensureFacultyExists } from "./faculty.service.js"

function mapReviewerRow(row, emailById) {
  return {
    id: row.id,
    nama: row.profiles?.full_name ?? "",
    email: emailById.get(row.id) ?? "",
    fakultasId: row.faculties?.id ?? "",
    fakultas: row.faculties?.name ?? "",
    isActive: Boolean(row.is_active),
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

async function getReviewerRowById(id) {
  const { data, error } = await adminClient
    .from("reviewer_profiles")
    .select("id, is_active, profiles!inner(full_name), faculties!inner(id, code, name)")
    .eq("id", id)
    .single()

  if (error) {
    if (error.code === "PGRST116") {
      throw new AppError("Reviewer tidak ditemukan.", 404)
    }

    throw new AppError("Gagal mengambil data reviewer.", 500)
  }

  return data
}

function normalizeCreatePayload(payload) {
  const nama = typeof payload.nama === "string" ? payload.nama.trim() : ""
  const email = typeof payload.email === "string" ? payload.email.trim().toLowerCase() : ""
  const password = typeof payload.password === "string" ? payload.password : ""
  const fakultasId = typeof payload.fakultasId === "string" ? payload.fakultasId : ""
  const isActive = Boolean(payload.isActive)

  if (!nama || !email || !password || !fakultasId) {
    throw new AppError("Nama, email, password, dan fakultas wajib diisi.", 400)
  }

  if (password.length < 8) {
    throw new AppError("Password reviewer minimal 8 karakter.", 400)
  }

  return {
    nama,
    email,
    password,
    fakultasId,
    isActive,
  }
}

function normalizeUpdatePayload(payload) {
  const nama = typeof payload.nama === "string" ? payload.nama.trim() : ""
  const email = typeof payload.email === "string" ? payload.email.trim().toLowerCase() : ""
  const fakultasId = typeof payload.fakultasId === "string" ? payload.fakultasId : ""
  const isActive = Boolean(payload.isActive)

  if (!nama || !email || !fakultasId) {
    throw new AppError("Nama, email, dan fakultas wajib diisi.", 400)
  }

  return {
    nama,
    email,
    fakultasId,
    isActive,
  }
}

export async function listReviewers() {
  const { data, error } = await adminClient
    .from("reviewer_profiles")
    .select("id, is_active, created_at, profiles!inner(full_name), faculties!inner(id, code, name)")
    .order("created_at", { ascending: false })

  if (error) {
    throw new AppError("Gagal mengambil daftar reviewer.", 500)
  }

  const rows = data ?? []
  const emailById = await buildEmailMap(rows.map((row) => row.id))

  return rows.map((row) => mapReviewerRow(row, emailById))
}

export async function getReviewerAccessByUserId(userId) {
  const { data, error } = await adminClient
    .from("reviewer_profiles")
    .select("id, is_active")
    .eq("id", userId)
    .single()

  if (error) {
    if (error.code === "PGRST116") {
      throw new AppError("Akun reviewer ini belum memiliki profil reviewer.", 403)
    }

    throw new AppError("Gagal mengambil status reviewer.", 500)
  }

  if (!data.is_active) {
    throw new AppError("Akun reviewer tidak aktif. Hubungi administrator.", 403)
  }

  return data
}

export async function createReviewer(payload) {
  const values = normalizeCreatePayload(payload)
  await ensureFacultyExists(values.fakultasId)

  const { data: authData, error: authError } = await adminClient.auth.admin.createUser({
    email: values.email,
    password: values.password,
    email_confirm: true,
    user_metadata: {
      role: "reviewer",
    },
  })

  if (authError || !authData.user) {
    throw new AppError(authError?.message ?? "Gagal membuat akun auth reviewer.", 500)
  }

  try {
    const { error: profileError } = await adminClient
      .from("profiles")
      .insert({
        id: authData.user.id,
        role: "reviewer",
        full_name: values.nama,
      })

    if (profileError) {
      throw profileError
    }

    const { error: reviewerError } = await adminClient
      .from("reviewer_profiles")
      .insert({
        id: authData.user.id,
        faculty_id: values.fakultasId,
        is_active: values.isActive,
      })

    if (reviewerError) {
      throw reviewerError
    }
  } catch (error) {
    await adminClient.auth.admin.deleteUser(authData.user.id).catch(() => null)
    throw new AppError("Gagal menyimpan reviewer baru ke database.", 500)
  }

  const row = await getReviewerRowById(authData.user.id)
  const emailById = new Map([[authData.user.id, authData.user.email ?? values.email]])
  return mapReviewerRow(row, emailById)
}

export async function updateReviewer(id, payload) {
  const current = await getReviewerRowById(id)
  const { data: currentAuth, error: currentAuthError } = await adminClient.auth.admin.getUserById(id)

  if (currentAuthError || !currentAuth.user) {
    throw new AppError("Akun auth reviewer tidak ditemukan.", 404)
  }

  const values = normalizeUpdatePayload(payload)
  await ensureFacultyExists(values.fakultasId)

  const previousEmail = currentAuth.user.email ?? ""
  const emailChanged = previousEmail !== values.email

  if (emailChanged) {
    const { error: emailError } = await adminClient.auth.admin.updateUserById(id, {
      email: values.email,
      email_confirm: true,
    })

    if (emailError) {
      throw new AppError(emailError.message || "Gagal memperbarui email reviewer.", 500)
    }
  }

  try {
    const { error: profileError } = await adminClient
      .from("profiles")
      .update({
        full_name: values.nama,
      })
      .eq("id", id)

    if (profileError) {
      throw profileError
    }

    const { error: reviewerError } = await adminClient
      .from("reviewer_profiles")
      .update({
        faculty_id: values.fakultasId,
        is_active: values.isActive,
      })
      .eq("id", id)

    if (reviewerError) {
      throw reviewerError
    }
  } catch (_error) {
    if (emailChanged) {
      await adminClient.auth.admin
        .updateUserById(id, {
          email: previousEmail,
          email_confirm: true,
        })
        .catch(() => null)
    }

    throw new AppError("Gagal memperbarui data reviewer.", 500)
  }

  const row = await getReviewerRowById(current.id)
  const emailById = new Map([[id, values.email]])
  return mapReviewerRow(row, emailById)
}

export async function deleteReviewer(id) {
  await getReviewerRowById(id)

  const { error } = await adminClient.auth.admin.deleteUser(id)

  if (error) {
    throw new AppError(error.message || "Gagal menghapus reviewer.", 500)
  }
}
