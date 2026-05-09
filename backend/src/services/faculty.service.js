import { adminClient } from "../config/supabase.js"
import { AppError } from "../utils/app-error.js"

function mapFaculty(row) {
  return {
    id: row.id,
    code: row.code,
    name: row.name,
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

  return (data ?? []).map(mapFaculty)
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
