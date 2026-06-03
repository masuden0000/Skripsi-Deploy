import { NextResponse } from "next/server"

const DEFAULT_BACKEND_URL = "http://127.0.0.1:4000"
const DEFAULT_AI_BACKEND_URL = "http://127.0.0.1:8000"

export function getBackendBaseUrl() {
  return process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL
}

export function getAiBackendBaseUrl() {
  return process.env.NEXT_PUBLIC_AI_BACKEND_URL || DEFAULT_AI_BACKEND_URL
}

type ProxyOptions = Omit<RequestInit, "cache" | "headers"> & {
  headers?: Record<string, string>
  /** Cookie header yang diteruskan ke backend (isi dengan request.headers.get("cookie")) */
  cookie?: string | null
  /** Jika true, header set-cookie dari backend diteruskan kembali ke browser */
  forwardSetCookie?: boolean
}

/**
 * Proxy request ke backend dengan error handling.
 * Jika backend tidak terjangkau (network error), mengembalikan HTTP 503.
 */
export async function proxyToBackend(
  path: string,
  options: ProxyOptions = {}
): Promise<NextResponse> {
  const { cookie, forwardSetCookie, headers: extraHeaders, ...fetchOptions } = options

  const headers: Record<string, string> = { ...(extraHeaders ?? {}) }
  if (cookie) {
    headers["cookie"] = cookie
  }

  try {
    const backendResponse = await fetch(`${getBackendBaseUrl()}${path}`, {
      ...fetchOptions,
      headers,
      cache: "no-store",
    })

    const responseText = await backendResponse.text()
    const response = new NextResponse(responseText, {
      status: backendResponse.status,
      headers: {
        "content-type": backendResponse.headers.get("content-type") ?? "application/octet-stream",
      },
    })

    if (forwardSetCookie) {
      for (const setCookieValue of backendResponse.headers.getSetCookie()) {
        response.headers.append("set-cookie", setCookieValue)
      }
    }

    return response
  } catch (err) {
    const message = err instanceof Error ? `${err.name}: ${err.message}` : String(err)
    console.error("[proxyToBackend] fetch failed:", message, "→ path:", path)
    return NextResponse.json(
      { error: "Tidak dapat menjangkau server backend.", detail: message },
      { status: 503 }
    )
  }
}

/**
 * Proxy request langsung ke AI backend (FastAPI) tanpa melalui Express.
 */
export async function proxyToAiBackend(
  path: string,
  options: ProxyOptions = {}
): Promise<NextResponse> {
  const { cookie, forwardSetCookie, headers: extraHeaders, ...fetchOptions } = options

  const headers: Record<string, string> = { ...(extraHeaders ?? {}) }
  if (cookie) {
    headers["cookie"] = cookie
  }

  try {
    const backendResponse = await fetch(`${getAiBackendBaseUrl()}${path}`, {
      ...fetchOptions,
      headers,
      cache: "no-store",
    })

    const responseText = await backendResponse.text()
    const response = new NextResponse(responseText, {
      status: backendResponse.status,
      headers: {
        "content-type": backendResponse.headers.get("content-type") ?? "application/octet-stream",
      },
    })

    if (forwardSetCookie) {
      for (const setCookieValue of backendResponse.headers.getSetCookie()) {
        response.headers.append("set-cookie", setCookieValue)
      }
    }

    return response
  } catch (err) {
    const message = err instanceof Error ? `${err.name}: ${err.message}` : String(err)
    console.error("[proxyToAiBackend] fetch failed:", message, "→ path:", path)
    return NextResponse.json(
      { error: "Tidak dapat menjangkau server backend.", detail: message },
      { status: 503 }
    )
  }
}
