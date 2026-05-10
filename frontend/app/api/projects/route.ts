import { NextResponse } from "next/server"

const AI_BACKEND_URL = process.env.AI_BACKEND_URL || "http://127.0.0.1:8000"

function buildResponse(backendResponse: Response, responseText: string) {
  return new NextResponse(responseText, {
    status: backendResponse.status,
    headers: {
      "content-type": backendResponse.headers.get("content-type") ?? "application/json",
    },
  })
}

export async function GET(request: Request) {
  const backendResponse = await fetch(`${AI_BACKEND_URL}/api/projects`, {
    method: "GET",
    headers: {
      "content-type": "application/json",
    },
    cache: "no-store",
  })

  const responseText = await backendResponse.text()
  return buildResponse(backendResponse, responseText)
}

export async function POST(request: Request) {
  const formData = await request.formData()

  const backendResponse = await fetch(`${AI_BACKEND_URL}/api/projects`, {
    method: "POST",
    body: formData,
    cache: "no-store",
  })

  const responseText = await backendResponse.text()
  return buildResponse(backendResponse, responseText)
}