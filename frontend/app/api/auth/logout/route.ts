import { proxyToBackend } from "@/lib/backend-api"

export async function POST(request: Request) {
  return proxyToBackend("/api/auth/logout", {
    method: "POST",
    cookie: request.headers.get("cookie"),
    forwardSetCookie: true,
  })
}
