import { proxyToBackend } from "@/lib/backend-api"

export async function GET() {
  return proxyToBackend("/api/projects", {
    method: "GET",
  })
}

export async function POST(request: Request) {
  const formData = await request.formData()
  return proxyToBackend("/api/projects", {
    method: "POST",
    body: formData,
  })
}

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

  return proxyToBackend("/api/projects/upload-url", {
    method: "POST",
    body: formData,
  })
}
