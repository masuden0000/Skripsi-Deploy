import { proxyToAiBackend } from "@/lib/backend-api"

export async function POST(request: Request) {
  const body = await request.json()
  return proxyToAiBackend("/api/validation/summarize", {
    method: "POST",
    body: JSON.stringify(body),
    headers: { "Content-Type": "application/json" },
  })
}
