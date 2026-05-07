"use client"

import { useState, useTransition } from "react"
import Image from "next/image"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { login } from "@/app/actions/auth"

const ROLES = [
  { value: "admin",    label: "Admin" },
  { value: "reviewer", label: "Reviewer" },
]

export default function LoginForm() {
  const [role, setRole] = useState<string>("")
  const [error, setError] = useState<string>("")
  const [isPending, startTransition] = useTransition()

  const canSubmit = Boolean(role) && !isPending

  function handleSubmit(formData: FormData) {
    setError("")
    formData.set("role", role)
    startTransition(async () => {
      const result = await login(formData)
      if (result?.error) {
        setError(result.error)
      }
    })
  }

  return (
    <div
      className="w-full overflow-hidden rounded-xl border border-pkm-100 bg-white/95"
      style={{ boxShadow: "0px 25px 50px 0px rgba(0,0,0,0.25)" }}
    >
      {/* Header: logo + judul */}
      <div className="flex flex-col items-center px-6 pb-0 pt-10">
        <div className="relative mb-5">
          <div
            className="absolute inset-0 rounded-full blur-[24px]"
            style={{
              background:
                "linear-gradient(135deg, rgba(0,212,146,0.3) 0%, rgba(5,223,114,0.3) 100%)",
            }}
          />
          <div className="relative flex size-28 items-end justify-center rounded-full bg-white px-4 pt-4 shadow-[0px_10px_15px_0px_rgba(0,0,0,0.1),0px_4px_6px_0px_rgba(0,0,0,0.1)]">
            <Image
              src="/logo-upnvj.png"
              alt="Logo UPNVJ"
              width={80}
              height={80}
              className="mb-2 object-contain"
              priority
            />
          </div>
        </div>

        <h1 className="text-center text-base font-semibold text-pkm-900">
          Sistem Review PKM
        </h1>
        <p
          className="mt-1 text-center text-[13px]"
          style={{ color: "rgba(0,153,102,0.8)" }}
        >
          Universitas Pembangunan Nasional Veteran Jakarta
        </p>
      </div>

      {/* Form */}
      <form action={handleSubmit} className="flex flex-col gap-5 px-6 py-8">
        {/* Role checkbox */}
        <div className="flex flex-col gap-2">
          <Label className="text-sm font-medium text-pkm-900">
            Masuk sebagai
          </Label>
          <div className="flex gap-3">
            {ROLES.map((r) => {
              const active = role === r.value
              return (
                <button
                  key={r.value}
                  type="button"
                  onClick={() => setRole(r.value)}
                  className="flex flex-1 items-center gap-2.5 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors"
                  style={
                    active
                      ? {
                          borderColor: "#009966",
                          background: "#ecfdf5",
                          color: "#004f3b",
                        }
                      : {
                          borderColor: "#a4f4cf",
                          background: "#fff",
                          color: "#6b7280",
                        }
                  }
                >
                  {/* Checkbox indicator */}
                  <span
                    className="flex size-4 shrink-0 items-center justify-center rounded border-2 transition-colors"
                    style={
                      active
                        ? { borderColor: "#009966", background: "#009966" }
                        : { borderColor: "#a4f4cf", background: "#fff" }
                    }
                  >
                    {active && (
                      <svg
                        viewBox="0 0 10 8"
                        className="size-2.5"
                        fill="none"
                        stroke="white"
                        strokeWidth={2}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M1 4l2.5 2.5L9 1" />
                      </svg>
                    )}
                  </span>
                  {r.label}
                </button>
              )
            })}
          </div>
        </div>

        {/* Email */}
        <div className="flex flex-col gap-2">
          <Label htmlFor="email" className="text-sm font-medium text-pkm-900">
            Username
          </Label>
          <div className="relative">
            <Image
              src="/icon-user.svg"
              alt=""
              width={20}
              height={20}
              aria-hidden
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2"
            />
            <Input
              id="email"
              name="email"
              type="email"
              placeholder="Masukkan username"
              required
              className="h-11 rounded-lg border-pkm-400 pl-10 text-sm placeholder:text-gray-400 focus-visible:ring-pkm-600"
            />
          </div>
        </div>

        {/* Password */}
        <div className="flex flex-col gap-2">
          <Label
            htmlFor="password"
            className="text-sm font-medium text-pkm-900"
          >
            Password
          </Label>
          <div className="relative">
            <Image
              src="/icon-lock.svg"
              alt=""
              width={20}
              height={20}
              aria-hidden
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2"
            />
            <Input
              id="password"
              name="password"
              type="password"
              placeholder="Masukkan password"
              required
              className="h-11 rounded-lg border-pkm-400 pl-10 text-sm placeholder:text-gray-400 focus-visible:ring-pkm-600"
            />
          </div>
        </div>

        {/* Error alert */}
        {error && (
          <Alert variant="destructive" className="py-2">
            <AlertDescription className="text-sm">{error}</AlertDescription>
          </Alert>
        )}

        {/* Submit button */}
        <Button
          type="submit"
          disabled={!canSubmit}
          className="h-11 w-full rounded-lg text-sm font-medium text-white disabled:opacity-50"
          style={
            canSubmit
              ? {
                  background:
                    "linear-gradient(90deg, #009966 0%, #00bc7d 100%)",
                  boxShadow:
                    "0px 10px 7.5px rgba(164,244,207,0.6), 0px 4px 3px rgba(164,244,207,0.4)",
                }
              : { background: "#a4f4cf" }
          }
        >
          {isPending ? "Memproses..." : "Masuk ke Dashboard"}
        </Button>
      </form>
    </div>
  )
}
