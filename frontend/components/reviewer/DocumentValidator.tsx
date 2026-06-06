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
  type ValidationCheck,
} from "@/lib/api/pkm"
import { PKM_SCHEMES } from "@/lib/constants/pkm-schemes"
import { YearPicker } from "@/components/ui/year-picker"

const MAX_FILE_SIZE = 10 * 1024 * 1024

const CATEGORY_LABELS: Record<string, string> = {
  typography        : "Typography",
  page_layout       : "Page Layout",
  spacing           : "Spacing",
  document_structure: "Struktur Dokumen",
  numbering         : "Penomoran",
  figures_tables    : "Gambar & Tabel",
  page_count        : "Jumlah Halaman",
}

// Peta nama field teknis (dari backend) → label Indonesia yang ramah dibaca.
// Dipakai di panel kiri supaya tidak tampil nama teknis seperti "figure_caption_position".
const FIELD_LABELS: Record<string, string> = {
  // ── Typography ──────────────────────────────────────────────────────────
  font_per_paragraph      : "Font elemen teks",
  undefined_style         : "Style tidak terdefinisi",
  paragraph_inherited     : "Atribut diwarisi (inherited)",
  paragraph_attribute     : "Atribut elemen teks",
  // ── Numbering ───────────────────────────────────────────────────────────
  preliminary_format      : "Format nomor halaman awal (romawi, sebelum Bab 1)",
  preliminary_location    : "Posisi nomor halaman awal (romawi)",
  preliminary_start       : "Titik mulai nomor halaman awal",
  content_format          : "Format nomor halaman isi (angka arab, mulai Bab 1)",
  content_location        : "Posisi nomor halaman isi (angka arab)",
  content_start           : "Titik mulai nomor halaman isi",
  page_number             : "Nomor halaman",
  // ── Layout ──────────────────────────────────────────────────────────────
  section_attribute       : "Atribut halaman",
  section_missing         : "Section tidak ditemukan",
  // ── Heading ─────────────────────────────────────────────────────────────
  heading_1_case          : "Kapitalisasi Heading 1",
  heading_2_case          : "Kapitalisasi Heading 2",
  heading_3_case          : "Kapitalisasi Heading 3",
  heading_4_case          : "Kapitalisasi Heading 4",
  heading_5_case          : "Kapitalisasi Heading 5",
  heading_case            : "Kapitalisasi heading",
  // ── Figures & Tables ────────────────────────────────────────────────────
  figure_caption_position : "Posisi caption gambar",
  figure_caption_format   : "Format caption gambar",
  table_caption_position  : "Posisi caption tabel",
  table_caption_format    : "Format caption tabel",
  caption                 : "Caption gambar/tabel",
  lampiran_separator      : "Format penulisan judul lampiran",
  lampiran_format         : "Atribut judul lampiran",
  lampiran_alignment      : "Rata teks judul lampiran",
  lampiran_font           : "Font judul lampiran",
  lampiran_font_size      : "Ukuran font judul lampiran",
  lampiran_spacing        : "Spasi judul lampiran",
  halaman_inti            : "Jumlah halaman inti",
}

// Terjemahan nama parameter teknis validocx → label Indonesia
const PARAM_LABELS: Record<string, string> = {
  font          : "Jenis huruf",
  alignment     : "Rata teks",
  line_spacing  : "Spasi baris",
  first_line_indent : "Indentasi baris pertama",
  space_before  : "Jarak sebelum",
  space_after   : "Jarak sesudah",
  left_indent   : "Indentasi kiri",
  right_indent  : "Indentasi kanan",
}

// Terjemahan nama style Word bawaan (bahasa Inggris) → Indonesia
const WORD_STYLE_LABELS: Record<string, string> = {
  "Normal"                 : "Normal",
  "Default Paragraph Font" : "Font default",
  "Heading 1"              : "Heading 1",
  "Heading 2"              : "Heading 2",
  "Heading 3"              : "Heading 3",
  "Body Text"              : "Teks isi",
  "Caption"                : "Caption",
  "Table Paragraph"        : "Teks tabel",
}

