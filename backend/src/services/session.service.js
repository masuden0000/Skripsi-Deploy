import jwt from "jsonwebtoken"
import { env } from "../config/env.js"
import { AppError } from "../utils/app-error.js"
import { getProfileByUserId } from "./profile.service.js"

export function createSessionToken({ userId, email, role }) {
  return jwt.sign(
    {
      sub: userId,
      email,
      role,
    },
    env.SESSION_SECRET
  )
}

export async function resolveSessionUser(token) {
  try {
    const payload = jwt.verify(token, env.SESSION_SECRET)
    const profile = await getProfileByUserId(payload.sub)

    return {
      id: payload.sub,
      email: typeof payload.email === "string" ? payload.email : "",
      role: profile.role,
    }
  } catch (error) {
    if (error instanceof AppError) {
      throw error
    }

    throw new AppError("Session login tidak valid atau sudah berakhir.", 401)
  }
}
