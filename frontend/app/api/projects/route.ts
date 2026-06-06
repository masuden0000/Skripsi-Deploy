import { proxyToBackend } from "@/lib/backend-api"

export async function GET() {
  return proxyToBackend("/api/projects", {
    method: "GET",
  })
}

export async function POST(request: Request) {
  const formData = await request.formData()
  return proxyToBackend("/api/projects", {
    method: "POST",
    body: formData,
  })
}

