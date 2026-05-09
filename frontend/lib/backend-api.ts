const DEFAULT_BACKEND_URL = "http://127.0.0.1:4000"

export function getBackendBaseUrl() {
  return process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL
}