// Konversi nama field teknis ke label Indonesia.
// Menangani field dari FIELD_LABELS, field validocx_param.*, dan raw field name.
function formatFieldLabel(field: string): string {
  if (FIELD_LABELS[field]) return FIELD_LABELS[field]
  if (field.startsWith("validocx_param.")) {
    // Format asli: "validocx_param.font_(Default_Paragraph_Font)"
    // Tujuan: "Jenis huruf — Font default"
    const inner = field.replace("validocx_param.", "")
    // Pisahkan param dan style: "font_(Default_Paragraph_Font)" → ["font", "Default Paragraph Font"]
    const match = inner.match(/^(\S+?)_\((.+)\)$/)
    if (match) {
      const rawParam = match[1]
      const rawStyle = match[2].replace(/_/g, " ")
      const param = PARAM_LABELS[rawParam] ?? rawParam.replace(/_/g, " ")
      const style = WORD_STYLE_LABELS[rawStyle] ?? rawStyle
      const paramLabel = param.charAt(0).toUpperCase() + param.slice(1)
      return `${paramLabel} — ${style}`
    }
    // Fallback jika format tak cocok
    const stripped = inner.replace(/_/g, " ")
    return stripped.charAt(0).toUpperCase() + stripped.slice(1)
  }
  return field
}

// ── SummaryBar ───────────────────────────────────────────────────────────────
function SummaryBar({
  result,
  viewMode,
  onErrorClick,
  onWarningClick,
  onPassedClick,
}: {
  result: ValidationResult
  viewMode: "error" | "warning" | "passed"
  onErrorClick: () => void
  onWarningClick: () => void
  onPassedClick: () => void
}) {
  const errors   = result.issues?.filter((i) => i.severity === "error").length   ?? 0
  const warnings = result.issues?.filter((i) => i.severity === "warning").length ?? 0
  const passed   = result.summary?.passed ?? 0
  const isErrorActive   = viewMode === "error"
  const isWarningActive = viewMode === "warning"
  const isPassedActive  = viewMode === "passed"

  return (
    <div className="grid grid-cols-3 divide-x divide-border border-t border-border">
      <button
        type="button"
        onClick={onErrorClick}
        className={[
          "flex flex-col items-center py-4 transition-colors cursor-pointer",
          isErrorActive ? "bg-red-100 ring-1 ring-inset ring-red-200" : "bg-red-50 hover:bg-red-100/70",
        ].join(" ")}
      >
        <span className="text-2xl font-bold tabular-nums text-red-600">{errors}</span>
        <span className={["mt-0.5 text-[11px] font-medium uppercase tracking-wide", isErrorActive ? "text-red-700" : "text-gray-400"].join(" ")}>
          Error{isErrorActive ? " ▾" : ""}
        </span>
      </button>
      <button
        type="button"
        onClick={onWarningClick}
        className={[
          "flex flex-col items-center py-4 transition-colors cursor-pointer",
          isWarningActive ? "bg-amber-100 ring-1 ring-inset ring-amber-200" : "bg-amber-50 hover:bg-amber-100/70",
        ].join(" ")}
      >
        <span className="text-2xl font-bold tabular-nums text-amber-600">{warnings}</span>
        <span className={["mt-0.5 text-[11px] font-medium uppercase tracking-wide", isWarningActive ? "text-amber-700" : "text-gray-400"].join(" ")}>
          Peringatan{isWarningActive ? " ▾" : ""}
        </span>
      </button>
      <button
        type="button"
        onClick={onPassedClick}
        className={[
          "flex flex-col items-center py-4 transition-colors cursor-pointer",
          isPassedActive ? "bg-pkm-100 ring-1 ring-inset ring-pkm-200" : "bg-pkm-50 hover:bg-pkm-100/70",
        ].join(" ")}
      >
        <span className="text-2xl font-bold tabular-nums text-pkm-600">{passed}</span>
        <span className={["mt-0.5 text-[11px] font-medium uppercase tracking-wide", isPassedActive ? "text-pkm-700" : "text-gray-400"].join(" ")}>
          Lulus{isPassedActive ? " ▾" : ""}
        </span>
      </button>
    </div>
  )
}

