import { apiRequest } from "./client"
import {
  authLoginSchema,
  authLoginResponseSchema,
  type AuthLoginInput,
  type AuthLoginResponse,
} from "@/lib/schemas"

export interface LoginError {
  error: string
}

export async function login(
  credentials: AuthLoginInput
): Promise<{ data: AuthLoginResponse | null; error: string | null }> {
  return apiRequest("POST", "/api/auth/login", credentials, authLoginResponseSchema)
}

export interface SessionUser {
  id: string
  email: string
  role: string
}

export interface SessionResponse {
  authenticated: boolean
  destination: string
  user: SessionUser
}

export async function getSession(): Promise<{ data: SessionResponse | null; error: string | null }> {
  return apiRequest("GET", "/api/auth/session")
}

