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

export async function GET(request: Request) {
  const backendResponse = await fetch(`${getBackendBaseUrl()}/api/reviewers`, {
    method: "GET",
    headers: {
      cookie: request.headers.get("cookie") ?? "",
    },
    cache: "no-store",
  })

  const responseText = await backendResponse.text()
  return buildResponse(backendResponse, responseText)
}

export async function POST(request: Request) {
  const body = await request.text()

  const backendResponse = await fetch(`${getBackendBaseUrl()}/api/reviewers`, {
    method: "POST",
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
