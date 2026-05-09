import { adminClient } from "../config/supabase.js"
import { AppError } from "../utils/app-error.js"

export async function getProfileByUserId(userId) {
  const { data, error } = await adminClient
    .from("profiles")
    .select("id, role")
    .eq("id", userId)
    .single()

  if (error) {
    throw new AppError("Gagal mengambil profil pengguna dari database.", 500)
  }

  if (!data?.role) {
    throw new AppError("Akun ini belum memiliki role yang ditetapkan.", 403)
  }

  return data
}
