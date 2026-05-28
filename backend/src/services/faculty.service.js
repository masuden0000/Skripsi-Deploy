import { adminClient } from "../config/supabase.js"
import { AppError } from "../utils/app-error.js"

function mapFaculty(row, reviewerCount = 0) {
  return {
    id: row.id,
    code: row.code,
    name: row.name,
    reviewerCount,
  }
}

export async function listFaculties() {
  const { data, error } = await adminClient
    .from("faculties")
    .select("id, code, name")
    .order("name", { ascending: true })

  if (error) {
    throw new AppError("Gagal mengambil daftar fakultas.", 500)
  }

  const { data: reviewerRows, error: reviewerError } = await adminClient
    .from("reviewer_profiles")
    .select("faculty_id")

  if (reviewerError) {
    throw new AppError("Gagal mengambil jumlah reviewer per fakultas.", 500)
  }

  // Hitung manual supaya daftar fakultas tetap sederhana dan tidak bergantung
  // pada bentuk nested relation dari PostgREST.
  const reviewerCountByFaculty = new Map()
  for (const row of reviewerRows ?? []) {
    const currentCount = reviewerCountByFaculty.get(row.faculty_id) ?? 0
    reviewerCountByFaculty.set(row.faculty_id, currentCount + 1)
  }

  return (data ?? []).map((row) => mapFaculty(row, reviewerCountByFaculty.get(row.id) ?? 0))
}

export async function ensureFacultyExists(facultyId) {
  if (!facultyId) {
    throw new AppError("Fakultas wajib dipilih.", 400)
  }

  const { data, error } = await adminClient
    .from("faculties")
    .select("id, code, name")
    .eq("id", facultyId)
    .single()

  if (error) {
    if (error.code === "PGRST116") {
      throw new AppError("Fakultas tidak ditemukan.", 404)
    }

    throw new AppError("Gagal mengambil data fakultas.", 500)
  }

  return mapFaculty(data)
}

function normalizeFacultyPayload(payload) {
  const name = typeof payload.name === "string" ? payload.name.trim() : ""
  const code = typeof payload.code === "string" ? payload.code.trim().toUpperCase() : ""

  if (!name || !code) {
    throw new AppError("Nama fakultas dan kode fakultas wajib diisi.", 400)
  }

  return { name, code }
}

async function getFacultyById(id) {
  const { data, error } = await adminClient
    .from("faculties")
    .select("id, code, name")
    .eq("id", id)
    .single()

  if (error) {
    if (error.code === "PGRST116") {
      throw new AppError("Fakultas tidak ditemukan.", 404)
    }

    throw new AppError("Gagal mengambil data fakultas.", 500)
  }

  return data
}

export async function createFaculty(payload) {
  const values = normalizeFacultyPayload(payload)
  const { data, error } = await adminClient
    .from("faculties")
    .insert(values)
    .select("id, code, name")
    .single()

  if (error) {
    if (error.code === "23505") {
      throw new AppError("Nama atau kode fakultas sudah terdaftar.", 409)
    }

    throw new AppError("Gagal menambah fakultas.", 500)
  }

  return mapFaculty(data, 0)
}

export async function getFacultyByIdService(id) {
  const { data, error } = await adminClient
    .from("faculties")
    .select("id, code, name")
    .eq("id", id)
    .single()

  if (error) {
    if (error.code === "PGRST116") {
      throw new AppError("Fakultas tidak ditemukan.", 404)
    }

    throw new AppError("Gagal mengambil data fakultas.", 500)
  }

  const { count } = await adminClient
    .from("reviewer_profiles")
    .select("*", { count: "exact", head: true })
    .eq("faculty_id", id)

  return mapFaculty(data, count ?? 0)
}

export async function updateFaculty(id, payload) {
  const current = await getFacultyById(id)
  const values = normalizeFacultyPayload(payload)

  const { data, error } = await adminClient
    .from("faculties")
    .update(values)
    .eq("id", id)
    .select("id, code, name")
    .single()

  if (error) {
    if (error.code === "23505") {
      throw new AppError("Nama atau kode fakultas sudah terdaftar.", 409)
    }

    throw new AppError("Gagal memperbarui fakultas.", 500)
  }

  const { count } = await adminClient
    .from("reviewer_profiles")
    .select("*", { count: "exact", head: true })
    .eq("faculty_id", id)

  return mapFaculty(data, count ?? 0)
}

export async function listReviewersByFaculty(facultyId) {
  await getFacultyById(facultyId)

  const { data, error } = await adminClient
    .from("reviewer_profiles")
    .select("id, is_active, created_at, profiles!inner(full_name), faculties!inner(id, code, name)")
    .eq("faculty_id", facultyId)
    .order("created_at", { ascending: false })

  if (error) {
    throw new AppError("Gagal mengambil daftar reviewer.", 500)
  }

  const rows = data ?? []
  const userIds = rows.map((row) => row.id)

  const { data: authData, error: authError } = await adminClient.auth.admin.listUsers({
    page: 1,
    perPage: 1000,
  })

  if (authError) {
    throw new AppError("Gagal mengambil email reviewer dari auth.", 500)
  }

  const userIdSet = new Set(userIds)
  const emailById = new Map()

  for (const user of authData.users ?? []) {
    if (userIdSet.has(user.id)) {
      emailById.set(user.id, user.email ?? "")
    }
  }

  return rows.map((row) => ({
    id: row.id,
    nama: row.profiles?.full_name ?? "",
    email: emailById.get(row.id) ?? "",
    isActive: Boolean(row.is_active),
  }))
}

export async function deleteFaculty(id) {
  await getFacultyById(id)

  const { count, error: reviewerError } = await adminClient
    .from("reviewer_profiles")
    .select("*", { count: "exact", head: true })
    .eq("faculty_id", id)

  if (reviewerError) {
    throw new AppError("Gagal memeriksa reviewer pada fakultas ini.", 500)
  }

  if ((count ?? 0) > 0) {
    throw new AppError("Fakultas tidak bisa dihapus karena masih dipakai reviewer.", 409)
  }

  const { error } = await adminClient
    .from("faculties")
    .delete()
    .eq("id", id)

  if (error) {
    throw new AppError("Gagal menghapus fakultas.", 500)
  }
}
