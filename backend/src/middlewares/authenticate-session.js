import { env } from "../config/env.js"
import { resolveSessionUser } from "../services/session.service.js"
import { AppError } from "../utils/app-error.js"

export async function authenticateSession(req, _res, next) {
  try {
    const token = req.cookies?.[env.SESSION_COOKIE_NAME]

    if (!token) {
      throw new AppError("Session login tidak ditemukan.", 401)
    }

    req.user = await resolveSessionUser(token)
    next()
  } catch (error) {
    next(error)
  }
}
