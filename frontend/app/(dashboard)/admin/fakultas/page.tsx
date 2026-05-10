"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import {
  AdminMetricCard,
  AdminModalShell,
  AdminPageHeader,
  AdminSurfaceCard,
  SearchInput,
} from "@/components/admin/shared"
import {
  ArrowLeftIcon,
  DetailIcon,
  EditIcon,
  GraduationIcon,
  PlusIcon,
  TrashIcon,
  UserIcon,
} from "@/components/icons/public-icons"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

type Faculty = {
  id: string
  code: string
  name: string
  reviewerCount: number
}

type Reviewer = {
  id: string
  nama: string
  email: string
  isActive: boolean
}

type FacultyFormData = {
  name: string
  code: string
}

type FacultyApiResponse = {
  data?: Faculty | Faculty[]
  error?: string
  message?: string
}

type ReviewerApiResponse = {
  data?: Reviewer | Reviewer[]
  error?: string
}

async function readApiResponse(response: Response) {
  const text = await response.text()

  if (!text) {
    return {}
  }

  try {
    return JSON.parse(text) as FacultyApiResponse | ReviewerApiResponse
  } catch {
    return { error: "Respons server tidak valid." }
  }
}

function getReviewerInitials(nama: string) {
  return nama
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((bagian) => bagian[0]?.toUpperCase() ?? "")
    .join("")
}

function mapStatusLabel(isActive: boolean) {
  return isActive ? "Aktif" : "Tidak Aktif"
}

function FacultyModal({
  faculty,
  isSubmitting,
  errorMessage,
  onClose,
  onSave,
}: {
  faculty: Faculty | null
  isSubmitting: boolean
  errorMessage: string | null
  onClose: () => void
  onSave: (data: FacultyFormData) => Promise<void>
}) {
  const [name, setName] = useState(faculty?.name ?? "")
  const [code, setCode] = useState(faculty?.code ?? "")
  const [localError, setLocalError] = useState<string | null>(null)
  const isEditMode = Boolean(faculty)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!name.trim() || !code.trim()) {
      setLocalError("Nama fakultas dan kode fakultas wajib diisi.")
      return
    }

    setLocalError(null)
    await onSave({
      name: name.trim(),
      code: code.trim().toUpperCase(),
    })
  }

  return (
    <AdminModalShell
      title={isEditMode ? "Edit Fakultas" : "Tambah Fakultas"}
      description={
        isEditMode
          ? "Perbarui nama dan kode fakultas."
          : "Tambahkan fakultas baru untuk dipakai pada data reviewer."
      }
      onClose={onClose}
      maxWidthClassName="max-w-md"
    >
      <form onSubmit={handleSubmit} className="space-y-4 px-6 py-5">
        <div className="space-y-1.5">
          <Label htmlFor="faculty-name" className="text-xs font-medium text-gray-600">
            Nama Fakultas
          </Label>
          <Input
            id="faculty-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="cth. Fakultas Ilmu Komputer"
            disabled={isSubmitting}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="faculty-code" className="text-xs font-medium text-gray-600">
            Kode Fakultas
          </Label>
          <Input
            id="faculty-code"
            value={code}
            onChange={(event) => setCode(event.target.value.toUpperCase())}
            placeholder="cth. FIK"
            disabled={isSubmitting}
          />
        </div>

        {localError || errorMessage ? (
          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
            {localError || errorMessage}
          </div>
        ) : null}

        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
            Batal
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Menyimpan..." : isEditMode ? "Simpan Perubahan" : "Tambah Fakultas"}
          </Button>
        </div>
      </form>
    </AdminModalShell>
  )
}

