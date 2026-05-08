"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

// ─── Types ────────────────────────────────────────────────────────────────────

type Periode = {
  id: string
  nama: string
  tanggalMulai: string  // YYYY-MM-DD
  tanggalSelesai: string
}

// ─── Mock data ────────────────────────────────────────────────────────────────

const MOCK_PERIODE: Periode[] = [
  {
    id: "p1",
    nama: "Periode Review PKM 2026/I",
    tanggalMulai: "2026-04-01",
    tanggalSelesai: "2026-07-31",
  },
  {
    id: "p2",
    nama: "Periode Review PKM 2025/II",
    tanggalMulai: "2025-08-01",
    tanggalSelesai: "2025-11-30",
  },
  {
    id: "p3",
    nama: "Periode Review PKM 2025/I",
    tanggalMulai: "2025-02-01",
    tanggalSelesai: "2025-06-30",
  },
  {
    id: "p4",
    nama: "Periode Review PKM 2024/II",
    tanggalMulai: "2024-08-01",
    tanggalSelesai: "2024-11-30",
  },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatTanggal(iso: string) {
  return new Date(iso).toLocaleDateString("id-ID", {
    day: "numeric",
    month: "long",
    year: "numeric",
  })
}

function isOngoing(p: Periode) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return new Date(p.tanggalSelesai) >= today
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      className={`size-4 transition-transform duration-200 flex-none ${open ? "rotate-180" : ""}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
    </svg>
  )
}

function PlusIcon() {
  return (
    <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v14M5 12h14" />
    </svg>
  )
}

function CalendarIcon() {
  return (
    <svg className="size-3.5 flex-none opacity-60" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path strokeLinecap="round" d="M16 2v4M8 2v4M3 10h18" />
    </svg>
  )
}

// ─── Period Item ──────────────────────────────────────────────────────────────

function PeriodeItem({
  periode,
  isExpanded,
  onToggle,
  isOngoingItem,
}: {
  periode: Periode
  isExpanded: boolean
  onToggle: () => void
  isOngoingItem: boolean
}) {
  return (
    <div>
      {/* Row */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-4 px-5 py-4 text-left transition-colors hover:bg-pkm-50/50"
      >
        {/* Status dot */}
        <span
          className={`size-2 rounded-full flex-none mt-0.5 ${
            isOngoingItem ? "bg-pkm-600 shadow-[0_0_6px_rgba(0,153,102,0.5)]" : "bg-gray-300"
          }`}
        />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-800 truncate">{periode.nama}</p>
          <p className="text-xs mt-0.5" style={{ color: "rgba(0,0,0,0.4)" }}>
            {formatTanggal(periode.tanggalMulai)} — {formatTanggal(periode.tanggalSelesai)}
          </p>
        </div>
        <ChevronIcon open={isExpanded} />
      </button>

      {/* Expanded detail */}
      {isExpanded && (
        <div className="px-5 pb-5 bg-pkm-50/20 border-t border-gray-50">
          <div className="pt-4 flex items-start justify-between gap-4">
            {/* Info */}
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <CalendarIcon />
                <span>
                  Mulai:{" "}
                  <span className="font-medium text-gray-700">{formatTanggal(periode.tanggalMulai)}</span>
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <CalendarIcon />
                <span>
                  Selesai:{" "}
                  <span className="font-medium text-gray-700">{formatTanggal(periode.tanggalSelesai)}</span>
                </span>
              </div>
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

            {/* Action */}
            <Button variant="outline" size="sm" className="shrink-0 text-pkm-700 border-pkm-200 hover:bg-pkm-50">
              Lihat Detail
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Section (collapsible group) ─────────────────────────────────────────────

function PeriodeSection({
  title,
  periodes,
  count,
  defaultOpen,
  badgeClass,
  expandedId,
  onToggleItem,
  isOngoingSection,
}: {
  title: string
  periodes: Periode[]
  count: number
  defaultOpen: boolean
  badgeClass: string
  expandedId: string | null
  onToggleItem: (id: string) => void
  isOngoingSection: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="rounded-xl border border-gray-100 bg-white shadow-sm overflow-hidden">
      {/* Section header */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50/60 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <span className="text-sm font-semibold text-gray-700">{title}</span>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${badgeClass}`}>
            {count}
          </span>
        </div>
        <ChevronIcon open={open} />
      </button>

      {/* Period list */}
      {open && (
        <div className="divide-y divide-gray-50 border-t border-gray-50">
          {periodes.length === 0 ? (
            <div className="px-5 py-8 text-center text-sm" style={{ color: "rgba(0,0,0,0.35)" }}>
              Belum ada periode
            </div>
          ) : (
            periodes.map((p) => (
              <PeriodeItem
                key={p.id}
                periode={p}
                isExpanded={expandedId === p.id}
                onToggle={() => onToggleItem(p.id)}
                isOngoingItem={isOngoingSection}
              />
            ))
          )}
        </div>
      )}
    </div>
  )
}

