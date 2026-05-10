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