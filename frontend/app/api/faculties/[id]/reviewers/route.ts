import { proxyToBackend } from "@/lib/backend-api"

export async function GET(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { id } = await context.params
  return proxyToBackend(`/api/faculties/${id}/reviewers`, {
    method: "GET",
    cookie: request.headers.get("cookie"),
  })
}
