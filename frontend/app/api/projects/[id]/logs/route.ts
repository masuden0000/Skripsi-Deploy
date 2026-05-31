import { NextResponse } from "next/server"
import { getBackendBaseUrl } from "@/lib/backend-api"

type RouteContext = {
  params: Promise<{ id: string }>
}

export async function GET(request: Request, context: RouteContext) {
  const { id } = await context.params
  const acceptsSSE = request.headers.get("accept")?.includes("text/event-stream")
  const sinceId = new URL(request.url).searchParams.get("since_id") || "0"
  const sinceParam = sinceId !== "0" ? `?since_id=${sinceId}` : ""
  const backendUrl = getBackendBaseUrl()

  if (!acceptsSSE) {
    try {
      const response = await fetch(`${backendUrl}/api/projects/${id}/logs${sinceParam}`, {
        headers: { accept: "application/json" },
        cache: "no-store",
      })
      const data = await response.json()
      return NextResponse.json(data, { status: response.status })
    } catch {
      return NextResponse.json(
        { error: "Tidak dapat menjangkau server backend." },
        { status: 503 }
      )
    }
  }

  try {
    const response = await fetch(`${backendUrl}/api/projects/${id}/logs${sinceParam}`, {
      headers: {
        accept: "text/event-stream",
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
  } catch {
    return NextResponse.json(
      { error: "Tidak dapat menjangkau server backend." },
      { status: 503 }
    )
  }
}
