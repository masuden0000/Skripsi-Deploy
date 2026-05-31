import { proxyToBackend } from "@/lib/backend-api"

export async function GET(request: Request) {
  return proxyToBackend("/api/reviewer-assignments", {
    method: "GET",
    cookie: request.headers.get("cookie"),
  })
}
