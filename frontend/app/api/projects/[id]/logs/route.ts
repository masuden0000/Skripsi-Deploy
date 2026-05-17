import { NextResponse } from "next/server"

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:4000"

type RouteContext = {
  params: Promise<{ id: string }>
}

export async function GET(request: Request, context: RouteContext) {
  const { id } = await context.params
  const acceptsSSE = request.headers.get("accept")?.includes("text/event-stream")

  if (!acceptsSSE) {
    // JSON snapshot — untuk memuat log historis saat restore halaman
    const response = await fetch(`${BACKEND_URL}/api/projects/${id}/logs`, {
      headers: { accept: "application/json" },
      cache: "no-store",
    })
    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  }

  // SSE streaming — untuk real-time log saat proses berjalan
  const response = await fetch(`${BACKEND_URL}/api/projects/${id}/logs`, {
    headers: {
      "accept": "text/event-stream",
      "cache-control": "no-cache",
    },
  })

  if (!response.ok) {
    return new NextResponse("Failed to connect to log stream", { status: 502 })
  }

  const stream = response.body
  if (!stream) {
    return new NextResponse("No stream available", { status: 500 })
  }

  return new NextResponse(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no",
    },
  })
}
