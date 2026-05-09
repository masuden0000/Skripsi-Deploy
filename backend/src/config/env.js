import dotenv from "dotenv"

dotenv.config()

function requireEnv(name) {
  const value = process.env[name]

  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`)
  }

  return value
}

function toNumber(value, fallback) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function toList(value, fallback) {
  const source = value ?? fallback

  return source
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
}

export const env = {
  NODE_ENV: process.env.NODE_ENV ?? "development",
  PORT: toNumber(process.env.PORT, 4000),
  FRONTEND_URL: process.env.FRONTEND_URL ?? "http://127.0.0.1:3000",
  FRONTEND_URLS: toList(
    process.env.FRONTEND_URLS,
    `${process.env.FRONTEND_URL ?? "http://127.0.0.1:3000"},http://localhost:3000,http://127.0.0.1:3000`
  ),
  SUPABASE_URL: requireEnv("SUPABASE_URL"),
  SUPABASE_ANON_KEY: requireEnv("SUPABASE_ANON_KEY"),
  SUPABASE_SERVICE_ROLE_KEY: requireEnv("SUPABASE_SERVICE_ROLE_KEY"),
  SESSION_SECRET: requireEnv("SESSION_SECRET"),
  SESSION_COOKIE_NAME: process.env.SESSION_COOKIE_NAME ?? "app_session",
  SESSION_MAX_AGE_SECONDS: toNumber(process.env.SESSION_MAX_AGE_SECONDS, 60 * 60 * 24),
}
