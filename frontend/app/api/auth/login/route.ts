import { NextResponse } from "next/server"
import { getBackendBaseUrl } from "@/lib/backend-api"

export async function POST(request: Request) {
  const body = await request.text()

  const backendResponse = await fetch(`${getBackendBaseUrl()}/api/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      cookie: request.headers.get("cookie") ?? "",
    },
    body,
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
    // Forward session cookie so the browser stores it on the frontend origin.
    response.headers.set("set-cookie", setCookie)
  }

  return response
}
