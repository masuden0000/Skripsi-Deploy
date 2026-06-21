import { proxyToBackend } from "@/lib/backend-api"

type RouteContext = {
  params: Promise<{ id: string }>
}

export async function PATCH(request: Request, context: RouteContext) {
  const { id } = await context.params
  return proxyToBackend(`/api/reviewer-assignments/${id}/complete`, {
    method: "PATCH",
    cookie: request.headers.get("cookie"),
  })
}
