import { proxyToBackend } from "@/lib/backend-api"

type RouteContext = {
  params: Promise<{ id: string }>
}

export async function GET(_req: Request, context: RouteContext) {
  const { id } = await context.params
  return proxyToBackend(`/api/projects/${id}/placeholders`, {
    method: "GET",
  })
}
