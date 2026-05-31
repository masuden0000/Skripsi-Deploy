import { proxyToBackend } from "@/lib/backend-api"

type RouteContext = {
  params: Promise<{ id: string }>
}

export async function GET(_request: Request, context: RouteContext) {
  const { id } = await context.params
  return proxyToBackend(`/api/projects/${id}`, {
    method: "GET",
  })
}

export async function DELETE(_request: Request, context: RouteContext) {
  const { id } = await context.params
  return proxyToBackend(`/api/projects/${id}`, {
    method: "DELETE",
  })
}
