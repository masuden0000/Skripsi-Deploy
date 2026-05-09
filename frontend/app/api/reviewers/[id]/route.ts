import { NextResponse } from "next/server"
import { getBackendBaseUrl } from "@/lib/backend-api"

function buildResponse(backendResponse: Response, responseText: string) {
  return new NextResponse(responseText, {
    status: backendResponse.status,
    headers: {
      "content-type": backendResponse.headers.get("content-type") ?? "application/json",
    },
  })
}

export async function PUT(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { id } = await context.params
  const body = await request.text()

  const backendResponse = await fetch(`${getBackendBaseUrl()}/api/reviewers/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      cookie: request.headers.get("cookie") ?? "",
    },
    body,
    cache: "no-store",
  })

  const responseText = await backendResponse.text()
  return buildResponse(backendResponse, responseText)
}

export async function DELETE(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { id } = await context.params

  const backendResponse = await fetch(`${getBackendBaseUrl()}/api/reviewers/${id}`, {
    method: "DELETE",
    headers: {
      cookie: request.headers.get("cookie") ?? "",
    },
    cache: "no-store",
  })

  const responseText = await backendResponse.text()
  return buildResponse(backendResponse, responseText)
}
