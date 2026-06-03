"use client"

import { useCallback, useState } from "react"
import { ReviewerSurfaceCard } from "./shared"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import {
  Loader2Icon,
  UploadIcon,
  CheckCircleIcon,
  AlertCircleIcon,
  FileTextIcon,
} from "@/components/icons/public-icons"
import {
  runDocumentValidation,
  type ValidationResult,
  type ValidationIssue,
  type ValidationOccurrence,
} from "@/lib/api/pkm"
import { PKM_SCHEMES } from "@/lib/constants/pkm-schemes"
import { YearPicker } from "@/components/ui/year-picker"

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

// Konfigurasi label dan ikon per kategori masalah validasi.
// Kategori ini sama dengan yang dikirim oleh backend (typography, page_layout, dst.)
const CATEGORY_CONFIG: Record<string, { label: string; icon: string }> = {
  typography        : { label: "Typography",       icon: "🔤" },
  page_layout       : { label: "Page Layout",      icon: "📐" },
  spacing           : { label: "Spacing",          icon: "↕"  },
  document_structure: { label: "Struktur Dokumen", icon: "📋" },
  numbering         : { label: "Penomoran",        icon: "🔢" },
  figures_tables    : { label: "Gambar & Tabel",   icon: "📊" },
}

// SummaryBar: empat kotak angka ringkasan di atas dua panel.
// Menampilkan jumlah Error, Peringatan, Lulus, dan Dilewati.
function SummaryBar({ result }: { result: ValidationResult }) {
  const errors   = result.issues?.filter((i) => i.severity === "error").length   ?? 0
  const warnings = result.issues?.filter((i) => i.severity === "warning").length ?? 0

  const items = [
    { count: errors,                         label: "Error",      color: "text-red-600"    },
    { count: warnings,                       label: "Peringatan", color: "text-yellow-600" },
    { count: result.summary?.passed  ?? 0,  label: "Lulus",      color: "text-green-600"  },
    { count: result.issues?.filter((i) => i.severity === "info").length ?? 0, label: "Dilewati", color: "text-slate-400" },
  ]

  return (
    <div className="grid grid-cols-4 border-t border-border">
      {items.map(({ count, label, color }, i) => (
        <div
          key={label}
          className={[
            "flex flex-col items-center py-3",
            i < items.length - 1 ? "border-r border-border" : "",
          ].join(" ")}
        >
          <span className={`text-2xl font-bold ${color}`}>{count}</span>
          <span className="text-xs text-muted-foreground mt-0.5">{label}</span>
        </div>
      ))}
    </div>
  )
}

