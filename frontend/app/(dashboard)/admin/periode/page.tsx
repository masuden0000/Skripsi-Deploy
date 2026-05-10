"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import {
  AdminModalShell,
  AdminPageHeader,
  AdminSurfaceCard,
} from "@/components/admin/shared"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  CalendarIcon,
  ChevronIcon,
  DetailIcon,
  EditIcon,
  PlusIcon,
  TrashIcon,
} from "@/components/icons/public-icons"
import {
  formatTanggal,
  formatTanggalDanWaktu,
  hasReviewPeriodBeenUpdated,
  isOngoingReviewPeriod,
} from "@/lib/review-periods"
import {
  getReviewPeriods,
  createReviewPeriod,
  updateReviewPeriod,
  deleteReviewPeriod,
} from "@/lib/api"
import type { ReviewPeriod, ReviewPeriodFormData } from "@/lib/schemas"

function PeriodeItem({
  periode,
  isExpanded,
  onToggle,
  onEdit,
  onDelete,
  onViewDetail,
}: {
  periode: ReviewPeriod
  isExpanded: boolean
  onToggle: () => void
  onEdit: () => void
  onDelete: () => void
  onViewDetail: () => void
}) {
  const isOngoingItem = isOngoingReviewPeriod(periode)
  const shouldShowUpdatedAt = hasReviewPeriodBeenUpdated(periode)

  return (
    <div>
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center gap-4 px-5 py-4 text-left transition-colors hover:bg-pkm-50/50"
      >
        <span
          className={`size-2 rounded-full flex-none mt-0.5 ${
            isOngoingItem ? "bg-pkm-600 shadow-[0_0_6px_rgba(0,153,102,0.5)]" : "bg-gray-300"
          }`}
        />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-800 truncate">{periode.nama}</p>
          <p className="text-xs mt-0.5" style={{ color: "rgba(0,0,0,0.4)" }}>
            {formatTanggal(periode.tanggalMulai)} - {formatTanggal(periode.tanggalSelesai)}
          </p>
        </div>
        <ChevronIcon open={isExpanded} />
      </button>

      {isExpanded && (
        <div className="px-5 pb-5 bg-pkm-50/20 border-t border-gray-50">
          <div className="pt-4 flex items-start justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <CalendarIcon />
                <span>
                  Mulai: <span className="font-medium text-gray-700">{formatTanggal(periode.tanggalMulai)}</span>
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <CalendarIcon />
                <span>
                  Selesai: <span className="font-medium text-gray-700">{formatTanggal(periode.tanggalSelesai)}</span>
                </span>
              </div>
              {shouldShowUpdatedAt ? (
                <p className="text-xs text-gray-500">
                  Terakhir diperbarui:{" "}
                  <span className="font-medium text-gray-700">
                    {formatTanggalDanWaktu(periode.updatedAt)}
                  </span>
                </p>
              ) : null}
              <div className="pt-0.5">
                {isOngoingItem ? (
                  <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full bg-pkm-100 text-pkm-700">
                    <span className="size-1.5 rounded-full bg-pkm-600" />
                    Berlangsung
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full bg-gray-100 text-gray-500">
                    <span className="size-1.5 rounded-full bg-gray-400" />
                    Selesai
                  </span>
                )}
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-2">
              {isOngoingItem && (
                <Button
                  type="button"
                  size="sm"
                  onClick={onDelete}
                  className="bg-red-600 text-white hover:bg-red-700 border-0"
                >
                  <TrashIcon />
                  Hapus
                </Button>
              )}
              {isOngoingItem && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={onEdit}
                  className="border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-gray-800"
                >
                  <EditIcon />
                  Edit
                </Button>
              )}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onViewDetail}
                className="text-pkm-700 border-pkm-200 hover:bg-pkm-50"
              >
                <DetailIcon />
                Lihat Detail
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function PeriodeSection({
  title,
  periodes,
  count,
  defaultOpen,
  badgeClass,
  expandedId,
  onToggleItem,
  onEditItem,
  onDeleteItem,
  onViewDetail,
}: {
  title: string
  periodes: ReviewPeriod[]
  count: number
  defaultOpen: boolean
  badgeClass: string
  expandedId: string | null
  onToggleItem: (id: string) => void
  onEditItem: (periode: ReviewPeriod) => void
  onDeleteItem: (id: string) => void
  onViewDetail: (id: string) => void
}) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <AdminSurfaceCard>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50/60 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <span className="text-sm font-semibold text-gray-700">{title}</span>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${badgeClass}`}>{count}</span>
        </div>
        <ChevronIcon open={open} />
      </button>

      {open && (
        <div className="divide-y divide-gray-50 border-t border-gray-50">
          {periodes.length === 0 ? (
            <div className="px-5 py-8 text-center text-sm" style={{ color: "rgba(0,0,0,0.35)" }}>
              Belum ada periode
            </div>
          ) : (
            periodes.map((periode) => (
              <PeriodeItem
                key={periode.id}
                periode={periode}
                isExpanded={expandedId === periode.id}
                onToggle={() => onToggleItem(periode.id)}
                onEdit={() => onEditItem(periode)}
                onDelete={() => onDeleteItem(periode.id)}
                onViewDetail={() => onViewDetail(periode.id)}
              />
            ))
          )}
        </div>
      )}
    </AdminSurfaceCard>
  )
}

function TambahPeriodeModal({
  periode,
  isSubmitting,
  errorMessage,
  onClose,
  onSave,
}: {
  periode?: ReviewPeriod | null
  isSubmitting: boolean
  errorMessage: string | null
  onClose: () => void
  onSave: (data: ReviewPeriodFormData) => Promise<void>
}) {
  const [nama, setNama] = useState(periode?.nama ?? "")
  const [tanggalMulai, setTanggalMulai] = useState(periode?.tanggalMulai ?? "")
  const [tanggalSelesai, setTanggalSelesai] = useState(periode?.tanggalSelesai ?? "")
  const [localError, setLocalError] = useState<string | null>(null)
  const isEditMode = Boolean(periode)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!nama.trim() || !tanggalMulai || !tanggalSelesai) {
      setLocalError("Semua field wajib diisi.")
      return
    }

    if (tanggalSelesai < tanggalMulai) {
      setLocalError("Tanggal selesai tidak boleh sebelum tanggal mulai.")
      return
    }

    setLocalError(null)
    await onSave({
      nama: nama.trim(),
      tanggalMulai,
      tanggalSelesai,
    })
  }

  return (
    <AdminModalShell
      title={isEditMode ? "Edit Periode Review" : "Tambah Periode Review"}
      description={
        isEditMode
          ? "Perbarui nama dan rentang tanggal periode"
          : "Tentukan nama dan rentang tanggal periode"
      }
      onClose={onClose}
    >
        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="nama" className="text-xs font-medium text-gray-600">
              Nama Periode
            </Label>
            <Input
              id="nama"
              value={nama}
              onChange={(event) => setNama(event.target.value)}
              placeholder="cth. Periode Review PKM 2026/II"
              required
              disabled={isSubmitting}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="tanggal-mulai" className="text-xs font-medium text-gray-600">
                Tanggal Mulai
              </Label>
              <Input
                id="tanggal-mulai"
                type="date"
                value={tanggalMulai}
                onChange={(event) => setTanggalMulai(event.target.value)}
                required
                disabled={isSubmitting}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="tanggal-selesai" className="text-xs font-medium text-gray-600">
                Tanggal Selesai
              </Label>
              <Input
                id="tanggal-selesai"
                type="date"
                value={tanggalSelesai}
                min={tanggalMulai || undefined}
                onChange={(event) => setTanggalSelesai(event.target.value)}
                required
                disabled={isSubmitting}
              />
            </div>
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
              {isSubmitting
                ? "Menyimpan..."
                : isEditMode
                  ? "Simpan Perubahan"
                  : "Simpan Periode"}
            </Button>
          </div>
        </form>
    </AdminModalShell>
  )
}

export default function PeriodeReviewPage() {
  const router = useRouter()
  const [periodes, setPeriodes] = useState<ReviewPeriod[]>([])
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [editingPeriode, setEditingPeriode] = useState<ReviewPeriod | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const loadReviewPeriods = useCallback(async () => {
    setIsLoading(true)
    setLoadError(null)

    const { data, error: fetchError } = await getReviewPeriods()

    if (fetchError) {
      setLoadError(fetchError)
      setPeriodes([])
    } else {
      setPeriodes(data ?? [])
    }

    setIsLoading(false)
  }, [])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadReviewPeriods()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [loadReviewPeriods])

  const berlangsung = useMemo(
    () => periodes.filter((periode) => isOngoingReviewPeriod(periode)),
    [periodes]
  )
  const telahLewat = useMemo(
    () => periodes.filter((periode) => !isOngoingReviewPeriod(periode)),
    [periodes]
  )

  function handleToggleItem(id: string) {
    setExpandedId((current) => (current === id ? null : id))
  }

  function handleCloseModal() {
    setShowModal(false)
    setEditingPeriode(null)
    setFormError(null)
  }

  function handleOpenCreateModal() {
    setEditingPeriode(null)
    setFormError(null)
    setShowModal(true)
  }

  function handleEditPeriode(periode: ReviewPeriod) {
    setEditingPeriode(periode)
    setFormError(null)
    setShowModal(true)
  }

  async function handleSave(data: ReviewPeriodFormData) {
    setIsSubmitting(true)
    setFormError(null)

    const isEditMode = Boolean(editingPeriode)
    const apiCall = isEditMode
      ? updateReviewPeriod(editingPeriode!.id, data)
      : createReviewPeriod(data)

    const { error: saveError } = await apiCall

    if (saveError) {
      setFormError(saveError)
      setIsSubmitting(false)
      return
    }

    await loadReviewPeriods()
    handleCloseModal()
    setIsSubmitting(false)
  }

  function handleViewDetail(id: string) {
    router.push(`/admin/periode/${id}`)
  }

  async function handleDeletePeriode(id: string) {
    if (!window.confirm("Apakah Anda yakin ingin menghapus periode ini?")) return

    const { error: deleteError } = await deleteReviewPeriod(id)

    if (deleteError) {
      alert(deleteError)
      return
    }

    await loadReviewPeriods()
    alert("Periode review berhasil dihapus.")
  }

  return (
    <>
      {(showModal || editingPeriode) && (
        <TambahPeriodeModal
          periode={editingPeriode}
          isSubmitting={isSubmitting}
          errorMessage={formError}
          onClose={handleCloseModal}
          onSave={handleSave}
        />
      )}

      <div className="px-8 py-8">
        <AdminPageHeader
          title="Periode Review PKM"
          description="Kelola periode review Program Kreativitas Mahasiswa"
          action={
            <Button onClick={handleOpenCreateModal} className="flex items-center gap-2">
              <PlusIcon />
              Tambah Periode
            </Button>
          }
        />

        {loadError ? (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <div className="flex items-center justify-between gap-3">
              <span>{loadError}</span>
              <Button type="button" variant="outline" size="sm" onClick={() => void loadReviewPeriods()}>
                Coba Lagi
              </Button>
            </div>
          </div>
        ) : null}

        {isLoading ? (
          <div className="rounded-xl border border-gray-100 bg-white px-5 py-10 text-sm text-center text-gray-500 shadow-sm">
            Memuat periode review...
          </div>
        ) : (
          <div className="space-y-4">
            <PeriodeSection
              title="Berlangsung"
              periodes={berlangsung}
              count={berlangsung.length}
              defaultOpen={true}
              badgeClass="bg-pkm-100 text-pkm-700"
              expandedId={expandedId}
              onToggleItem={handleToggleItem}
              onEditItem={handleEditPeriode}
              onDeleteItem={handleDeletePeriode}
              onViewDetail={handleViewDetail}
            />
            <PeriodeSection
              title="Telah Lewat"
              periodes={telahLewat}
              count={telahLewat.length}
              defaultOpen={true}
              badgeClass="bg-gray-100 text-gray-500"
              expandedId={expandedId}
              onToggleItem={handleToggleItem}
              onEditItem={handleEditPeriode}
              onDeleteItem={handleDeletePeriode}
              onViewDetail={handleViewDetail}
            />
          </div>
        )}
      </div>
    </>
  )
}
