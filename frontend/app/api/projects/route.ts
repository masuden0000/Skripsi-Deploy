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

export async function GET() {
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
  const contentType = request.headers.get("content-type") ?? ""
  let formData: FormData

  if (contentType.includes("multipart/form-data")) {
    formData = await request.formData()
  } else {
    const payload = await request.json()
    formData = new FormData()
    formData.append("skema", payload.skema ?? "")
    formData.append("tahun", payload.tahun ?? "")
    formData.append("file_name", payload.file_name ?? payload.fileName ?? "")
  }

  const backendResponse = await fetch(`${BACKEND_URL}/api/projects/upload-url`, {
    method: "POST",
    body: formData,
    cache: "no-store",
  })

  const responseText = await backendResponse.text()
  return buildResponse(backendResponse, responseText)
}
