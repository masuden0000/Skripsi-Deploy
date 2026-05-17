import { NextResponse } from "next/server"
import { getBackendBaseUrl } from "@/lib/backend-api"

export async function PATCH(request: Request) {
  const body = await request.text()

  const backendResponse = await fetch(`${getBackendBaseUrl()}/api/auth/profile`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      cookie: request.headers.get("cookie") ?? "",
    },
    body,
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
