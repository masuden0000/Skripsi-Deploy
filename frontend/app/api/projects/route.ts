import { NextResponse } from "next/server"

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:4000"

function buildResponse(backendResponse: Response, responseText: string) {
  return new NextResponse(responseText, {
    status: backendResponse.status,
    headers: {
      "content-type": backendResponse.headers.get("content-type") ?? "application/json",
    },
  })
}

export async function GET(request: Request) {
  const backendResponse = await fetch(`${BACKEND_URL}/api/projects`, {
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

  const backendResponse = await fetch(`${BACKEND_URL}/api/projects`, {
    method: "POST",
    body: formData,
    cache: "no-store",
  })

  const responseText = await backendResponse.text()
  return buildResponse(backendResponse, responseText)
}

// PUT - Generate signed upload URL for direct upload to Supabase
export async function PUT(request: Request) {
  const { bucket, projectId, fileName } = await request.json()

  const formData = new FormData()
  formData.append("skema", "")
  formData.append("tahun", "")
  formData.append("judul", "")
  formData.append("file_name", fileName)

  const backendResponse = await fetch(`${BACKEND_URL}/api/projects/upload-url`, {
    method: "POST",
    body: formData,
    cache: "no-store",
  })

  const responseText = await backendResponse.text()
  return buildResponse(backendResponse, responseText)
}