// OccurrenceCard: satu kartu = satu lokasi spesifik sebuah masalah.
// Menampilkan nomor halaman, nama BAB, nomor paragraf, cuplikan teks,
// dan badge merah/hijau untuk nilai salah vs nilai yang seharusnya.
function OccurrenceCard({ occ }: { occ: ValidationOccurrence }) {
  return (
    <div className="rounded-lg border border-border bg-white p-3 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {occ.page != null && (
          <span className="text-xs font-semibold bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
            📄 Halaman {occ.page}
          </span>
        )}
        {occ.bab && (
          <span className="text-xs font-semibold bg-green-100 text-green-700 px-2 py-0.5 rounded">
            📂 {occ.bab}
          </span>
        )}
        {occ.para_idx != null && (
          <span className="text-xs text-muted-foreground">
            Paragraf ke-{occ.para_idx + 1}
          </span>
        )}
        {occ.style && (
          <span className="text-xs text-muted-foreground">· Style: {occ.style}</span>
        )}
      </div>

      {occ.text && (
        <p className="text-xs italic text-slate-600 bg-slate-50 px-3 py-2 rounded border-l-2 border-slate-300">
          &ldquo;{occ.text}&rdquo;
        </p>
      )}

      {(occ.actual || occ.expected) && (
        <div className="flex flex-wrap gap-2">
          {occ.actual && (
            <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">
              ❌ Ditemukan: {occ.actual}
            </span>
          )}
          {occ.expected && (
            <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">
              ✓ Harus: {occ.expected}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

// IssueListPanel: panel kiri berisi daftar semua masalah dikelompokkan per kategori.
// `selectedIdx` adalah index dari allIssues flat list yang sedang aktif.
// `onSelect` dipanggil saat baris diklik untuk memperbarui selectedIdx.
function IssueListPanel({
  issues,
  selectedIdx,
  onSelect,
}: {
  issues: ValidationIssue[]
  selectedIdx: number | null
  onSelect: (idx: number) => void
}) {
  // Kelompokkan issues per kategori, pertahankan urutan kemunculan asli
  const grouped = issues.reduce<Record<string, Array<{ issue: ValidationIssue; idx: number }>>>(
    (acc, issue, idx) => {
      const cat = issue.category ?? "other"
      if (!acc[cat]) acc[cat] = []
      acc[cat].push({ issue, idx })
      return acc
    },
    {}
  )

  return (
    <div className="border-r border-border overflow-y-auto">
      <div className="px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide bg-muted/50 border-b border-border">
        Detail Masalah ({issues.length})
      </div>

      {Object.entries(grouped).map(([cat, items]) => {
        const config = CATEGORY_CONFIG[cat] ?? { label: cat, icon: "•" }
        return (
          <div key={cat}>
            <div className="px-4 py-1.5 text-xs font-bold text-muted-foreground/70 uppercase tracking-widest bg-muted/30 border-b border-border/50">
              {config.icon} {config.label}
            </div>

            {items.map(({ issue, idx }) => {
              const isActive = selectedIdx === idx
              const isError  = issue.severity === "error"
              return (
                <button
                  key={idx}
                  onClick={() => onSelect(idx)}
                  className={[
                    "w-full text-left px-4 py-2.5 border-b border-border/50 flex items-start gap-2.5 transition-colors",
                    isActive
                      ? "bg-blue-50 border-l-2 border-l-blue-500"
                      : "hover:bg-muted/40",
                  ].join(" ")}
                >
                  <div
                    className={[
                      "shrink-0 size-4 rounded-full flex items-center justify-center text-[10px] font-bold mt-0.5",
                      isError
                        ? "bg-red-100 text-red-700"
                        : "bg-yellow-100 text-yellow-700",
                    ].join(" ")}
                  >
                    {isError ? "!" : "i"}
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{issue.field ?? issue.category}</p>
                    <p className="text-xs text-muted-foreground truncate mt-0.5">{issue.message}</p>
                  </div>

                  {(issue.occurrences?.length ?? 0) > 0 && (
                    <span
                      className={[
                        "shrink-0 text-xs font-semibold px-1.5 py-0.5 rounded-full",
                        isError
                          ? "bg-red-100 text-red-700"
                          : "bg-yellow-100 text-yellow-700",
                      ].join(" ")}
                    >
                      {issue.occurrences!.length}×
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        )
      })}
    </div>
  )
}

// LocationPanel: panel kanan menampilkan detail lokasi masalah yang dipilih.
// Jika `issue` null (belum ada yang diklik), tampilkan empty state.
// Jika issue punya occurrences, tampilkan OccurrenceCard per lokasi.
// Jika tidak punya occurrences (masalah level dokumen), tampilkan info actual/expected saja.
function LocationPanel({ issue }: { issue: ValidationIssue | null }) {
  if (!issue) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[300px] text-muted-foreground bg-muted/20">
        <FileTextIcon className="size-8 mb-3 opacity-30" />
        <p className="text-sm">Klik salah satu masalah di kiri untuk melihat lokasi</p>
      </div>
    )
  }

  const occurrences = issue.occurrences ?? []

  return (
    <div className="overflow-y-auto bg-muted/10">
      <div className="px-5 py-3 border-b border-border bg-white sticky top-0">
        <p className="text-sm font-semibold">
          {issue.field ?? issue.category}
          {occurrences.length > 0 && (
            <span className="ml-2 text-xs font-normal text-muted-foreground">
              — {occurrences.length} lokasi ditemukan
            </span>
          )}
        </p>
        <p className="text-xs text-muted-foreground mt-0.5">{issue.message}</p>
      </div>

      <div className="p-4 space-y-3">
        {occurrences.length > 0 ? (
          occurrences.map((occ, i) => <OccurrenceCard key={i} occ={occ} />)
        ) : (
          <div className="rounded-lg border border-border bg-white p-4">
            <p className="text-sm text-muted-foreground">
              Masalah ini berlaku untuk seluruh dokumen, bukan paragraf tertentu.
            </p>
            {(issue.expected || issue.actual) && (
              <div className="flex flex-wrap gap-2 mt-3">
                {issue.actual && (
                  <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">
                    ❌ Ditemukan: {issue.actual}
                  </span>
                )}
                {issue.expected && (
                  <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">
                    ✓ Harus: {issue.expected}
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// Komponen utama halaman validasi.
// Mengelola state upload, proses validasi, dan state UI (masalah yang dipilih di panel kiri).
export function DocumentValidator() {
  const [selectedSchemaId, setSelectedSchemaId] = useState<string>("")
  const [selectedYear, setSelectedYear]         = useState<string>("")
  const [file, setFile]                         = useState<File | null>(null)
  const [loading, setLoading]                   = useState(false)
  const [result, setResult]                     = useState<ValidationResult | null>(null)
  const [error, setError]                       = useState<string | null>(null)
  // selectedIssueIdx: index masalah di allIssues yang sedang diklik di panel kiri.
  // null = belum ada yang dipilih (panel kanan menampilkan empty state).
  const [selectedIssueIdx, setSelectedIssueIdx] = useState<number | null>(null)

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (selected) {
      if (selected.size > MAX_FILE_SIZE) {
        setError("Ukuran file terlalu besar. Maksimal 10MB.")
        setFile(null)
        return
      }
      const isDocx =
        selected.type === "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ||
        selected.name.toLowerCase().endsWith(".docx")
      if (!isDocx) {
        setError("Hanya file DOCX yang diterima.")
        setFile(null)
        return
      }
      setError(null)
      setFile(selected)
      setResult(null)
      setSelectedIssueIdx(null)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const dropped = e.dataTransfer.files?.[0]
    if (dropped) {
      const fakeEvent = { target: { files: [dropped] } } as unknown as React.ChangeEvent<HTMLInputElement>
      handleFileChange(fakeEvent)
    }
  }, [handleFileChange])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
  }, [])

  const handleValidate = async () => {
    if (!selectedSchemaId || !selectedYear || !file) {
      setError("Pilih skema PKM, tahun, dan upload file proposal terlebih dahulu.")
      return
    }
    setLoading(true)
    setError(null)
    setResult(null)
    setSelectedIssueIdx(null)

    const res = await runDocumentValidation({ schemaId: selectedSchemaId, year: selectedYear, file })
    setLoading(false)

    if (res.error) {
      setError(res.error)
    } else {
      setResult(res.data)
    }
  }

  const handleReset = () => {
    setSelectedSchemaId("")
    setSelectedYear("")
    setFile(null)
    setResult(null)
    setError(null)
    setSelectedIssueIdx(null)
  }

  // allIssues: flat list semua masalah — dipakai untuk index-based selection antara panel kiri dan kanan
  const allIssues = result?.issues ?? []

  return (
    <ReviewerSurfaceCard>
      {/* Header */}
      <div className="px-6 pt-6 pb-4">
        <h3 className="text-base font-semibold flex items-center gap-2">
          <FileTextIcon className="size-5 text-primary" />
          Validasi Dokumen Otomatis
        </h3>
      </div>

      {/* Form upload */}
      <div className="px-6 pb-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">1. Pilih Skema PKM</label>
            <Select value={selectedSchemaId} onValueChange={setSelectedSchemaId}>
              <SelectTrigger>
                <SelectValue placeholder="Pilih jenis PKM" />
              </SelectTrigger>
              <SelectContent>
                {PKM_SCHEMES.map((schema) => (
                  <SelectItem key={schema.value} value={schema.value}>
                    {schema.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">2. Pilih Tahun</label>
            <YearPicker
              value={selectedYear}
              onChange={setSelectedYear}
              placeholder="Pilih tahun"
              disabled={loading}
            />
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">3. Upload Proposal</label>
          <div
            className={[
              "relative rounded-lg border-2 border-dashed p-6 transition-colors",
              file
                ? "border-primary bg-primary/5"
                : "border-muted-foreground/25 hover:border-muted-foreground/50",
            ].join(" ")}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
          >
            <input
              type="file"
              accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={handleFileChange}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              disabled={loading}
            />
            <div className="flex flex-col items-center text-center">
              {file ? (
                <>
                  <FileTextIcon className="size-8 text-primary mb-2" />
                  <p className="text-sm font-medium">{file.name}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); setFile(null); setResult(null) }}
                    className="mt-2 text-xs text-destructive hover:underline"
                  >
                    Hapus file
                  </button>
                </>
              ) : (
                <>
                  <UploadIcon className="size-8 text-muted-foreground mb-2" />
                  <p className="text-sm text-muted-foreground">
                    Seret file ke sini atau klik untuk memilih
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">Format: DOCX, maks 10MB</p>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            onClick={handleValidate}
            disabled={!selectedSchemaId || !selectedYear || !file || loading}
            className="flex-1 sm:flex-none"
          >
            {loading ? (
              <>
                <Loader2Icon className="size-4 animate-spin" />
                <span>Memvalidasi...</span>
              </>
            ) : (
              <>
                <CheckCircleIcon className="size-4" />
                <span>Validasi Dokumen</span>
              </>
            )}
          </Button>

          {result && (
            <Button variant="outline" onClick={handleReset}>
              Reset
            </Button>
          )}
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertCircleIcon className="size-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </div>

      {/* Hasil validasi */}
      {result && (
        <>
          {/* Alert status overall */}
          <div className="px-6 pb-4">
            {result.valid ? (
              <Alert className="border-green-200 bg-green-50">
                <CheckCircleIcon className="size-4 text-green-600" />
                <AlertTitle className="text-green-800">Dokumen Valid</AlertTitle>
                <AlertDescription className="text-green-700">
                  Dokumen proposal telah memenuhi semua persyaratan format.
                  {result.summary && (
                    <span className="ml-1">
                      ({result.summary.passed ?? 0} dari {result.summary.total_checks ?? 0} pemeriksaan lulus)
                    </span>
                  )}
                </AlertDescription>
              </Alert>
            ) : (
              <Alert variant="destructive">
                <AlertCircleIcon className="size-4" />
                <AlertTitle>Ditemukan Masalah Format</AlertTitle>
                <AlertDescription>
                  {allIssues.filter((i) => i.severity === "error").length} error,{" "}
                  {allIssues.filter((i) => i.severity === "warning").length} peringatan ditemukan.
                </AlertDescription>
              </Alert>
            )}
          </div>

          {/* Summary bar + dua panel */}
          {allIssues.length > 0 && (
            <div className="border-t border-border">
              <SummaryBar result={result} />
              <div className="grid grid-cols-[320px_1fr] border-t border-border min-h-[360px] max-h-[600px]">
                <IssueListPanel
                  issues={allIssues}
                  selectedIdx={selectedIssueIdx}
                  onSelect={setSelectedIssueIdx}
                />
                <LocationPanel
                  issue={selectedIssueIdx !== null ? allIssues[selectedIssueIdx] : null}
                />
              </div>
            </div>
          )}
        </>
      )}
    </ReviewerSurfaceCard>
  )
}
