import { NextResponse } from "next/server"
import { getBackendBaseUrl } from "@/lib/backend-api"

export async function POST(request: Request) {
  const backendResponse = await fetch(`${getBackendBaseUrl()}/api/auth/logout`, {
    method: "POST",
    headers: {
      cookie: request.headers.get("cookie") ?? "",
    },
    cache: "no-store",
  })

  const responseText = await backendResponse.text()
  const response = new NextResponse(responseText, {
    status: backendResponse.status,
    headers: {
      "content-type": backendResponse.headers.get("content-type") ?? "application/json",
    },
  })

  const setCookie = backendResponse.headers.get("set-cookie")
  if (setCookie) {
    response.headers.set("set-cookie", setCookie)
  }

  return response
}
