import { proxyToBackend } from "@/lib/backend-api"

export async function POST(request: Request) {
  const body = await request.text()
  return proxyToBackend("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    cookie: request.headers.get("cookie"),
    forwardSetCookie: true,
  })
}
