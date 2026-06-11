import { getAiBackendBaseUrl } from "@/lib/backend-api"

/**
 * GET /api/pkm/validation/export/[sessionId]?schema_name=...
 *
 * Proxy ke FastAPI GET /api/validation/export/{session_id} yang mengembalikan
 * file Excel (.xlsx) berisi ringkasan LLM per dokumen dalam satu bulk session.
 *
 * Response binary di-forward langsung sebagai ArrayBuffer agar tidak corrupt.
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  const { sessionId } = await params
  const schemaName = new URL(request.url).searchParams.get("schema_name") ?? ""

  const aiUrl =
    `${getAiBackendBaseUrl()}/api/validation/export/${encodeURIComponent(sessionId)}` +
    (schemaName ? `?schema_name=${encodeURIComponent(schemaName)}` : "")

  try {
    const aiRes = await fetch(aiUrl, { cache: "no-store" })

    if (!aiRes.ok) {
      // Kembalikan pesan error dari FastAPI sebagai JSON
      const text = await aiRes.text()
      return new Response(text, {
        status: aiRes.status,
        headers: { "content-type": "application/json" },
      })
    }

    const buffer = await aiRes.arrayBuffer()
    const disposition =
      aiRes.headers.get("content-disposition") ??
      `attachment; filename="ringkasan-validasi-${sessionId.slice(0, 8)}.xlsx"`

    return new Response(buffer, {
      status: 200,
      headers: {
        "content-type":
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "content-disposition": disposition,
      },
    })
  } catch (err) {
    const message = err instanceof Error ? `${err.name}: ${err.message}` : String(err)
    console.error("[export/route] fetch failed:", message)
    return Response.json(
      { error: "Tidak dapat menjangkau server backend.", detail: message },
      { status: 503 }
    )
  }
}
