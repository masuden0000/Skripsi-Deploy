/**
 * Fungsi: Menangani request HTTP terkait autentikasi (login, logout, session).
 * Digunakan oleh: routes/auth.routes.js
 * Tujuan: Mengelola cookie session dan redirect berdasarkan role pengguna.
 */

import { ROLE_ROUTES } from "../constants/roles.js"
import { env } from "../config/env.js"
import { loginWithPassword } from "../services/auth.service.js"
import { clearSessionCookie, getSessionCookieOptions } from "../utils/cookies.js"

export async function login(req, res) {
  const result = await loginWithPassword(req.body ?? {})

  res.cookie(env.SESSION_COOKIE_NAME, result.sessionToken, getSessionCookieOptions())

  res.status(200).json({
    message: "Login berhasil.",
    destination: result.destination,
    user: result.user,
  })
}

export async function logout(_req, res) {
  clearSessionCookie(res)

  res.status(200).json({
    message: "Logout berhasil.",
  })
}

export async function getSession(req, res) {
  const destination = ROLE_ROUTES[req.user.role] ?? "/login"

  res.status(200).json({
    authenticated: true,
    destination,
    user: req.user,
  })
}