"use client"

import { useState, useTransition } from "react"
import Image from "next/image"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { PasswordInput } from "@/components/admin/shared"
import { login } from "@/lib/api"
import type { AuthLoginInput } from "@/lib/schemas"

const ROLES = [
  { value: "admin",    label: "Admin" },
  { value: "reviewer", label: "Reviewer" },
]

export default function LoginForm() {
  const [role, setRole] = useState<string>("")
  const [error, setError] = useState<string>("")
  const [isPending, startTransition] = useTransition()

  const canSubmit = Boolean(role) && !isPending

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError("")
    const formData = new FormData(e.currentTarget)

    const credentials: AuthLoginInput = {
      email: formData.get("email") as string,
      password: formData.get("password") as string,
      role: role as "admin" | "reviewer",
    }

    startTransition(async () => {
      const { data, error: loginError } = await login(credentials)

      if (loginError) {
        setError(loginError)
        return
      }

      if (data?.destination) {
        window.location.assign(data.destination)
      } else {
        window.location.assign("/login")
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
      <form onSubmit={handleSubmit} className="flex flex-col gap-5 px-6 py-8">
        {/* Role selector */}
        <div className="flex flex-col gap-2">
          <Label className="text-sm font-medium text-pkm-900">
            Masuk sebagai
          </Label>
          <Select
            value={role || undefined}
            onValueChange={setRole}
          >
            <SelectTrigger className="h-11 rounded-lg border-pkm-400 text-sm focus:ring-pkm-600">
              <SelectValue placeholder="Pilih role akun" />
            </SelectTrigger>
            <SelectContent>
              {ROLES.map((r) => (
                <SelectItem key={r.value} value={r.value}>
                  {r.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
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
          <PasswordInput
            id="password"
            name="password"
            placeholder="Masukkan password"
            required
            showLockIcon
          />
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
