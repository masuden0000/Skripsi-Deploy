import { NextResponse, type NextRequest } from "next/server"
import { ROLE_ROUTES } from "@/lib/roles"
import { getBackendBaseUrl } from "@/lib/backend-api"

/** Route prefix yang butuh autentikasi, dipetakan ke role yang diizinkan */
const PROTECTED_ROUTES: Record<string, string> = {
  "/admin": "admin",
  "/reviewer": "reviewer",
}

/** Halaman auth yang harus diblokir jika sudah login */
const AUTH_PATHS = ["/login"]

type SessionPayload = {
  authenticated?: boolean
  destination?: string
  user?: {
    role?: string
  }
}

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl
  const backendUrl = getBackendBaseUrl()

  const protectedPrefix = Object.keys(PROTECTED_ROUTES).find((prefix) =>
    pathname.startsWith(prefix)
  )

  let sessionPayload: SessionPayload | null = null

  try {
    const sessionResponse = await fetch(`${backendUrl}/api/auth/session`, {
      method: "GET",
      headers: {
        cookie: request.headers.get("cookie") ?? "",
      },
      cache: "no-store",
    })

    if (sessionResponse.ok) {
      sessionPayload = await sessionResponse.json()
    }
  } catch {
    // Jika backend tidak aktif, halaman login tetap boleh diakses.
  }

  const role = sessionPayload?.user?.role
  const isAuthenticated = Boolean(sessionPayload?.authenticated && role)

  if (!isAuthenticated && protectedPrefix) {
    return NextResponse.redirect(new URL("/login", request.url))
  }

  if (isAuthenticated) {
    if (AUTH_PATHS.some((path) => pathname.startsWith(path))) {
      const destination = sessionPayload?.destination ?? ROLE_ROUTES[role!] ?? "/login"
      return NextResponse.redirect(new URL(destination, request.url))
    }

    if (protectedPrefix) {
      const requiredRole = PROTECTED_ROUTES[protectedPrefix]
      if (role !== requiredRole) {
        const correctPath = ROLE_ROUTES[role!] ?? "/login"
        return NextResponse.redirect(new URL(correctPath, request.url))
      }
    }
  }

  return NextResponse.next({ request })
}

export const config = {
  matcher: [
    /*
     * Match semua path kecuali:
     * - _next/static (file statis Next.js)
     * - _next/image (optimisasi gambar)
     * - favicon.ico
     * - File gambar/aset publik
     */
    "/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
}