// ─── Tambah Periode Modal ─────────────────────────────────────────────────────

function TambahPeriodeModal({
  onClose,
  onSave,
}: {
  onClose: () => void
  onSave: (data: Omit<Periode, "id">) => void
}) {
  const [nama, setNama] = useState("")
  const [tanggalMulai, setTanggalMulai] = useState("")
  const [tanggalSelesai, setTanggalSelesai] = useState("")

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!nama.trim() || !tanggalMulai || !tanggalSelesai) return
    onSave({ nama: nama.trim(), tanggalMulai, tanggalSelesai })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/25 backdrop-blur-[2px]"
        onClick={onClose}
      />

      {/* Modal card */}
      <div className="relative z-10 w-full max-w-md bg-white rounded-2xl shadow-2xl">
        {/* Header */}
        <div className="px-6 pt-6 pb-5 border-b border-gray-100">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-base font-semibold text-gray-800">Tambah Periode Review</h2>
              <p className="text-xs mt-0.5" style={{ color: "rgba(0,0,0,0.4)" }}>
                Tentukan nama dan rentang tanggal periode
              </p>
            </div>
            <button
              onClick={onClose}
              className="size-7 flex items-center justify-center rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors flex-none"
            >
              <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          {/* Nama Periode */}
          <div className="space-y-1.5">
            <Label htmlFor="nama" className="text-xs font-medium text-gray-600">
              Nama Periode
            </Label>
            <Input
              id="nama"
              value={nama}
              onChange={(e) => setNama(e.target.value)}
              placeholder="cth. Periode Review PKM 2026/II"
              required
            />
          </div>

          {/* Date range */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="tanggal-mulai" className="text-xs font-medium text-gray-600">
                Tanggal Mulai
              </Label>
              <Input
                id="tanggal-mulai"
                type="date"
                value={tanggalMulai}
                onChange={(e) => setTanggalMulai(e.target.value)}
                required
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
                onChange={(e) => setTanggalSelesai(e.target.value)}
                required
              />
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="outline" onClick={onClose}>
              Batal
            </Button>
            <Button type="submit">
              Simpan Periode
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PeriodeReviewPage() {
  const [periodes, setPeriodes] = useState<Periode[]>(MOCK_PERIODE)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)

  const berlangsung = periodes.filter(isOngoing)
  const telahLewat = periodes.filter((p) => !isOngoing(p))

  function handleToggleItem(id: string) {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  function handleSave(data: Omit<Periode, "id">) {
    setPeriodes((prev) => [{ id: `p${Date.now()}`, ...data }, ...prev])
    setShowModal(false)
  }

  return (
    <>
      {showModal && (
        <TambahPeriodeModal onClose={() => setShowModal(false)} onSave={handleSave} />
      )}

      <div className="px-8 py-8 max-w-2xl">
        {/* Page header */}
        <div className="flex items-start justify-between mb-7">
          <div>
            <h1 className="text-xl font-semibold text-gray-800">Periode Review PKM</h1>
            <p className="text-sm mt-0.5" style={{ color: "rgba(0,0,0,0.4)" }}>
              Kelola periode review Program Kreativitas Mahasiswa
            </p>
          </div>
          <Button onClick={() => setShowModal(true)} className="flex items-center gap-2 shrink-0">
            <PlusIcon />
            Tambah Periode
          </Button>
        </div>

        {/* Sections */}
        <div className="space-y-4">
          <PeriodeSection
            title="Berlangsung"
            periodes={berlangsung}
            count={berlangsung.length}
            defaultOpen={true}
            badgeClass="bg-pkm-100 text-pkm-700"
            expandedId={expandedId}
            onToggleItem={handleToggleItem}
            isOngoingSection={true}
          />
          <PeriodeSection
            title="Telah Lewat"
            periodes={telahLewat}
            count={telahLewat.length}
            defaultOpen={true}
            badgeClass="bg-gray-100 text-gray-500"
            expandedId={expandedId}
            onToggleItem={handleToggleItem}
            isOngoingSection={false}
          />
        </div>
      </div>
    </>
  )
}
