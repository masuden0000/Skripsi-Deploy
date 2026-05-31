import { proxyToBackend } from "@/lib/backend-api"

type RouteContext = {
  params: Promise<{ id: string }>
}

export async function POST(_request: Request, context: RouteContext) {
  const { id } = await context.params
  return proxyToBackend(`/api/projects/${id}/generate`, {
    method: "POST",
  })
}
