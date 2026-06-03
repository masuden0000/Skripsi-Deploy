import { proxyToAiBackend } from "@/lib/backend-api"

export async function POST(request: Request) {
  const formData = await request.formData()
  return proxyToAiBackend("/api/validation/run", {
    method: "POST",
    body: formData,
  })
}
