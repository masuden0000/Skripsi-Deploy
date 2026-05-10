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

export async function GET(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { id } = await context.params

  const backendResponse = await fetch(`${getBackendBaseUrl()}/api/faculties/${id}/reviewers`, {
    method: "GET",
    headers: {
      cookie: request.headers.get("cookie") ?? "",
    },
    cache: "no-store",
  })

  const responseText = await backendResponse.text()
  return buildResponse(backendResponse, responseText)
}