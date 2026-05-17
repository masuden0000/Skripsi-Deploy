"use client"

import { useState, useTransition } from "react"
import {
  AdminPageHeader,
  AdminSurfaceCard,
  PasswordInput,
} from "@/components/admin/shared"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { updateProfile } from "@/lib/api"

export default function ProfilReviewerPage() {
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [isPending, startTransition] = useTransition()

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    setSuccess("")

    if (newPassword !== confirmPassword) {
      setError("Konfirmasi password tidak sesuai.")
      return
    }

    startTransition(async () => {
      const { error: apiError } = await updateProfile({
        type: "password",
        currentPassword,
        newPassword,
      })
      if (apiError) {
        setError(apiError)
        return
      }
      setCurrentPassword("")
      setNewPassword("")
      setConfirmPassword("")
      setSuccess("Password berhasil diperbarui.")
    })
  }

  const canSubmit =
    Boolean(currentPassword) && Boolean(newPassword) && Boolean(confirmPassword) && !isPending

  return (
    <div className="px-8 py-8">
      <AdminPageHeader
        title="Profil Saya"
        description="Kelola password akun Anda"
      />

      <div className="width-full">
        <AdminSurfaceCard>
          <div className="px-6 py-5 border-b border-gray-100">
            <h2 className="text-base font-semibold text-gray-800">Ubah Password</h2>
            <p className="mt-0.5 text-xs text-[rgba(0,0,0,0.4)]">
              Gunakan password yang kuat dan unik
            </p>
          </div>
          <form onSubmit={handleSubmit} className="flex flex-col gap-5 px-6 py-5">
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
                disabled={isPending}
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
                disabled={isPending}
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
                disabled={isPending}
                showLockIcon
              />
            </div>

            {error && (
              <Alert variant="destructive" className="py-2">
                <AlertDescription className="text-sm">{error}</AlertDescription>
              </Alert>
            )}
            {success && (
              <Alert className="py-2 border-pkm-100 bg-pkm-50">
                <AlertDescription className="text-sm text-pkm-700">{success}</AlertDescription>
              </Alert>
            )}

            <Button
              type="submit"
              disabled={!canSubmit}
              className="h-11 w-full rounded-lg text-sm font-medium text-white disabled:opacity-50"
              style={
                canSubmit
                  ? {
                      background: "linear-gradient(90deg, #009966 0%, #00bc7d 100%)",
                      boxShadow:
                        "0px 10px 7.5px rgba(164,244,207,0.6), 0px 4px 3px rgba(164,244,207,0.4)",
                    }
                  : { background: "#a4f4cf" }
              }
            >
              {isPending ? "Memproses..." : "Simpan Password"}
            </Button>
          </form>
        </AdminSurfaceCard>
      </div>
    </div>
  )
}