function FacultyDetailView({
  faculty,
  onBack,
}: {
  faculty: Faculty
  onBack: () => void
}) {
  const [reviewers, setReviewers] = useState<Reviewer[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingReviewer, setEditingReviewer] = useState<Reviewer | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [faculties, setFaculties] = useState<Faculty[]>([])

  const loadReviewers = useCallback(async () => {
    setIsLoading(true)
    setLoadError(null)

    try {
      const response = await fetch(`/api/faculties/${faculty.id}/reviewers`, {
        method: "GET",
        cache: "no-store",
      })
      const payload = await readApiResponse(response)

      if (!response.ok) {
        setLoadError((payload as { error?: string }).error ?? "Gagal memuat data reviewer.")
        setReviewers([])
        return
      }

      setReviewers(Array.isArray((payload as { data?: Reviewer[] }).data) ? ((payload as { data: Reviewer[] }).data) : [])
    } catch {
      setLoadError("Tidak bisa terhubung ke server.")
      setReviewers([])
    } finally {
      setIsLoading(false)
    }
  }, [faculty.id])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadReviewers()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [loadReviewers])

  async function handleDeleteReviewer(id: string) {
    if (!window.confirm("Apakah Anda yakin ingin menghapus reviewer ini?")) return

    try {
      const response = await fetch(`/api/reviewers/${id}`, {
        method: "DELETE",
      })
      const payload = await readApiResponse(response)

      if (!response.ok) {
        alert((payload as { error?: string }).error ?? "Gagal menghapus reviewer.")
        return
      }

      await loadReviewers()
      alert((payload as { message?: string }).message ?? "Reviewer berhasil dihapus.")
    } catch {
      alert("Tidak bisa terhubung ke server.")
    }
  }

  function handleEditReviewer(reviewer: Reviewer) {
    setEditingReviewer(reviewer)
    setFormError(null)
    setIsModalOpen(true)
  }

  function handleCloseModal() {
    setIsModalOpen(false)
    setEditingReviewer(null)
    setFormError(null)
  }

  async function handleSaveReviewer(data: { nama: string; email: string; isActive: boolean; fakultasId: string }) {
    setIsSubmitting(true)
    setFormError(null)

    try {
      const isEditMode = Boolean(editingReviewer)
      const response = await fetch(
        isEditMode ? `/api/reviewers/${editingReviewer!.id}` : "/api/reviewers",
        {
          method: isEditMode ? "PUT" : "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(data),
        }
      )
      const payload = await readApiResponse(response)

      if (!response.ok) {
        setFormError((payload as { error?: string }).error ?? "Gagal menyimpan reviewer.")
        return
      }

      await loadReviewers()
      handleCloseModal()
    } catch {
      setFormError("Tidak bisa terhubung ke server.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <Button
          type="button"
          variant="ghost"
          onClick={onBack}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-800 px-0 hover:bg-transparent"
        >
          <ArrowLeftIcon className="size-4" />
          Kembali
        </Button>
      </div>

      <AdminSurfaceCard className="mb-6">
        <div className="flex items-center gap-4 px-6 py-5">
          <div className="flex size-14 items-center justify-center rounded-full bg-pkm-100">
            <GraduationIcon className="size-6 text-pkm-700" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-800">{faculty.name}</h2>
            <div className="mt-1 flex items-center gap-3">
              <span className="inline-flex rounded-full border border-pkm-200 bg-pkm-50 px-3 py-1 text-xs font-medium text-pkm-700">
                {faculty.code}
              </span>
              <span className="text-sm text-gray-500">{faculty.reviewerCount} reviewer terhubung</span>
            </div>
          </div>
        </div>
      </AdminSurfaceCard>

      <AdminSurfaceCard>
        <div className="border-b border-gray-100 px-5 py-4">
          <h2 className="text-sm font-semibold text-gray-700">Daftar Reviewer</h2>
          <p className="mt-0.5 text-xs text-[rgba(0,0,0,0.4)]">
            Reviewer yang terhubung dengan fakultas ini
          </p>
        </div>

        <div className="overflow-x-auto px-5 py-4">
          {isLoading ? (
            <div className="py-8 text-center text-sm text-gray-500">Memuat reviewer...</div>
          ) : loadError ? (
            <div className="py-8 text-center">
              <p className="mb-3 text-sm text-red-600">{loadError}</p>
              <Button type="button" variant="outline" size="sm" onClick={() => void loadReviewers()}>
                Coba Lagi
              </Button>
            </div>
          ) : reviewers.length === 0 ? (
            <div className="py-8 text-center text-sm text-gray-500">
              Belum ada reviewer pada fakultas ini.
            </div>
          ) : (
            <table className="w-full min-w-[760px] border-separate border-spacing-0">
              <thead>
                <tr className="text-left">
                  <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                    Reviewer
                  </th>
                  <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                    Email
                  </th>
                  <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                    Status
                  </th>
                  <th className="border-b border-gray-100 pb-3 text-right text-xs font-semibold text-gray-700">
                    Aksi
                  </th>
                </tr>
              </thead>
              <tbody>
                {reviewers.map((reviewer) => (
                  <tr key={reviewer.id}>
                    <td className="border-b border-gray-50 py-4 pr-4">
                      <div className="flex items-center gap-4">
                        <div className="flex size-12 items-center justify-center rounded-full bg-pkm-100 text-sm font-semibold text-pkm-700">
                          {getReviewerInitials(reviewer.nama)}
                        </div>
                        <span className="text-sm font-medium text-gray-800">{reviewer.nama}</span>
                      </div>
                    </td>
                    <td className="border-b border-gray-50 py-4 pr-4">
                      <span className="text-sm text-gray-600">{reviewer.email}</span>
                    </td>
                    <td className="border-b border-gray-50 py-4 pr-4">
                      <span
                        className={[
                          "inline-flex rounded-full px-3 py-1 text-xs font-medium",
                          reviewer.isActive
                            ? "bg-pkm-100 text-pkm-700"
                            : "bg-gray-100 text-gray-500",
                        ].join(" ")}
                      >
                        {mapStatusLabel(reviewer.isActive)}
                      </span>
                    </td>
                    <td className="border-b border-gray-50 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => handleEditReviewer(reviewer)}
                          className="border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-gray-800"
                        >
                          <EditIcon />
                          Edit
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          onClick={() => void handleDeleteReviewer(reviewer.id)}
                          className="border-0 bg-red-600 text-white hover:bg-red-700"
                        >
                          <TrashIcon />
                          Hapus
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </AdminSurfaceCard>

      {isModalOpen && (
        <ReviewerEditModal
          reviewer={editingReviewer}
          faculties={faculties}
          currentFacultyId={faculty.id}
          isSubmitting={isSubmitting}
          errorMessage={formError}
          onClose={handleCloseModal}
          onSave={handleSaveReviewer}
        />
      )}
    </div>
  )
}

type ReviewerFormData = {
  nama: string
  email: string
  isActive: boolean
  fakultasId: string
}

function ReviewerEditModal({
  reviewer,
  faculties,
  currentFacultyId,
  isSubmitting,
  errorMessage,
  onClose,
  onSave,
}: {
  reviewer: Reviewer | null
  faculties: Faculty[]
  currentFacultyId: string
  isSubmitting: boolean
  errorMessage: string | null
  onClose: () => void
  onSave: (data: ReviewerFormData) => Promise<void>
}) {
  const [nama, setNama] = useState(reviewer?.nama ?? "")
  const [email, setEmail] = useState(reviewer?.email ?? "")
  const [status, setStatus] = useState(mapStatusLabel(reviewer?.isActive ?? true))
  const [localError, setLocalError] = useState<string | null>(null)
  const isEditMode = Boolean(reviewer)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!nama.trim() || !email.trim()) {
      setLocalError("Nama dan email wajib diisi.")
      return
    }

    setLocalError(null)
    await onSave({
      nama: nama.trim(),
      email: email.trim(),
      isActive: status === "Aktif",
      fakultasId: currentFacultyId,
    })
  }

  return (
    <AdminModalShell
      title={isEditMode ? "Edit Reviewer" : "Tambah Reviewer"}
      description="Perbarui data reviewer dan statusnya."
      onClose={onClose}
      maxWidthClassName="max-w-lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4 px-6 py-5">
        <div className="space-y-1.5">
          <Label htmlFor="nama-reviewer" className="text-xs font-medium text-gray-600">
            Nama Reviewer
          </Label>
          <Input
            id="nama-reviewer"
            value={nama}
            onChange={(event) => setNama(event.target.value)}
            placeholder="cth. Dr. Ahmad Wijaya"
            disabled={isSubmitting}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="email-reviewer" className="text-xs font-medium text-gray-600">
            Email
          </Label>
          <Input
            id="email-reviewer"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="cth. ahmad.w@university.ac.id"
            disabled={isSubmitting}
          />
        </div>

        <div className="space-y-1.5">
          <Label className="text-xs font-medium text-gray-600">Status</Label>
          <Select value={status} onValueChange={(value) => setStatus(value)} disabled={isSubmitting}>
            <SelectTrigger>
              <SelectValue placeholder="Pilih status reviewer" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Aktif">Aktif</SelectItem>
              <SelectItem value="Tidak Aktif">Tidak Aktif</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {localError || errorMessage ? (
          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
            {localError || errorMessage}
          </div>
        ) : null}

        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
            Batal
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Menyimpan..." : "Simpan Perubahan"}
          </Button>
        </div>
      </form>
    </AdminModalShell>
  )
}

export default function FacultyManagementPage() {
  const [faculties, setFaculties] = useState<Faculty[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingFaculty, setEditingFaculty] = useState<Faculty | null>(null)
  const [viewingFaculty, setViewingFaculty] = useState<Faculty | null>(null)
  const [searchQuery, setSearchQuery] = useState("")

  const totalReviewers = useMemo(
    () => faculties.reduce((total, faculty) => total + faculty.reviewerCount, 0),
    [faculties]
  )

  const filteredFaculties = useMemo(() => {
    if (!searchQuery.trim()) return faculties
    const query = searchQuery.toLowerCase()
    return faculties.filter(
      (faculty) =>
        faculty.name.toLowerCase().includes(query) ||
        faculty.code.toLowerCase().includes(query)
    )
  }, [faculties, searchQuery])

  const loadFaculties = useCallback(async () => {
    setIsLoading(true)
    setLoadError(null)

    try {
      const response = await fetch("/api/faculties", {
        method: "GET",
        cache: "no-store",
      })
      const payload = await readApiResponse(response)

      if (!response.ok) {
        setLoadError((payload as { error?: string }).error ?? "Gagal memuat data fakultas.")
        setFaculties([])
        return
      }

      setFaculties(Array.isArray((payload as { data?: Faculty[] }).data) ? ((payload as { data: Faculty[] }).data) : [])
    } catch {
      setLoadError("Tidak bisa terhubung ke server.")
      setFaculties([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadFaculties()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [loadFaculties])

  function handleOpenModal(faculty: Faculty | null = null) {
    setEditingFaculty(faculty)
    setFormError(null)
    setIsModalOpen(true)
  }

  function handleCloseModal() {
    setFormError(null)
    setIsModalOpen(false)
    setEditingFaculty(null)
  }

  async function handleSaveFaculty(data: FacultyFormData) {
    setIsSubmitting(true)
    setFormError(null)

    try {
      const isEditMode = Boolean(editingFaculty)
      const response = await fetch(
        isEditMode ? `/api/faculties/${editingFaculty!.id}` : "/api/faculties",
        {
          method: isEditMode ? "PUT" : "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(data),
        }
      )
      const payload = await readApiResponse(response)

      if (!response.ok) {
        setFormError((payload as { error?: string }).error ?? "Gagal menyimpan fakultas.")
        return
      }

      await loadFaculties()
      handleCloseModal()
    } catch {
      setFormError("Tidak bisa terhubung ke server.")
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleDeleteFaculty(faculty: Faculty) {
    if (!window.confirm(`Apakah Anda yakin ingin menghapus ${faculty.name}?`)) {
      return
    }

    try {
      const response = await fetch(`/api/faculties/${faculty.id}`, {
        method: "DELETE",
      })
      const payload = await readApiResponse(response)

      if (!response.ok) {
        alert((payload as { error?: string }).error ?? "Gagal menghapus fakultas.")
        return
      }

      await loadFaculties()
      alert((payload as { message?: string }).message ?? "Fakultas berhasil dihapus.")
    } catch {
      alert("Tidak bisa terhubung ke server.")
    }
  }

  function handleViewDetail(faculty: Faculty) {
    setViewingFaculty(faculty)
  }

  function handleBackFromDetail() {
    setViewingFaculty(null)
    void loadFaculties()
  }

  if (viewingFaculty) {
    return (
      <div className="px-8 py-8">
        <FacultyDetailView faculty={viewingFaculty} onBack={handleBackFromDetail} />
      </div>
    )
  }

  return (
    <>
      {isModalOpen ? (
        <FacultyModal
          faculty={editingFaculty}
          isSubmitting={isSubmitting}
          errorMessage={formError}
          onClose={handleCloseModal}
          onSave={handleSaveFaculty}
        />
      ) : null}

      <div className="px-8 py-8">
        <AdminPageHeader
          title="Kelola Fakultas"
          description="Kelola daftar fakultas yang digunakan pada data reviewer"
          action={
            <Button onClick={() => handleOpenModal(null)} className="flex items-center gap-2">
              <PlusIcon />
              Tambah Fakultas
            </Button>
          }
        />

        {loadError ? (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <div className="flex items-center justify-between gap-3">
              <span>{loadError}</span>
              <Button type="button" variant="outline" size="sm" onClick={() => void loadFaculties()}>
                Coba Lagi
              </Button>
            </div>
          </div>
        ) : null}

        <div className="grid gap-4 md:grid-cols-2">
          <AdminMetricCard
            title="Total Fakultas"
            value={String(faculties.length)}
            accentClassName="bg-pkm-100 text-pkm-700"
            icon={<GraduationIcon />}
          />
          <AdminMetricCard
            title="Total Reviewer Terhubung"
            value={String(totalReviewers)}
            accentClassName="bg-pkm-100 text-pkm-700"
            icon={<UserIcon />}
          />
        </div>

        <AdminSurfaceCard className="mt-4">
          <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
            <div>
              <h2 className="text-sm font-semibold text-gray-700">Daftar Fakultas</h2>
              <p className="mt-0.5 text-xs text-[rgba(0,0,0,0.4)]">
                Tambah, edit, atau hapus fakultas yang tersedia untuk reviewer
              </p>
            </div>
            <SearchInput
              value={searchQuery}
              onChange={setSearchQuery}
              placeholder="Cari fakultas..."
              className="w-64"
            />
          </div>

          <div className="overflow-x-auto px-5 py-4">
            {isLoading ? (
              <div className="py-8 text-center text-sm text-gray-500">Memuat fakultas...</div>
            ) : filteredFaculties.length === 0 ? (
              searchQuery.trim() ? (
                <div className="py-8 text-center text-sm text-gray-500">
                  Tidak ada fakultas yang cocok dengan "{searchQuery}"
                </div>
              ) : (
                <div className="py-8 text-center text-sm text-gray-500">Belum ada fakultas.</div>
              )
            ) : (
              <table className="w-full min-w-[760px] border-separate border-spacing-0">
                <thead>
                  <tr className="text-left">
                    <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                      No
                    </th>
                    <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                      Nama Fakultas
                    </th>
                    <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                      Kode Fakultas
                    </th>
                    <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                      Jumlah Reviewer
                    </th>
                    <th className="border-b border-gray-100 pb-3 text-right text-xs font-semibold text-gray-700">
                      Aksi
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredFaculties.map((faculty, index) => (
                    <tr key={faculty.id}>
                      <td className="border-b border-gray-50 py-4 pr-4 text-sm text-gray-500">
                        {index + 1}
                      </td>
                      <td className="border-b border-gray-50 py-4 pr-4">
                        <span className="text-sm font-medium text-gray-800">{faculty.name}</span>
                      </td>
                      <td className="border-b border-gray-50 py-4 pr-4">
                        <span className="inline-flex rounded-full border border-pkm-200 bg-pkm-50 px-3 py-1 text-xs font-medium text-pkm-700">
                          {faculty.code}
                        </span>
                      </td>
                      <td className="border-b border-gray-50 py-4 pr-4">
                        <span className="text-sm text-gray-600">{faculty.reviewerCount} reviewer</span>
                      </td>
                      <td className="border-b border-gray-50 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => handleViewDetail(faculty)}
                            className="border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-gray-800"
                          >
                            <DetailIcon />
                            Detail
                          </Button>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => handleOpenModal(faculty)}
                            className="border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-gray-800"
                          >
                            <EditIcon />
                            Edit
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            onClick={() => void handleDeleteFaculty(faculty)}
                            className="border-0 bg-red-600 text-white hover:bg-red-700"
                          >
                            <TrashIcon />
                            Hapus
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </AdminSurfaceCard>
      </div>
    </>
  )
}