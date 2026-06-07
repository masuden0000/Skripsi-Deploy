import { proxyToAiBackend } from "@/lib/backend-api"

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  const { sessionId } = await params
  return proxyToAiBackend(`/api/validation/sessions/${encodeURIComponent(sessionId)}`)
}