// ── OccurrenceCard ───────────────────────────────────────────────────────────
function OccurrenceCard({
  occ,
  severity,
}: {
  occ: ValidationOccurrence
  severity?: string
}) {
  const accentColor = severity === "error" ? "border-l-red-300" : "border-l-amber-300"

  return (
    <div className={`rounded-lg border border-border bg-white border-l-4 ${accentColor} overflow-hidden`}>
      {/* Metadata row */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5 bg-gray-50/60 border-b border-border/50">
        {occ.page != null && (
          <span className="text-[11px] font-medium text-gray-500">
            Halaman {occ.page}
          </span>
        )}
        {occ.bab && (
          <>
            <span className="text-gray-300 text-xs">·</span>
            <span className="text-[11px] font-semibold text-pkm-700 bg-pkm-100 px-2 py-0.5 rounded-full">
              {occ.bab}
            </span>
          </>
        )}
      </div>

      {/* Body */}
      <div className="px-4 py-3 space-y-2.5">
        {occ.text && (
          <p className="text-xs text-gray-600 italic leading-relaxed border-l-2 border-gray-200 pl-3">
            &ldquo;{occ.text}&rdquo;
          </p>
        )}
        {(occ.actual || occ.expected) && (
          <div className="flex flex-wrap gap-2 pt-0.5">
            {occ.actual && (
              <span className="inline-flex items-center gap-1.5 text-xs bg-red-50 text-red-700 px-2.5 py-1 rounded-md border border-red-100">
                <span className="size-1.5 rounded-full bg-red-400 shrink-0" />
                <span className="font-medium">Ditemukan:</span>&nbsp;{occ.actual}
              </span>
            )}
            {occ.expected && (
              <span className="inline-flex items-center gap-1.5 text-xs bg-pkm-50 text-pkm-700 px-2.5 py-1 rounded-md border border-pkm-100">
                <span className="size-1.5 rounded-full bg-pkm-400 shrink-0" />
                <span className="font-medium">Seharusnya:</span>&nbsp;{occ.expected}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ── IssueListPanel ───────────────────────────────────────────────────────────
function IssueListPanel({
  issues,
  selectedIdx,
  onSelect,
}: {
  issues: ValidationIssue[]
  selectedIdx: number | null
  onSelect: (idx: number) => void
}) {
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
    <div className="border-r border-border overflow-y-auto flex flex-col">
      {/* Panel header */}
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-border sticky top-0 z-10">
        <span className="text-sm font-semibold text-gray-700">Detail Masalah</span>
        <span className="text-xs font-semibold bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
          {issues.length}
        </span>
      </div>

      <div className="flex-1">
        {Object.entries(grouped).map(([cat, items]) => {
          const label = CATEGORY_LABELS[cat] ?? cat
          return (
            <div key={cat}>
              {/* Category divider — subtle, no emoji */}
              <div className="flex items-center gap-2 px-4 py-2 bg-gray-50 border-b border-border/40">
                <span className="size-1.5 rounded-full bg-gray-300 shrink-0" />
                <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-[0.07em]">
                  {label}
                </span>
              </div>

              {items.map(({ issue, idx }) => {
                const isActive = selectedIdx === idx
                const isError  = issue.severity === "error"
                return (
                  <button
                    key={idx}
                    onClick={() => onSelect(idx)}
                    className={[
                      "w-full text-left px-4 py-3 border-b border-border/40 flex items-start gap-3 transition-colors duration-100",
                      isActive
                        ? "bg-pkm-50 border-l-[3px] border-l-pkm-600"
                        : "hover:bg-gray-50/80 border-l-[3px] border-l-transparent",
                    ].join(" ")}
                  >
                    {/* Severity pill */}
                    <span
                      className={[
                        "shrink-0 mt-0.5 text-[10px] font-bold px-1.5 py-0.5 rounded",
                        isError
                          ? "bg-red-100 text-red-600"
                          : "bg-amber-100 text-amber-600",
                      ].join(" ")}
                    >
                      {isError ? "ERR" : "WARN"}
                    </span>

                    <div className="flex-1 min-w-0">
                      <p className={`text-sm truncate ${isActive ? "font-semibold text-pkm-900" : "font-medium text-gray-800"}`}>
                        {FIELD_LABELS[issue.field ?? ""] ?? issue.field ?? CATEGORY_LABELS[issue.category] ?? issue.category}
                      </p>
                      <p className="text-[11px] text-gray-400 truncate mt-0.5 leading-tight">
                        {issue.message}
                      </p>
                    </div>

                    {(issue.occurrences?.length ?? 0) > 0 && (
                      <span
                        className={[
                          "shrink-0 text-[11px] font-semibold px-1.5 py-0.5 rounded-full tabular-nums",
                          isError
                            ? "bg-red-100 text-red-600"
                            : "bg-amber-100 text-amber-600",
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
    </div>
  )
}

// ── LocationPanel ────────────────────────────────────────────────────────────
function LocationPanel({ issue }: { issue: ValidationIssue | null }) {
  if (!issue) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[320px] bg-gray-50/60 gap-3">
        <div className="size-10 rounded-full bg-gray-100 flex items-center justify-center">
          <FileTextIcon className="size-5 text-gray-300" />
        </div>
        <p className="text-sm text-gray-400">Pilih masalah di kiri untuk melihat lokasi</p>
      </div>
    )
  }

  const occurrences = issue.occurrences ?? []

  return (
    <div className="flex flex-col overflow-y-auto">
      {/* Sticky header */}
      <div className="px-5 py-3.5 border-b border-border bg-white sticky top-0 z-10">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-gray-800 truncate">
              {FIELD_LABELS[issue.field ?? ""] ?? issue.field ?? CATEGORY_LABELS[issue.category] ?? issue.category}
            </p>
            <p className="text-xs text-gray-400 mt-0.5 line-clamp-1">{issue.message}</p>
          </div>
          {occurrences.length > 0 && (
            <span className="shrink-0 text-xs font-medium text-pkm-700 bg-pkm-100 px-2.5 py-1 rounded-full whitespace-nowrap">
              {occurrences.length} lokasi
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 p-4 space-y-3 bg-gray-50/40">
        {occurrences.length > 0 ? (
          occurrences.map((occ, i) => (
            <OccurrenceCard
              key={`${occ.page}-${occ.para_idx}-${i}`}
              occ={occ}
              severity={issue.severity}
            />
          ))
        ) : (
          <div className="rounded-lg border border-border bg-white p-4">
            <p className="text-sm text-gray-500">
              Masalah ini berlaku untuk seluruh dokumen, bukan pada elemen tertentu.
            </p>
            {(issue.expected || issue.actual) && (
              <div className="flex flex-wrap gap-2 mt-3">
                {issue.actual && (
                  <span className="inline-flex items-center gap-1.5 text-xs bg-red-50 text-red-700 px-2.5 py-1 rounded-md border border-red-100">
                    <span className="size-1.5 rounded-full bg-red-400 shrink-0" />
                    <span className="font-medium">Ditemukan:</span>&nbsp;{issue.actual}
                  </span>
                )}
                {issue.expected && (
                  <span className="inline-flex items-center gap-1.5 text-xs bg-pkm-50 text-pkm-700 px-2.5 py-1 rounded-md border border-pkm-100">
                    <span className="size-1.5 rounded-full bg-pkm-400 shrink-0" />
                    <span className="font-medium">Seharusnya:</span>&nbsp;{issue.expected}
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

// ── DocumentValidator (komponen utama) ───────────────────────────────────────
// ── PassedListPanel ──────────────────────────────────────────────────────────
// Panel kiri saat mode "Lulus": menampilkan semua pengecekan yang lolos,
// dikelompokkan per kategori. `checks` adalah flat list dari result.report.
function PassedListPanel({
  checks,
  selectedIdx,
  onSelect,
}: {
  checks: ValidationCheck[]
  selectedIdx: number | null
  onSelect: (idx: number) => void
}) {
  const grouped = checks.reduce<Record<string, Array<{ check: ValidationCheck; idx: number }>>>(
    (acc, check, idx) => {
      const cat = check.category ?? "other"
      if (!acc[cat]) acc[cat] = []
      acc[cat].push({ check, idx })
      return acc
    },
    {}
  )

  return (
    <div className="border-r border-border overflow-y-auto flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-border sticky top-0 z-10">
        <span className="text-sm font-semibold text-gray-700">Pengecekan Lulus</span>
        <span className="text-xs font-semibold bg-pkm-100 text-pkm-700 px-2 py-0.5 rounded-full">
          {checks.length}
        </span>
      </div>
      <div className="flex-1">
        {Object.entries(grouped).map(([cat, items]) => (
          <div key={cat}>
            <div className="flex items-center gap-2 px-4 py-2 bg-gray-50 border-b border-border/40">
              <span className="size-1.5 rounded-full bg-pkm-400 shrink-0" />
              <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-[0.07em]">
                {CATEGORY_LABELS[cat] ?? cat}
              </span>
            </div>
            {items.map(({ check, idx }) => {
              const isActive = selectedIdx === idx
              return (
                <button
                  key={idx}
                  onClick={() => onSelect(idx)}
                  className={[
                    "w-full text-left px-4 py-3 border-b border-border/40 flex items-start gap-3 transition-colors",
                    isActive
                      ? "bg-pkm-50 border-l-[3px] border-l-pkm-600"
                      : "hover:bg-gray-50 border-l-[3px] border-l-transparent",
                  ].join(" ")}
                >
                  <span className="shrink-0 mt-0.5 text-[10px] font-bold px-1.5 py-0.5 rounded bg-pkm-100 text-pkm-700">
                    OK
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm truncate ${isActive ? "font-semibold text-pkm-900" : "font-medium text-gray-800"}`}>
                      {formatFieldLabel(check.field)}
                    </p>
                    <p className="text-[11px] text-gray-400 truncate mt-0.5 leading-tight">
                      {check.message}
                    </p>
                  </div>
                </button>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── PassedDetailPanel ────────────────────────────────────────────────────────
// Panel kanan saat mode "Lulus": detail pengecekan yang dipilih.
// Menampilkan nilai yang ditemukan di dokumen dan nilai yang diharapkan.
function PassedDetailPanel({ check }: { check: ValidationCheck | null }) {
  if (!check) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[320px] bg-gray-50/60 gap-3">
        <div className="size-10 rounded-full bg-pkm-100 flex items-center justify-center">
          <CheckCircleIcon className="size-5 text-pkm-500" />
        </div>
        <p className="text-sm text-gray-400">Pilih pengecekan di kiri untuk melihat detail</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col overflow-y-auto bg-gray-50/40">
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-border bg-white sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <span className="size-4 rounded-full bg-pkm-100 flex items-center justify-center shrink-0">
            <CheckCircleIcon className="size-3 text-pkm-600" />
          </span>
          <p className="text-sm font-semibold text-gray-800">{formatFieldLabel(check.field)}</p>
        </div>
        <p className="text-xs text-gray-400 mt-1 ml-6">{check.message}</p>
      </div>

      {/* Detail nilai */}
      <div className="p-4 space-y-3">
        <div className="rounded-lg border border-pkm-100 bg-white p-4 space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold bg-pkm-100 text-pkm-700 px-2 py-0.5 rounded-full">Lolos ✓</span>
            <span className="text-xs text-gray-500">Pengecekan ini sesuai dengan aturan</span>
          </div>
          {(check.expected || check.actual) && (
            <div className="flex flex-wrap gap-2 pt-1">
              {check.actual && (
                <span className="inline-flex items-center gap-1.5 text-xs bg-pkm-50 text-pkm-700 px-2.5 py-1 rounded-md border border-pkm-100">
                  <span className="size-1.5 rounded-full bg-pkm-400 shrink-0" />
                  <span className="font-medium">Ditemukan:</span>&nbsp;{check.actual}
                </span>
              )}
              {check.expected && (
                <span className="inline-flex items-center gap-1.5 text-xs bg-pkm-50 text-pkm-700 px-2.5 py-1 rounded-md border border-pkm-100">
                  <span className="size-1.5 rounded-full bg-pkm-400 shrink-0" />
                  <span className="font-medium">Seharusnya:</span>&nbsp;{check.expected}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function DocumentValidator() {
  const [selectedSchemaId, setSelectedSchemaId] = useState<string>("")
  const [selectedYear, setSelectedYear]         = useState<string>("")
  const [file, setFile]                         = useState<File | null>(null)
  const [loading, setLoading]                   = useState(false)
  const [result, setResult]                     = useState<ValidationResult | null>(null)
  const [error, setError]                       = useState<string | null>(null)
  const [selectedIssueIdx, setSelectedIssueIdx] = useState<number | null>(null)
  // viewMode: "error" = tampil error (default), "warning" = tampil peringatan, "passed" = tampil yang lolos
  const [viewMode, setViewMode]                 = useState<"error" | "warning" | "passed">("error")
  const [selectedCheckIdx, setSelectedCheckIdx] = useState<number | null>(null)

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
    setViewMode("error")
    setSelectedCheckIdx(null)

    const res = await runDocumentValidation({ schemaId: selectedSchemaId, year: selectedYear, file })
    setLoading(false)

    if (res.error) {
      setError(res.error)
    } else {
      setResult(res.data)
      if (res.data?.valid) setViewMode("passed")
    }
  }

  const handleReset = () => {
    setSelectedSchemaId("")
    setSelectedYear("")
    setFile(null)
    setResult(null)
    setError(null)
    setSelectedIssueIdx(null)
    setViewMode("error")
    setSelectedCheckIdx(null)
  }

  const allIssues = result?.issues ?? []
  const filteredIssues = viewMode === "error"
    ? allIssues.filter((i) => i.severity === "error")
    : viewMode === "warning"
    ? allIssues.filter((i) => i.severity === "warning")
    : allIssues

  // Ambil semua checks yang lulus dari result.report (diratakan dari semua kategori)
  const passedChecks: ValidationCheck[] = Object.values(result?.report ?? {})
    .flat()
    .filter((c) => c.status === "passed")

  return (
    <ReviewerSurfaceCard>
      {/* Header */}
      <div className="px-6 pt-6 pb-4">
        <h3 className="text-base font-semibold flex items-center gap-2">
          <FileTextIcon className="size-5 text-primary" />
          Validasi Dokumen Otomatis
        </h3>
      </div>

      {/* Form */}
      <div className="px-6 pb-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">1. Pilih Skema PKM</label>
            <Select value={selectedSchemaId} onValueChange={setSelectedSchemaId}>
              <SelectTrigger>
                <SelectValue placeholder="Pilih jenis PKM" />
              </SelectTrigger>
              <SelectContent>
                {PKM_SCHEMES.map((s) => (
                  <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">2. Pilih Tahun</label>
            <YearPicker value={selectedYear} onChange={setSelectedYear} placeholder="Pilih tahun" disabled={loading} />
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
                  <p className="text-xs text-muted-foreground mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); handleReset() }}
                    className="mt-2 text-xs text-destructive hover:underline"
                  >
                    Hapus file
                  </button>
                </>
              ) : (
                <>
                  <UploadIcon className="size-8 text-muted-foreground mb-2" />
                  <p className="text-sm text-muted-foreground">Seret file ke sini atau klik untuk memilih</p>
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
              <><Loader2Icon className="size-4 animate-spin" /><span>Memvalidasi...</span></>
            ) : (
              <><CheckCircleIcon className="size-4" /><span>Validasi Dokumen</span></>
            )}
          </Button>
          {result && <Button variant="outline" onClick={handleReset}>Reset</Button>}
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
          <div className="px-6 pb-4">
            {result.valid ? (
              <Alert className="border-pkm-100 bg-pkm-50">
                <CheckCircleIcon className="size-4 text-pkm-600" />
                <AlertTitle className="text-pkm-900">Dokumen Valid</AlertTitle>
                <AlertDescription className="text-pkm-700">
                  Semua persyaratan format terpenuhi.
                  {result.summary && (
                    <span className="ml-1">({result.summary.passed ?? 0} dari {result.summary.total_checks ?? 0} pemeriksaan lulus)</span>
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

          <div className="border-t border-border">
              <SummaryBar
                result={result}
                viewMode={viewMode}
                onErrorClick={() => {
                  setViewMode("error")
                  setSelectedIssueIdx(null)
                }}
                onWarningClick={() => {
                  setViewMode((m) => m === "warning" ? "error" : "warning")
                  setSelectedIssueIdx(null)
                }}
                onPassedClick={() => {
                  setViewMode((m) => m === "passed" ? "error" : "passed")
                  setSelectedCheckIdx(null)
                }}
              />
              <div className="grid grid-cols-[300px_1fr] border-t border-border overflow-hidden" style={{ height: 680 }}>
                {viewMode === "passed" ? (
                  <>
                    <PassedListPanel
                      checks={passedChecks}
                      selectedIdx={selectedCheckIdx}
                      onSelect={setSelectedCheckIdx}
                    />
                    <PassedDetailPanel
                      check={selectedCheckIdx !== null ? passedChecks[selectedCheckIdx] : null}
                    />
                  </>
                ) : (
                  <>
                    <IssueListPanel
                      issues={filteredIssues}
                      selectedIdx={selectedIssueIdx}
                      onSelect={setSelectedIssueIdx}
                    />
                    <LocationPanel
                      issue={selectedIssueIdx !== null ? filteredIssues[selectedIssueIdx] : null}
                    />
                  </>
                )}
              </div>
            </div>
        </>
      )}
    </ReviewerSurfaceCard>
  )
}
