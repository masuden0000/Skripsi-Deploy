import { proxyToAiBackend } from "@/lib/backend-api"

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await params
  return proxyToAiBackend(`/api/validation/jobs/${encodeURIComponent(jobId)}`)
}
