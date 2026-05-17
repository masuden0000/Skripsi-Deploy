import { NextResponse } from "next/server"
import { getBackendBaseUrl } from "@/lib/backend-api"

export async function GET(request: Request) {
  const backendResponse = await fetch(`${getBackendBaseUrl()}/api/auth/session`, {
    method: "GET",
    headers: {
      cookie: request.headers.get("cookie") ?? "",
    },
    cache: "no-store",
  })

  const responseText = await backendResponse.text()
  return new NextResponse(responseText, {
    status: backendResponse.status,
    headers: {
      "content-type": backendResponse.headers.get("content-type") ?? "application/json",
    },
  })
}
