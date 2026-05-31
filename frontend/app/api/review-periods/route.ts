import { proxyToBackend } from "@/lib/backend-api"

export async function GET(request: Request) {
  return proxyToBackend("/api/review-periods", {
    method: "GET",
    cookie: request.headers.get("cookie"),
  })
}

export async function POST(request: Request) {
  const body = await request.text()
  return proxyToBackend("/api/review-periods", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    cookie: request.headers.get("cookie"),
  })
}
