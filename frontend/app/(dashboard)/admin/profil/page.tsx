"use client"

import { useEffect, useState, useTransition } from "react"
import Image from "next/image"
import {
  AdminPageHeader,
  AdminSurfaceCard,
  PasswordInput,
} from "@/components/admin/shared"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { getSession, updateProfile } from "@/lib/api"

export default function ProfilPage() {
  const [currentEmail, setCurrentEmail] = useState("")
  const [newEmail, setNewEmail] = useState("")
  const [emailError, setEmailError] = useState("")
  const [emailSuccess, setEmailSuccess] = useState("")
  const [isEmailPending, startEmailTransition] = useTransition()

  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [passwordError, setPasswordError] = useState("")
  const [passwordSuccess, setPasswordSuccess] = useState("")
  const [isPasswordPending, startPasswordTransition] = useTransition()

  useEffect(() => {
    getSession().then(({ data }) => {
      if (data?.user?.email) setCurrentEmail(data.user.email)
    })
  }, [])

  function handleEmailSubmit(e: React.FormEvent) {
    e.preventDefault()
    setEmailError("")
    setEmailSuccess("")
    startEmailTransition(async () => {
      const { error } = await updateProfile({ type: "email", newEmail })
      if (error) {
        setEmailError(error)
        return
      }
      setCurrentEmail(newEmail)
      setNewEmail("")
      setEmailSuccess("Email berhasil diperbarui.")
    })
  }

  function handlePasswordSubmit(e: React.FormEvent) {
    e.preventDefault()
    setPasswordError("")
    setPasswordSuccess("")
    if (newPassword !== confirmPassword) {
      setPasswordError("Konfirmasi password tidak sesuai.")
      return
    }
    startPasswordTransition(async () => {
      const { error } = await updateProfile({
        type: "password",
        currentPassword,
        newPassword,
      })
      if (error) {
        setPasswordError(error)
        return
      }
      setCurrentPassword("")
      setNewPassword("")
      setConfirmPassword("")
      setPasswordSuccess("Password berhasil diperbarui.")
    })
  }

  const canSubmitEmail = Boolean(newEmail) && !isEmailPending
  const canSubmitPassword =
    Boolean(currentPassword) && Boolean(newPassword) && Boolean(confirmPassword) && !isPasswordPending

  return (
    <div className="px-8 py-8">
      <AdminPageHeader
        title="Profil Saya"
        description="Kelola email dan password akun Anda"
      />

      <div className="flex flex-col gap-6 max-w-lg">
        {/* Email */}
        <AdminSurfaceCard>
          <div className="px-6 py-5 border-b border-gray-100">
            <h2 className="text-base font-semibold text-gray-800">Ubah Email</h2>
            <p className="mt-0.5 text-xs text-[rgba(0,0,0,0.4)]">
              Email saat ini:{" "}
              <span className="font-medium text-gray-600">{currentEmail || "—"}</span>
            </p>
          </div>
          <form onSubmit={handleEmailSubmit} className="flex flex-col gap-5 px-6 py-5">
            <div className="flex flex-col gap-2">
              <Label htmlFor="newEmail" className="text-sm font-medium text-pkm-900">
                Email Baru
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
                  id="newEmail"
                  type="email"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="Masukkan email baru"
                  required
                  disabled={isEmailPending}
                  className="h-11 rounded-lg border-pkm-400 pl-10 text-sm placeholder:text-gray-400 focus-visible:ring-pkm-600"
                />
              </div>
            </div>

            {emailError && (
              <Alert variant="destructive" className="py-2">
                <AlertDescription className="text-sm">{emailError}</AlertDescription>
              </Alert>
            )}
            {emailSuccess && (
              <Alert className="py-2 border-pkm-100 bg-pkm-50">
                <AlertDescription className="text-sm text-pkm-700">{emailSuccess}</AlertDescription>
              </Alert>
            )}

            <Button
              type="submit"
              disabled={!canSubmitEmail}
              className="h-11 w-full rounded-lg text-sm font-medium text-white disabled:opacity-50"
              style={
                canSubmitEmail
                  ? {
                      background: "linear-gradient(90deg, #009966 0%, #00bc7d 100%)",
                      boxShadow:
                        "0px 10px 7.5px rgba(164,244,207,0.6), 0px 4px 3px rgba(164,244,207,0.4)",
                    }
                  : { background: "#a4f4cf" }
              }
            >
              {isEmailPending ? "Memproses..." : "Simpan Email"}
            </Button>
          </form>
        </AdminSurfaceCard>

        {/* Password */}
        <AdminSurfaceCard>
          <div className="px-6 py-5 border-b border-gray-100">
            <h2 className="text-base font-semibold text-gray-800">Ubah Password</h2>
            <p className="mt-0.5 text-xs text-[rgba(0,0,0,0.4)]">
              Gunakan password yang kuat dan unik
            </p>
          </div>
          <form onSubmit={handlePasswordSubmit} className="flex flex-col gap-5 px-6 py-5">
            <div className="flex flex-col gap-2">
              <Label htmlFor="currentPassword" className="text-sm font-medium text-pkm-900">
                Password Lama
              </Label>
              <PasswordInput
                id="currentPassword"
                name="currentPassword"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Masukkan password lama"
                required
                disabled={isPasswordPending}
                showLockIcon
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="newPassword" className="text-sm font-medium text-pkm-900">
                Password Baru
              </Label>
              <PasswordInput
                id="newPassword"
                name="newPassword"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Masukkan password baru"
                required
                disabled={isPasswordPending}
                showLockIcon
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="confirmPassword" className="text-sm font-medium text-pkm-900">
                Konfirmasi Password Baru
              </Label>
              <PasswordInput
                id="confirmPassword"
                name="confirmPassword"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Ulangi password baru"
                required
                disabled={isPasswordPending}
                showLockIcon
              />
            </div>

            {passwordError && (
              <Alert variant="destructive" className="py-2">
                <AlertDescription className="text-sm">{passwordError}</AlertDescription>
              </Alert>
            )}
            {passwordSuccess && (
              <Alert className="py-2 border-pkm-100 bg-pkm-50">
                <AlertDescription className="text-sm text-pkm-700">{passwordSuccess}</AlertDescription>
              </Alert>
            )}

            <Button
              type="submit"
              disabled={!canSubmitPassword}
              className="h-11 w-full rounded-lg text-sm font-medium text-white disabled:opacity-50"
              style={
                canSubmitPassword
                  ? {
                      background: "linear-gradient(90deg, #009966 0%, #00bc7d 100%)",
                      boxShadow:
                        "0px 10px 7.5px rgba(164,244,207,0.6), 0px 4px 3px rgba(164,244,207,0.4)",
                    }
                  : { background: "#a4f4cf" }
              }
            >
              {isPasswordPending ? "Memproses..." : "Simpan Password"}
            </Button>
          </form>
        </AdminSurfaceCard>
      </div>
    </div>
  )
}
