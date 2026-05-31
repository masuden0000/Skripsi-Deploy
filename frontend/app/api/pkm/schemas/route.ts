import { proxyToBackend } from "@/lib/backend-api"

export async function GET() {
  return proxyToBackend("/api/pkm/schemas", {
    method: "GET",
  })
}
