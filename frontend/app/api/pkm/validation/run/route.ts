import { proxyToBackend } from "@/lib/backend-api"

export async function POST(request: Request) {
  const formData = await request.formData()
  return proxyToBackend("/api/pkm/validation/run", {
    method: "POST",
    body: formData,
  })
}
