import { proxyToAiBackend } from "@/lib/backend-api"

export async function POST(request: Request) {
  const formData = await request.formData()
  return proxyToAiBackend("/api/validation/bulk", {
    method: "POST",
    body: formData,
  })
}
