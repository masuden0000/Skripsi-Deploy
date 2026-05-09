import { createAuthClient } from "../config/supabase.js"
import { ROLE_ROUTES, VALID_ROLES } from "../constants/roles.js"
import { AppError } from "../utils/app-error.js"
import { getProfileByUserId } from "./profile.service.js"
import { getReviewerAccessByUserId } from "./reviewer.service.js"
import { createSessionToken } from "./session.service.js"

export async function loginWithPassword({ email, password, role }) {
  if (!email || !password || !role) {
    throw new AppError("Semua field wajib diisi.", 400)
  }

  if (!VALID_ROLES.includes(role)) {
    throw new AppError("Role yang dipilih tidak valid.", 400)
  }

  const authClient = createAuthClient()
  const { data, error } = await authClient.auth.signInWithPassword({
    email,
    password,
  })

  if (error || !data.user) {
    throw new AppError("Email atau password salah. Periksa kembali.", 401)
  }

  const profile = await getProfileByUserId(data.user.id)

  if (profile.role !== role) {
    throw new AppError(
      `Akun ini terdaftar sebagai ${profile.role}, bukan ${role}. Pilih role yang sesuai.`,
      403
    )
  }

  if (profile.role === "reviewer") {
    await getReviewerAccessByUserId(data.user.id)
  }

  const destination = ROLE_ROUTES[profile.role]
  if (!destination) {
    throw new AppError("Role tidak dikenal. Hubungi administrator.", 500)
  }

  const sessionToken = createSessionToken({
    userId: data.user.id,
    email: data.user.email ?? "",
    role: profile.role,
  })

  return {
    sessionToken,
    destination,
    user: {
      id: data.user.id,
      email: data.user.email ?? "",
      role: profile.role,
    },
  }
}
