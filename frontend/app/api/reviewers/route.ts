import { proxyToBackend } from "@/lib/backend-api"

export async function GET(request: Request) {
  return proxyToBackend("/api/reviewers", {
    method: "GET",
    cookie: request.headers.get("cookie"),
  })
}

export async function POST(request: Request) {
  const body = await request.text()
  return proxyToBackend("/api/reviewers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    cookie: request.headers.get("cookie"),
  })
}
