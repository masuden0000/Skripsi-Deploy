"use client"

import { useMemo, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

type ReviewerStatus = "Aktif" | "Tidak Aktif"

type Reviewer = {
  id: string
  nama: string
  inisial: string
  email: string
  bidangKeahlian: string
  totalReview: number
  status: ReviewerStatus
}

type ReviewerFormData = Omit<Reviewer, "id" | "inisial">

const REVIEWER_SEED: Reviewer[] = [
  {
    id: "rv-1",
    nama: "Dr. Ahmad Wijaya",
    inisial: "DA",
    email: "ahmad.w@university.ac.id",
    bidangKeahlian: "AI & Machine Learning",
    totalReview: 15,
    status: "Aktif",
  },
  {
    id: "rv-2",
    nama: "Prof. Siti Nurhaliza",
    inisial: "PS",
    email: "siti.n@university.ac.id",
    bidangKeahlian: "Software Engineering",
    totalReview: 22,
    status: "Aktif",
  },
  {
    id: "rv-3",
    nama: "Dr. Budi Santoso",
    inisial: "DB",
    email: "budi.s@university.ac.id",
    bidangKeahlian: "Data Science",
    totalReview: 18,
    status: "Aktif",
  },
  {
    id: "rv-4",
    nama: "Dr. Dewi Lestari",
    inisial: "DD",
    email: "dewi.l@university.ac.id",
    bidangKeahlian: "IoT & Embedded Systems",
    totalReview: 12,
    status: "Aktif",
  },
  {
    id: "rv-5",
    nama: "Prof. Eko Prasetyo",
    inisial: "PE",
    email: "eko.p@university.ac.id",
    bidangKeahlian: "Cybersecurity",
    totalReview: 20,
    status: "Tidak Aktif",
  },
]

function getReviewerInitials(nama: string) {
  return nama
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((bagian) => bagian[0]?.toUpperCase() ?? "")
    .join("")
}

function formatAverage(total: number, count: number) {
  if (!count) {
    return "0.0"
  }

  return (total / count).toFixed(1)
}

function PlusIcon() {
  return (
    <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v14M5 12h14" />
    </svg>
  )
}

function UserIcon() {
  return (
    <svg className="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M20 21a8 8 0 0 0-16 0" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  )
}

function GraduationIcon() {
  return (
    <svg className="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="m3 8 9-5 9 5-9 5-9-5Z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M7 10.5v4.25C7 16.55 9.24 18 12 18s5-1.45 5-3.25V10.5" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 9v5" />
    </svg>
  )
}

function ReviewIcon() {
  return (
    <svg className="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 5h18" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M7 5V3" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M17 5V3" />
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path strokeLinecap="round" strokeLinejoin="round" d="m9 13 2 2 4-4" />
    </svg>
  )
}

function StarIcon() {
  return (
    <svg className="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="m12 3 2.8 5.67 6.2.9-4.5 4.38 1.06 6.18L12 17.27l-5.56 2.86 1.06-6.18L3 9.57l6.2-.9L12 3Z" />
    </svg>
  )
}

function EmailIcon() {
  return (
    <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path strokeLinecap="round" strokeLinejoin="round" d="m3 7 9 6 9-6" />
    </svg>
  )
}

function EditIcon() {
  return (
    <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 20h9" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19l-4 1 1-4 12.5-12.5Z" />
    </svg>
  )
}

function TrashIcon() {
  return (
    <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 6h18" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 6v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V6" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M10 11v6M14 11v6" />
    </svg>
  )
}

function StatCard({
  title,
  value,
  accentClass,
  icon,
}: {
  title: string
  value: string
  accentClass: string
  icon: React.ReactNode
}) {
  return (
    <div className="rounded-3xl border border-emerald-100/70 bg-white px-6 py-5 shadow-[0_12px_32px_rgba(15,118,110,0.12)]">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-[15px] font-medium text-slate-500">{title}</p>
          <p className="mt-1 text-[34px] font-semibold tracking-tight text-emerald-900">{value}</p>
        </div>
        <div className={`flex size-15 items-center justify-center rounded-2xl ${accentClass}`}>
          {icon}
        </div>
      </div>
    </div>
  )
}

function ReviewerModal({
  reviewer,
  onClose,
  onSave,
}: {
  reviewer: Reviewer | null
  onClose: () => void
  onSave: (data: ReviewerFormData) => void
}) {
  const [nama, setNama] = useState(reviewer?.nama ?? "")
  const [email, setEmail] = useState(reviewer?.email ?? "")
  const [bidangKeahlian, setBidangKeahlian] = useState(reviewer?.bidangKeahlian ?? "")
  const [totalReview, setTotalReview] = useState(String(reviewer?.totalReview ?? 0))
  const [status, setStatus] = useState<ReviewerStatus>(reviewer?.status ?? "Aktif")
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const isEditMode = Boolean(reviewer)

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const totalReviewNumber = Number(totalReview)
    if (!nama.trim() || !email.trim() || !bidangKeahlian.trim()) {
      setErrorMessage("Semua field wajib diisi.")
      return
    }

    if (!Number.isFinite(totalReviewNumber) || totalReviewNumber < 0) {
      setErrorMessage("Total review harus berupa angka nol atau lebih.")
      return
    }

    setErrorMessage(null)
    onSave({
      nama: nama.trim(),
      email: email.trim(),
      bidangKeahlian: bidangKeahlian.trim(),
      totalReview: totalReviewNumber,
      status,
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Tutup modal"
        className="absolute inset-0 bg-slate-950/25 backdrop-blur-[2px]"
        onClick={onClose}
      />

      <div className="relative z-10 w-full max-w-lg rounded-[28px] border border-emerald-100 bg-white shadow-[0_24px_70px_rgba(15,118,110,0.2)]">
        <div className="border-b border-emerald-100 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-emerald-950">
                {isEditMode ? "Edit Reviewer" : "Tambah Reviewer"}
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                {isEditMode
                  ? "Perbarui data reviewer dan bidang keahliannya."
                  : "Tambahkan reviewer baru untuk kebutuhan distribusi review."}
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="flex size-9 items-center justify-center rounded-xl text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
            >
              <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 px-6 py-5">
          <div className="space-y-1.5">
            <Label htmlFor="nama-reviewer" className="text-xs font-medium text-slate-600">
              Nama Reviewer
            </Label>
            <Input
              id="nama-reviewer"
              value={nama}
              onChange={(event) => setNama(event.target.value)}
              placeholder="cth. Dr. Ahmad Wijaya"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="email-reviewer" className="text-xs font-medium text-slate-600">
              Email
            </Label>
            <Input
              id="email-reviewer"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="cth. ahmad.w@university.ac.id"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="bidang-reviewer" className="text-xs font-medium text-slate-600">
              Bidang Keahlian
            </Label>
            <Input
              id="bidang-reviewer"
              value={bidangKeahlian}
              onChange={(event) => setBidangKeahlian(event.target.value)}
              placeholder="cth. AI & Machine Learning"
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="total-review" className="text-xs font-medium text-slate-600">
                Total Review
              </Label>
              <Input
                id="total-review"
                type="number"
                min="0"
                value={totalReview}
                onChange={(event) => setTotalReview(event.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="status-reviewer" className="text-xs font-medium text-slate-600">
                Status
              </Label>
              <select
                id="status-reviewer"
                value={status}
                onChange={(event) => setStatus(event.target.value as ReviewerStatus)}
                className="flex h-8 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none transition focus:border-emerald-400 focus:ring-3 focus:ring-emerald-100"
              >
                <option value="Aktif">Aktif</option>
                <option value="Tidak Aktif">Tidak Aktif</option>
              </select>
            </div>
          </div>

          {errorMessage ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
              {errorMessage}
            </div>
          ) : null}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Batal
            </Button>
            <Button type="submit">
              {isEditMode ? "Simpan Perubahan" : "Tambah Reviewer"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function ReviewerManagementPage() {
  const [reviewers, setReviewers] = useState<Reviewer[]>(REVIEWER_SEED)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingReviewer, setEditingReviewer] = useState<Reviewer | null>(null)

  const totalReview = useMemo(
    () => reviewers.reduce((sum, reviewer) => sum + reviewer.totalReview, 0),
    [reviewers]
  )
  const totalAktif = useMemo(
    () => reviewers.filter((reviewer) => reviewer.status === "Aktif").length,
    [reviewers]
  )
  const averageReview = useMemo(
    () => formatAverage(totalReview, reviewers.length),
    [reviewers.length, totalReview]
  )

  function handleOpenCreateModal() {
    setEditingReviewer(null)
    setIsModalOpen(true)
  }

  function handleCloseModal() {
    setIsModalOpen(false)
    setEditingReviewer(null)
  }

  function handleEditReviewer(reviewer: Reviewer) {
    setEditingReviewer(reviewer)
    setIsModalOpen(true)
  }

  function handleDeleteReviewer(id: string) {
    setReviewers((current) => current.filter((reviewer) => reviewer.id !== id))
  }

  function handleSaveReviewer(data: ReviewerFormData) {
    if (editingReviewer) {
      setReviewers((current) =>
        current.map((reviewer) =>
          reviewer.id === editingReviewer.id
            ? {
                ...reviewer,
                ...data,
                inisial: getReviewerInitials(data.nama),
              }
            : reviewer
        )
      )
      handleCloseModal()
      return
    }

    const nextReviewer: Reviewer = {
      id: `rv-${Date.now()}`,
      ...data,
      inisial: getReviewerInitials(data.nama),
    }

    setReviewers((current) => [nextReviewer, ...current])
    handleCloseModal()
  }

  return (
    <>
      {isModalOpen ? (
        <ReviewerModal
          reviewer={editingReviewer}
          onClose={handleCloseModal}
          onSave={handleSaveReviewer}
        />
      ) : null}

      <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.08),_transparent_28%),linear-gradient(180deg,rgba(240,253,250,0.85)_0%,rgba(255,255,255,1)_42%)] px-8 py-8">
        <div className="mx-auto max-w-[1500px]">
          <div className="mb-8 flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
            <div>
              <h1 className="text-[42px] font-semibold tracking-[-0.03em] text-emerald-950">
                Manajemen Reviewer
              </h1>
              <p className="mt-2 text-xl text-slate-500">
                Kelola akun reviewer dan informasi terkait
              </p>
            </div>

            <Button
              onClick={handleOpenCreateModal}
              className="h-12 rounded-2xl px-6 text-base shadow-[0_10px_28px_rgba(16,185,129,0.28)]"
            >
              <PlusIcon />
              Tambah Reviewer
            </Button>
          </div>

          <div className="grid gap-5 xl:grid-cols-4">
            <StatCard
              title="Total Reviewer"
              value={String(reviewers.length)}
              accentClass="bg-emerald-50 text-emerald-600"
              icon={<UserIcon />}
            />
            <StatCard
              title="Aktif"
              value={String(totalAktif)}
              accentClass="bg-emerald-50 text-emerald-500"
              icon={<GraduationIcon />}
            />
            <StatCard
              title="Total Review"
              value={String(totalReview)}
              accentClass="bg-blue-50 text-blue-600"
              icon={<ReviewIcon />}
            />
            <StatCard
              title="Rata-rata Review"
              value={averageReview}
              accentClass="bg-violet-50 text-violet-600"
              icon={<StarIcon />}
            />
          </div>

          <section className="mt-8 overflow-hidden rounded-[30px] border border-emerald-100/80 bg-white shadow-[0_18px_54px_rgba(15,118,110,0.12)]">
            <div className="border-b border-emerald-100/80 bg-emerald-50/45 px-8 py-7">
              <h2 className="text-[34px] font-semibold tracking-[-0.03em] text-emerald-950">
                Daftar Reviewer
              </h2>
              <p className="mt-2 text-xl text-slate-500">
                Kelola dan pantau reviewer yang terdaftar
              </p>
            </div>

            <div className="overflow-x-auto px-8 py-7">
              <table className="min-w-[980px] w-full border-separate border-spacing-0">
                <thead>
                  <tr className="text-left">
                    <th className="border-b border-slate-200 pb-4 pr-4 text-[15px] font-semibold text-slate-900">Reviewer</th>
                    <th className="border-b border-slate-200 pb-4 pr-4 text-[15px] font-semibold text-slate-900">Email</th>
                    <th className="border-b border-slate-200 pb-4 pr-4 text-[15px] font-semibold text-slate-900">Bidang Keahlian</th>
                    <th className="border-b border-slate-200 pb-4 pr-4 text-[15px] font-semibold text-slate-900">Total Review</th>
                    <th className="border-b border-slate-200 pb-4 pr-4 text-[15px] font-semibold text-slate-900">Status</th>
                    <th className="border-b border-slate-200 pb-4 text-right text-[15px] font-semibold text-slate-900">Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  {reviewers.map((reviewer) => (
                    <tr key={reviewer.id}>
                      <td className="border-b border-slate-100 py-4 pr-4">
                        <div className="flex items-center gap-4">
                          <div className="flex size-14 items-center justify-center rounded-full bg-emerald-100 text-lg font-semibold text-emerald-700">
                            {reviewer.inisial}
                          </div>
                          <span className="text-[17px] font-medium text-slate-900">{reviewer.nama}</span>
                        </div>
                      </td>
                      <td className="border-b border-slate-100 py-4 pr-4">
                        <div className="flex items-center gap-3 text-[15px] text-slate-500">
                          <EmailIcon />
                          <span>{reviewer.email}</span>
                        </div>
                      </td>
                      <td className="border-b border-slate-100 py-4 pr-4">
                        <span className="inline-flex rounded-full border border-emerald-200 bg-emerald-50/60 px-3 py-1 text-[15px] font-medium text-emerald-700">
                          {reviewer.bidangKeahlian}
                        </span>
                      </td>
                      <td className="border-b border-slate-100 py-4 pr-4 text-[17px] text-slate-700">
                        {reviewer.totalReview} proposal
                      </td>
                      <td className="border-b border-slate-100 py-4 pr-4">
                        <span
                          className={[
                            "inline-flex rounded-full px-3 py-1 text-[15px] font-semibold",
                            reviewer.status === "Aktif"
                              ? "bg-emerald-600 text-white"
                              : "bg-slate-200 text-slate-700",
                          ].join(" ")}
                        >
                          {reviewer.status}
                        </span>
                      </td>
                      <td className="border-b border-slate-100 py-4 text-right">
                        <div className="flex items-center justify-end gap-3">
                          <button
                            type="button"
                            onClick={() => handleEditReviewer(reviewer)}
                            className="flex size-12 items-center justify-center rounded-2xl border border-emerald-200 text-emerald-600 transition-colors hover:bg-emerald-50"
                          >
                            <EditIcon />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteReviewer(reviewer.id)}
                            className="flex size-12 items-center justify-center rounded-2xl border border-rose-200 text-rose-500 transition-colors hover:bg-rose-50"
                          >
                            <TrashIcon />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </div>
    </>
  )
}
