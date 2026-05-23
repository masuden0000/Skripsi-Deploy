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

export async function GET() {
  const backendResponse = await fetch(`${getBackendBaseUrl()}/api/pkm/schemas`, {
    method: "GET",
    headers: { "content-type": "application/json" },
    cache: "no-store",
  })

  const responseText = await backendResponse.text()
  return buildResponse(backendResponse, responseText)
}
