import { proxyToBackend } from "@/lib/backend-api"

export async function POST(request: Request) {
  const formData = await request.formData()
  return proxyToBackend("/api/projects/confirm-upload", {
    method: "POST",
    body: formData,
  })
}
