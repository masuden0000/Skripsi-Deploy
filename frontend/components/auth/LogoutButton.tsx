"use client"

import { useState, useTransition } from "react"
import { Button } from "@/components/ui/button"

export default function LogoutButton() {
  const [error, setError] = useState("")
  const [isPending, startTransition] = useTransition()

  function handleLogout() {
    setError("")

    startTransition(async () => {
      try {
        const response = await fetch("/api/auth/logout", {
          method: "POST",
          credentials: "include",
        })

        if (!response.ok) {
          const payload = await response.json().catch(() => null)
          throw new Error(payload?.error || "Logout gagal. Coba lagi.")
        }

        window.location.assign("/login")
      } catch (caughtError) {
        setError(
          caughtError instanceof Error
            ? caughtError.message
            : "Logout gagal. Coba lagi."
        )
      }
    })
  }

  return (
    <div>
      <Button
        type="button"
        variant="outline"
        disabled={isPending}
        onClick={handleLogout}
        className="h-10 w-full justify-center border-red-200 text-red-600 hover:border-red-300 hover:bg-red-50 hover:text-red-700 disabled:opacity-60"
      >
        <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 3h3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-3" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M10 17l5-5-5-5" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 12H3" />
        </svg>
        {isPending ? "Memproses..." : "Logout"}
      </Button>

      {error ? <p className="mt-2 text-xs text-red-600">{error}</p> : null}
    </div>
  )
}
