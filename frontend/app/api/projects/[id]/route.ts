import { NextResponse } from "next/server"

const AI_BACKEND_URL = process.env.AI_BACKEND_URL || "http://127.0.0.1:8000"

type RouteContext = {
  params: Promise<{ id: string }>
}

function buildResponse(backendResponse: Response, responseText: string) {
  return new NextResponse(responseText, {
    status: backendResponse.status,
    headers: {
      "content-type": backendResponse.headers.get("content-type") ?? "application/json",
    },
  })
}

export async function GET(request: Request, context: RouteContext) {
  const { id } = await context.params

  const backendResponse = await fetch(`${AI_BACKEND_URL}/api/projects/${id}`, {
    method: "GET",
    headers: {
      "content-type": "application/json",
    },
    cache: "no-store",
  })

  const responseText = await backendResponse.text()
  return buildResponse(backendResponse, responseText)
}

export async function DELETE(request: Request, context: RouteContext) {
  const { id } = await context.params

  const backendResponse = await fetch(`${AI_BACKEND_URL}/api/projects/${id}`, {
    method: "DELETE",
    headers: {
      "content-type": "application/json",
    },
    cache: "no-store",
  })

  const responseText = await backendResponse.text()
  return buildResponse(backendResponse, responseText)
}