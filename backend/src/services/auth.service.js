import { createAuthClient, adminClient } from "../config/supabase.js"
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
    throw new AppError("Password Anda salah.", 401)
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

export async function updateUserProfile(userId, userEmail, { type, newEmail, currentPassword, newPassword }) {
  if (type === "email") {
    if (!newEmail) throw new AppError("Email baru wajib diisi.", 400)

    const { error } = await adminClient.auth.admin.updateUserById(userId, { email: newEmail })
    if (error) throw new AppError("Gagal memperbarui email: " + error.message, 500)

  } else if (type === "password") {
    if (!currentPassword || !newPassword) {
      throw new AppError("Password lama dan baru wajib diisi.", 400)
    }
    if (newPassword.length < 6) {
      throw new AppError("Password baru minimal 6 karakter.", 400)
    }

    // Ambil email terkini dari Supabase — JWT session bisa menyimpan email lama
    // jika email sudah diubah sebelumnya dalam sesi yang sama
    const { data: freshUser, error: getUserError } = await adminClient.auth.admin.getUserById(userId)
    if (getUserError || !freshUser?.user) throw new AppError("Gagal memverifikasi akun.", 500)

    const authClient = createAuthClient()
    const { error: signInError } = await authClient.auth.signInWithPassword({
      email: freshUser.user.email,
      password: currentPassword,
    })
    if (signInError) throw new AppError("Password lama tidak sesuai.", 400)

    const { error: updateError } = await adminClient.auth.admin.updateUserById(userId, {
      password: newPassword,
    })
    if (updateError) throw new AppError("Gagal memperbarui password: " + updateError.message, 500)

  } else {
    throw new AppError("Tipe perubahan tidak valid.", 400)
  }
}
