import { proxyToBackend } from "@/lib/backend-api"

type RouteContext = {
  params: Promise<{ id: string }>
}

export async function PUT(request: Request, context: RouteContext) {
  const { id } = await context.params
  const body = await request.text()
  return proxyToBackend(`/api/reviewers/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body,
    cookie: request.headers.get("cookie"),
  })
}

export async function DELETE(request: Request, context: RouteContext) {
  const { id } = await context.params
  return proxyToBackend(`/api/reviewers/${id}`, {
    method: "DELETE",
    cookie: request.headers.get("cookie"),
  })
}
