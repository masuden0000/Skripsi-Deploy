import { proxyToBackend } from "@/lib/backend-api"

export async function GET(request: Request) {
  return proxyToBackend("/api/auth/session", {
    method: "GET",
    cookie: request.headers.get("cookie"),
  })
}
