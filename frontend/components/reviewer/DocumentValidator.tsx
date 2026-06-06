"use client"

import { useCallback, useEffect, useRef, useState } from "react"
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
  ChevronDownIcon,
  ChevronRightIcon,
  PlusIcon,
  TrashIcon,
  LayersIcon,
} from "@/components/icons/public-icons"
import {
  runDocumentValidation,
  runBulkValidation,
  checkJobStatus,
  type ValidationResult,
  type ValidationIssue,
  type ValidationOccurrence,
  type ValidationCheck,
  type JobStatus,
  type JobItemStatus,
} from "@/lib/api/pkm"
import { PKM_SCHEMES } from "@/lib/constants/pkm-schemes"
import { YearPicker } from "@/components/ui/year-picker"

// ─── Konstanta ───────────────────────────────────────────────────────────────

const MAX_FILE_SIZE     = 10 * 1024 * 1024   // 10 MB
const JOB_STORAGE_KEY  = "validation_bulk_job_id"
const POLL_INTERVAL_MS = 3000

const CATEGORY_LABELS: Record<string, string> = {
  typography        : "Typography",
  page_layout       : "Page Layout",
  spacing           : "Spacing",
  document_structure: "Struktur Dokumen",
  numbering         : "Penomoran",
  figures_tables    : "Gambar & Tabel",
  page_count        : "Jumlah Halaman",
}

const FIELD_LABELS: Record<string, string> = {
  font_per_paragraph      : "Font elemen teks",
  undefined_style         : "Style tidak terdefinisi",
  paragraph_inherited     : "Atribut diwarisi (inherited)",
  paragraph_attribute     : "Atribut elemen teks",
  preliminary_format      : "Format nomor halaman awal (romawi, sebelum Bab 1)",
  preliminary_location    : "Posisi nomor halaman awal (romawi)",
  preliminary_start       : "Titik mulai nomor halaman awal",
  content_format          : "Format nomor halaman isi (angka arab, mulai Bab 1)",
  content_location        : "Posisi nomor halaman isi (angka arab)",
  content_start           : "Titik mulai nomor halaman isi",
  page_number             : "Nomor halaman",
  section_attribute       : "Atribut halaman",
  section_missing         : "Section tidak ditemukan",
  heading_1_case          : "Kapitalisasi Heading 1",
  heading_2_case          : "Kapitalisasi Heading 2",
  heading_3_case          : "Kapitalisasi Heading 3",
  heading_4_case          : "Kapitalisasi Heading 4",
  heading_5_case          : "Kapitalisasi Heading 5",
  heading_case            : "Kapitalisasi heading",
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

const PARAM_LABELS: Record<string, string> = {
  font              : "Jenis huruf",
  alignment         : "Rata teks",
  line_spacing      : "Spasi baris",
  first_line_indent : "Indentasi baris pertama",
  space_before      : "Jarak sebelum",
  space_after       : "Jarak sesudah",
  left_indent       : "Indentasi kiri",
  right_indent      : "Indentasi kanan",
}

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

// ─── Helper: format field label ───────────────────────────────────────────────

function formatFieldLabel(field: string): string {
  if (FIELD_LABELS[field]) return FIELD_LABELS[field]
  if (field.startsWith("validocx_param.")) {
    const inner = field.replace("validocx_param.", "")
    const match = inner.match(/^(\S+?)_\((.+)\)$/)
    if (match) {
      const rawParam = match[1]
      const rawStyle = match[2].replace(/_/g, " ")
      const param    = PARAM_LABELS[rawParam] ?? rawParam.replace(/_/g, " ")
      const style    = WORD_STYLE_LABELS[rawStyle] ?? rawStyle
      const label    = param.charAt(0).toUpperCase() + param.slice(1)
      return `${label} — ${style}`
    }
    const stripped = inner.replace(/_/g, " ")
    return stripped.charAt(0).toUpperCase() + stripped.slice(1)
  }
  return field
}

// ─── Helper: parse nama file → nama ketua + skema PKM ───────────────────────

function parseFileName(fileName: string): { ketua: string; scheme: string } {
  const base  = fileName.replace(/\.docx$/i, "")
  const parts = base.split("_")

  const rawKetua  = parts[0] ?? base
  const rawScheme = parts[parts.length - 1] ?? ""

  // Cocokkan ke nilai PKM_SCHEMES (PKMKC → PKM-KC)
  const normalizedScheme = rawScheme.toUpperCase()
  const matched = PKM_SCHEMES.find(
    (s) => s.value.replace("-", "").toUpperCase() === normalizedScheme
  )

  return {
    ketua:  rawKetua,
    scheme: matched?.value ?? rawScheme,
  }
}

// ─── Helper: validasi file ────────────────────────────────────────────────────

function validateDocxFile(f: File): string | null {
  if (f.size > MAX_FILE_SIZE) return "Ukuran file terlalu besar. Maksimal 10MB."
  const isDocx =
    f.type === "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ||
    f.name.toLowerCase().endsWith(".docx")
  if (!isDocx) return "Hanya file DOCX yang diterima."
  return null
}

// ─── Tipe bulk item ───────────────────────────────────────────────────────────

type BulkItem = {
  id:        string
  schemaId:  string
  year:      string
  file:      File | null
  collapsed: boolean
  fileError: string | null
}

function makeBulkItem(): BulkItem {
  return {
    id:        crypto.randomUUID(),
    schemaId:  "",
    year:      "",
    file:      null,
    collapsed: false,
    fileError: null,
  }
}

// ─── Sub-komponen: SummaryBar ─────────────────────────────────────────────────

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

  return (
    <div className="grid grid-cols-3 divide-x divide-border border-t border-border">
      <button
        type="button"
        onClick={onErrorClick}
        className={[
          "flex flex-col items-center py-4 transition-colors cursor-pointer",
          viewMode === "error"
            ? "bg-red-100 ring-1 ring-inset ring-red-200"
            : "bg-red-50 hover:bg-red-100/70",
        ].join(" ")}
      >
        <span className="text-2xl font-bold tabular-nums text-red-600">{errors}</span>
        <span className={["mt-0.5 text-[11px] font-medium uppercase tracking-wide", viewMode === "error" ? "text-red-700" : "text-gray-400"].join(" ")}>
          Error{viewMode === "error" ? " ▾" : ""}
        </span>
      </button>
      <button
        type="button"
        onClick={onWarningClick}
        className={[
          "flex flex-col items-center py-4 transition-colors cursor-pointer",
          viewMode === "warning"
            ? "bg-amber-100 ring-1 ring-inset ring-amber-200"
            : "bg-amber-50 hover:bg-amber-100/70",
        ].join(" ")}
      >
        <span className="text-2xl font-bold tabular-nums text-amber-600">{warnings}</span>
        <span className={["mt-0.5 text-[11px] font-medium uppercase tracking-wide", viewMode === "warning" ? "text-amber-700" : "text-gray-400"].join(" ")}>
          Peringatan{viewMode === "warning" ? " ▾" : ""}
        </span>
      </button>
      <button
        type="button"
        onClick={onPassedClick}
        className={[
          "flex flex-col items-center py-4 transition-colors cursor-pointer",
          viewMode === "passed"
            ? "bg-pkm-100 ring-1 ring-inset ring-pkm-200"
            : "bg-pkm-50 hover:bg-pkm-100/70",
        ].join(" ")}
      >
        <span className="text-2xl font-bold tabular-nums text-pkm-600">{passed}</span>
        <span className={["mt-0.5 text-[11px] font-medium uppercase tracking-wide", viewMode === "passed" ? "text-pkm-700" : "text-gray-400"].join(" ")}>
          Lulus{viewMode === "passed" ? " ▾" : ""}
        </span>
      </button>
    </div>
  )
}

// ─── Sub-komponen: OccurrenceCard ─────────────────────────────────────────────

function OccurrenceCard({ occ, severity }: { occ: ValidationOccurrence; severity?: string }) {
  const accentColor = severity === "error" ? "border-l-red-300" : "border-l-amber-300"

  return (
    <div className={`rounded-lg border border-border bg-white border-l-4 ${accentColor} overflow-hidden`}>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5 bg-gray-50/60 border-b border-border/50">
        {occ.page != null && (
          <span className="text-[11px] font-medium text-gray-500">Halaman {occ.page}</span>
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

// ─── Sub-komponen: IssueListPanel ─────────────────────────────────────────────

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
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-border sticky top-0 z-10">
        <span className="text-sm font-semibold text-gray-700">Detail Masalah</span>
        <span className="text-xs font-semibold bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
          {issues.length}
        </span>
      </div>
      <div className="flex-1">
        {Object.entries(grouped).map(([cat, items]) => (
          <div key={cat}>
            <div className="flex items-center gap-2 px-4 py-2 bg-gray-50 border-b border-border/40">
              <span className="size-1.5 rounded-full bg-gray-300 shrink-0" />
              <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-[0.07em]">
                {CATEGORY_LABELS[cat] ?? cat}
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
                  <span className={["shrink-0 mt-0.5 text-[10px] font-bold px-1.5 py-0.5 rounded", isError ? "bg-red-100 text-red-600" : "bg-amber-100 text-amber-600"].join(" ")}>
                    {isError ? "ERR" : "WARN"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm truncate ${isActive ? "font-semibold text-pkm-900" : "font-medium text-gray-800"}`}>
                      {FIELD_LABELS[issue.field ?? ""] ?? issue.field ?? CATEGORY_LABELS[issue.category] ?? issue.category}
                    </p>
                    <p className="text-[11px] text-gray-400 truncate mt-0.5 leading-tight">{issue.message}</p>
                  </div>
                  {(issue.occurrences?.length ?? 0) > 0 && (
                    <span className={["shrink-0 text-[11px] font-semibold px-1.5 py-0.5 rounded-full tabular-nums", isError ? "bg-red-100 text-red-600" : "bg-amber-100 text-amber-600"].join(" ")}>
                      {issue.occurrences!.length}×
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Sub-komponen: LocationPanel ──────────────────────────────────────────────

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
      <div className="flex-1 p-4 space-y-3 bg-gray-50/40">
        {occurrences.length > 0 ? (
          occurrences.map((occ, i) => (
            <OccurrenceCard key={`${occ.page}-${occ.para_idx}-${i}`} occ={occ} severity={issue.severity} />
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

// ─── Sub-komponen: PassedListPanel ────────────────────────────────────────────

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
                  <span className="shrink-0 mt-0.5 text-[10px] font-bold px-1.5 py-0.5 rounded bg-pkm-100 text-pkm-700">OK</span>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm truncate ${isActive ? "font-semibold text-pkm-900" : "font-medium text-gray-800"}`}>
                      {formatFieldLabel(check.field)}
                    </p>
                    <p className="text-[11px] text-gray-400 truncate mt-0.5 leading-tight">{check.message}</p>
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

// ─── Sub-komponen: PassedDetailPanel ─────────────────────────────────────────

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
      <div className="px-5 py-3.5 border-b border-border bg-white sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <span className="size-4 rounded-full bg-pkm-100 flex items-center justify-center shrink-0">
            <CheckCircleIcon className="size-3 text-pkm-600" />
          </span>
          <p className="text-sm font-semibold text-gray-800">{formatFieldLabel(check.field)}</p>
        </div>
        <p className="text-xs text-gray-400 mt-1 ml-6">{check.message}</p>
      </div>
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

// ─── Sub-komponen: ValidationResultView ──────────────────────────────────────
// Menampilkan hasil validasi satu dokumen (sama seperti tampilan lama).

function ValidationResultView({ result }: { result: ValidationResult }) {
  const [viewMode, setViewMode]           = useState<"error" | "warning" | "passed">(
    result.valid ? "passed" : "error"
  )
  const [selectedIssueIdx, setSelectedIssueIdx] = useState<number | null>(null)
  const [selectedCheckIdx, setSelectedCheckIdx] = useState<number | null>(null)

  const allIssues = result.issues ?? []
  const filteredIssues = viewMode === "error"
    ? allIssues.filter((i) => i.severity === "error")
    : viewMode === "warning"
    ? allIssues.filter((i) => i.severity === "warning")
    : allIssues

  const passedChecks: ValidationCheck[] = Object.values(result.report ?? {})
    .flat()
    .filter((c) => c.status === "passed")

  return (
    <div>
      <div className="px-6 pb-4">
        {result.valid ? (
          <Alert className="border-pkm-100 bg-pkm-50">
            <CheckCircleIcon className="size-4 text-pkm-600" />
            <AlertTitle className="text-pkm-900">Dokumen Valid</AlertTitle>
            <AlertDescription className="text-pkm-700">
              Semua persyaratan format terpenuhi.
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

      <div className="border-t border-border">
        <SummaryBar
          result={result}
          viewMode={viewMode}
          onErrorClick={() => { setViewMode("error"); setSelectedIssueIdx(null) }}
          onWarningClick={() => { setViewMode((m) => m === "warning" ? "error" : "warning"); setSelectedIssueIdx(null) }}
          onPassedClick={() => { setViewMode((m) => m === "passed" ? "error" : "passed"); setSelectedCheckIdx(null) }}
        />
        <div className="grid grid-cols-[300px_1fr] border-t border-border overflow-hidden" style={{ height: 680 }}>
          {viewMode === "passed" ? (
            <>
              <PassedListPanel checks={passedChecks} selectedIdx={selectedCheckIdx} onSelect={setSelectedCheckIdx} />
              <PassedDetailPanel check={selectedCheckIdx !== null ? passedChecks[selectedCheckIdx] : null} />
            </>
          ) : (
            <>
              <IssueListPanel issues={filteredIssues} selectedIdx={selectedIssueIdx} onSelect={setSelectedIssueIdx} />
              <LocationPanel issue={selectedIssueIdx !== null ? filteredIssues[selectedIssueIdx] : null} />
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Sub-komponen: BulkItemForm ───────────────────────────────────────────────

function BulkItemForm({
  item,
  index,
  onUpdate,
  onRemove,
  canRemove,
  disabled,
}: {
  item:     BulkItem
  index:    number
  onUpdate: (id: string, changes: Partial<BulkItem>) => void
  onRemove: (id: string) => void
  canRemove: boolean
  disabled: boolean
}) {
  const [isDragging, setIsDragging] = useState(false)

  const applyFile = useCallback((f: File) => {
    const err = validateDocxFile(f)
    if (err) {
      onUpdate(item.id, { fileError: err })
    } else {
      onUpdate(item.id, { file: f, fileError: null })
    }
  }, [item.id, onUpdate])

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) applyFile(f)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const f = e.dataTransfer.files?.[0]
    if (f) applyFile(f)
  }

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      {/* Header — klik untuk collapse/expand */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => onUpdate(item.id, { collapsed: !item.collapsed })}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
      >
        <div className="flex items-center gap-2 min-w-0">
          {item.collapsed
            ? <ChevronRightIcon className="size-4 text-gray-400 shrink-0" />
            : <ChevronDownIcon  className="size-4 text-gray-400 shrink-0" />
          }
          <span className="text-sm font-semibold text-gray-700">Dokumen ke {index + 1}</span>
          {item.file && (
            <span className="text-xs text-gray-400 truncate hidden sm:block">— {item.file.name}</span>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {/* Status indikator */}
          {item.file && item.schemaId && item.year ? (
            <span className="size-2 rounded-full bg-pkm-500" title="Siap divalidasi" />
          ) : (
            <span className="size-2 rounded-full bg-gray-300" title="Belum lengkap" />
          )}
          {canRemove && (
            <button
              type="button"
              disabled={disabled}
              onClick={(e) => { e.stopPropagation(); onRemove(item.id) }}
              className="p-1 rounded text-gray-400 hover:text-destructive hover:bg-red-50 transition-colors"
              title="Hapus dokumen ini"
            >
              <TrashIcon className="size-3.5" />
            </button>
          )}
        </div>
      </button>

      {/* Body — hanya tampil kalau tidak collapsed */}
      {!item.collapsed && (
        <div className="p-4 border-t border-border space-y-4">
          <div className="grid grid-cols-2 gap-3">
            {/* Schema */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-gray-600">Skema PKM</label>
              <Select
                value={item.schemaId}
                onValueChange={(v) => onUpdate(item.id, { schemaId: v })}
                disabled={disabled}
              >
                <SelectTrigger className="h-9 text-sm">
                  <SelectValue placeholder="Pilih skema" />
                </SelectTrigger>
                <SelectContent>
                  {PKM_SCHEMES.map((s) => (
                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Tahun */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-gray-600">Tahun</label>
              <YearPicker
                value={item.year}
                onChange={(v) => onUpdate(item.id, { year: v })}
                placeholder="Pilih tahun"
                disabled={disabled}
              />
            </div>
          </div>

          {/* Upload file */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-gray-600">File Proposal (.docx)</label>
            <div
              className={[
                "relative rounded-lg border-2 border-dashed p-4 transition-colors",
                isDragging
                  ? "border-primary bg-primary/10"
                  : item.file
                  ? "border-primary bg-primary/5"
                  : "border-muted-foreground/25 hover:border-muted-foreground/50",
              ].join(" ")}
              onDrop={handleDrop}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
              onDragLeave={() => setIsDragging(false)}
            >
              <input
                type="file"
                accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={handleFileInput}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                disabled={disabled}
              />
              <div className="flex items-center gap-3">
                {item.file ? (
                  <>
                    <FileTextIcon className="size-6 text-primary shrink-0" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{item.file.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {(item.file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); onUpdate(item.id, { file: null, fileError: null }) }}
                      className="ml-auto text-xs text-destructive hover:underline shrink-0"
                    >
                      Hapus
                    </button>
                  </>
                ) : (
                  <>
                    <UploadIcon className="size-6 text-muted-foreground shrink-0" />
                    <div>
                      <p className="text-sm text-muted-foreground">Seret atau klik untuk pilih file</p>
                      <p className="text-xs text-muted-foreground">DOCX, maks 10MB</p>
                    </div>
                  </>
                )}
              </div>
            </div>
            {item.fileError && (
              <p className="text-xs text-destructive">{item.fileError}</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Sub-komponen: JobProgressRow ─────────────────────────────────────────────

function JobProgressRow({ item }: { item: JobItemStatus }) {
  const { ketua, scheme } = parseFileName(item.file_name)

  const statusConfig = {
    pending:    { icon: "○", color: "text-gray-400", label: "Menunggu" },
    processing: { icon: "⟳", color: "text-amber-500 animate-spin", label: "Sedang diproses..." },
    completed:  { icon: "✓", color: "text-pkm-600", label: "Selesai" },
    failed:     { icon: "✗", color: "text-red-500",  label: "Gagal" },
  }[item.status]

  return (
    <div className="flex items-center gap-3 px-4 py-2.5 border-b border-border/40 last:border-0">
      <span className={`text-base font-bold shrink-0 ${statusConfig.color}`}>
        {statusConfig.icon}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800 truncate">
          {ketua} — {scheme || item.schema_id}
        </p>
        <p className="text-xs text-gray-400 truncate">{item.file_name}</p>
      </div>
      <span className={`text-xs font-medium shrink-0 ${statusConfig.color}`}>
        {item.status === "processing" ? "Memvalidasi..." : statusConfig.label}
      </span>
    </div>
  )
}

// ─── Sub-komponen: DocSelectorTab ─────────────────────────────────────────────

function DocSelectorTab({
  items,
  selectedIdx,
  onSelect,
}: {
  items: JobItemStatus[]
  selectedIdx: number
  onSelect: (idx: number) => void
}) {
  return (
    <div className="px-6 pt-4 pb-2">
      <p className="text-xs font-medium text-gray-500 mb-2">Pilih dokumen untuk melihat hasil:</p>
      <div className="flex flex-wrap gap-2">
        {items.map((item, idx) => {
          const { ketua, scheme } = parseFileName(item.file_name)
          const isActive = selectedIdx === idx
          const statusDot = {
            completed:  "bg-pkm-500",
            failed:     "bg-red-500",
            processing: "bg-amber-400",
            pending:    "bg-gray-300",
          }[item.status]

          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelect(idx)}
              disabled={item.status !== "completed" && item.status !== "failed"}
              className={[
                "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-colors",
                isActive
                  ? "bg-pkm-600 text-white border-pkm-600"
                  : item.status === "completed" || item.status === "failed"
                  ? "bg-white text-gray-700 border-border hover:border-pkm-400 hover:text-pkm-700"
                  : "bg-gray-50 text-gray-400 border-border cursor-not-allowed",
              ].join(" ")}
            >
              <span className={`size-1.5 rounded-full shrink-0 ${statusDot}`} />
              {ketua}
              {scheme ? ` — ${scheme}` : ""}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ─── Komponen utama: DocumentValidator ───────────────────────────────────────

export function DocumentValidator() {

  // ── Mode: single (default) atau bulk ─────────────────────────────────────
  const [mode, setMode] = useState<"single" | "bulk">("single")

  // ── State mode single ─────────────────────────────────────────────────────
  const [selectedSchemaId, setSelectedSchemaId] = useState<string>("")
  const [selectedYear, setSelectedYear]         = useState<string>("")
  const [file, setFile]                         = useState<File | null>(null)
  const [loading, setLoading]                   = useState(false)
  const [singleResult, setSingleResult]         = useState<ValidationResult | null>(null)
  const [singleError, setSingleError]           = useState<string | null>(null)

  // ── State mode bulk — form ────────────────────────────────────────────────
  const [bulkItems, setBulkItems] = useState<BulkItem[]>([makeBulkItem()])
  const [bulkSubmitting, setBulkSubmitting] = useState(false)
  const [bulkError, setBulkError]           = useState<string | null>(null)

  // ── State bulk — job tracking ─────────────────────────────────────────────
  const [jobId, setJobId]         = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null)
  const [isPolling, setIsPolling] = useState(false)
  const [selectedDocIdx, setSelectedDocIdx] = useState<number>(0)

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // ── Restore job dari localStorage saat mount ──────────────────────────────
  useEffect(() => {
    const saved = localStorage.getItem(JOB_STORAGE_KEY)
    if (saved) {
      setMode("bulk")
      setJobId(saved)
      setIsPolling(true)
    }
  }, [])

  // ── Polling status job ────────────────────────────────────────────────────
  useEffect(() => {
    if (!jobId || !isPolling) return

    const poll = async () => {
      const { data } = await checkJobStatus(jobId)
      if (data) {
        setJobStatus(data)
        if (data.status === "completed" || data.status === "failed") {
          setIsPolling(false)
          // Pilih otomatis dokumen pertama yang selesai
          const firstDone = data.items.findIndex((i) => i.status === "completed" || i.status === "failed")
          if (firstDone >= 0) setSelectedDocIdx(firstDone)
        }
      }
    }

    poll()
    pollingRef.current = setInterval(poll, POLL_INTERVAL_MS)
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [jobId, isPolling])

  // ── Handlers mode single ──────────────────────────────────────────────────

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (!selected) return
    const err = validateDocxFile(selected)
    if (err) { setSingleError(err); setFile(null); return }
    setSingleError(null)
    setFile(selected)
    setSingleResult(null)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const dropped = e.dataTransfer.files?.[0]
    if (dropped) handleFileChange({ target: { files: [dropped] } } as unknown as React.ChangeEvent<HTMLInputElement>)
  }, [handleFileChange])

  const handleDragOver = useCallback((e: React.DragEvent) => { e.preventDefault() }, [])

  const handleSingleValidate = async () => {
    if (!selectedSchemaId || !selectedYear || !file) {
      setSingleError("Pilih skema PKM, tahun, dan upload file proposal terlebih dahulu.")
      return
    }
    setLoading(true)
    setSingleError(null)
    setSingleResult(null)

    const res = await runDocumentValidation({ schemaId: selectedSchemaId, year: selectedYear, file })
    setLoading(false)

    if (res.error) setSingleError(res.error)
    else setSingleResult(res.data)
  }

  const handleSingleReset = () => {
    setSelectedSchemaId("")
    setSelectedYear("")
    setFile(null)
    setSingleResult(null)
    setSingleError(null)
  }

  // ── Handlers mode bulk ────────────────────────────────────────────────────

  const updateBulkItem = useCallback((id: string, changes: Partial<BulkItem>) => {
    setBulkItems((prev) => prev.map((item) => item.id === id ? { ...item, ...changes } : item))
  }, [])

  const removeBulkItem = useCallback((id: string) => {
    setBulkItems((prev) => prev.filter((item) => item.id !== id))
  }, [])

  const addBulkItem = () => {
    setBulkItems((prev) => [
      ...prev.map((item) => ({ ...item, collapsed: true })),
      makeBulkItem(),
    ])
  }

  const handleBulkValidate = async () => {
    // Validasi form: semua item harus lengkap
    const hasEmpty = bulkItems.some((item) => !item.schemaId || !item.year || !item.file)
    if (hasEmpty) {
      setBulkError("Semua dokumen harus memiliki skema, tahun, dan file yang dipilih.")
      // Expand item yang belum lengkap
      setBulkItems((prev) =>
        prev.map((item) => ({
          ...item,
          collapsed: !!(item.schemaId && item.year && item.file),
        }))
      )
      return
    }
    const hasFileError = bulkItems.some((item) => item.fileError)
    if (hasFileError) {
      setBulkError("Ada file yang tidak valid. Periksa kembali file yang diupload.")
      return
    }

    setBulkSubmitting(true)
    setBulkError(null)

    const res = await runBulkValidation(
      bulkItems.map((item) => ({
        schemaId: item.schemaId,
        year:     item.year,
        file:     item.file!,
      }))
    )

    setBulkSubmitting(false)

    if (res.error) {
      setBulkError(res.error)
      return
    }

    const newJobId = res.data!.job_id
    localStorage.setItem(JOB_STORAGE_KEY, newJobId)
    setJobId(newJobId)
    setJobStatus(null)
    setSelectedDocIdx(0)
    setIsPolling(true)
  }

  const handleClearJob = () => {
    if (pollingRef.current) clearInterval(pollingRef.current)
    localStorage.removeItem(JOB_STORAGE_KEY)
    setJobId(null)
    setJobStatus(null)
    setIsPolling(false)
    setSelectedDocIdx(0)
    setBulkItems([makeBulkItem()])
    setBulkError(null)
  }

  const switchToSingle = () => {
    setMode("single")
    handleSingleReset()
  }

  const switchToBulk = () => {
    setMode("bulk")
    setSingleResult(null)
    setSingleError(null)
  }

  // ── Render: mode single ───────────────────────────────────────────────────

  const renderSingleMode = () => (
    <>
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
                    onClick={(e) => { e.stopPropagation(); handleSingleReset() }}
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
            onClick={handleSingleValidate}
            disabled={!selectedSchemaId || !selectedYear || !file || loading}
            className="flex-1 sm:flex-none"
          >
            {loading ? (
              <><Loader2Icon className="size-4 animate-spin" /><span>Memvalidasi...</span></>
            ) : (
              <><CheckCircleIcon className="size-4" /><span>Validasi Dokumen</span></>
            )}
          </Button>
          <Button variant="outline" onClick={switchToBulk} disabled={loading} className="gap-1.5">
            <LayersIcon className="size-4" />
            Upload Sekaligus
          </Button>
          {singleResult && <Button variant="outline" onClick={handleSingleReset}>Reset</Button>}
        </div>

        {singleError && (
          <Alert variant="destructive">
            <AlertCircleIcon className="size-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{singleError}</AlertDescription>
          </Alert>
        )}
      </div>

      {/* Hasil validasi mode single */}
      {singleResult && <ValidationResultView result={singleResult} />}
    </>
  )

  // ── Render: mode bulk — form (belum ada job aktif) ────────────────────────

  const renderBulkForm = () => (
    <div className="px-6 pb-6 space-y-3">
      {bulkItems.map((item, idx) => (
        <BulkItemForm
          key={item.id}
          item={item}
          index={idx}
          onUpdate={updateBulkItem}
          onRemove={removeBulkItem}
          canRemove={bulkItems.length > 1}
          disabled={bulkSubmitting}
        />
      ))}

      {bulkError && (
        <Alert variant="destructive">
          <AlertCircleIcon className="size-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{bulkError}</AlertDescription>
        </Alert>
      )}

      <div className="flex items-center gap-3 pt-1">
        <Button
          variant="outline"
          onClick={addBulkItem}
          disabled={bulkSubmitting || bulkItems.length >= 20}
          className="gap-1.5"
        >
          <PlusIcon className="size-4" />
          Tambah Dokumen
        </Button>
        <Button
          onClick={handleBulkValidate}
          disabled={bulkSubmitting}
          className="gap-1.5"
        >
          {bulkSubmitting ? (
            <><Loader2Icon className="size-4 animate-spin" /><span>Mengirim...</span></>
          ) : (
            <><CheckCircleIcon className="size-4" /><span>Validasi Semua</span></>
          )}
        </Button>
        <Button
          variant="ghost"
          onClick={switchToSingle}
          disabled={bulkSubmitting}
          className="ml-auto text-xs text-muted-foreground"
        >
          ← Validasi Satu Dokumen
        </Button>
      </div>
    </div>
  )

  // ── Render: mode bulk — progress + hasil ─────────────────────────────────

  const renderBulkProgress = () => {
    const isDone    = jobStatus?.status === "completed" || jobStatus?.status === "failed"
    const items     = jobStatus?.items ?? []
    const total     = jobStatus?.total_items     ?? 0
    const completed = jobStatus?.completed_items ?? 0
    const selectedItem = items[selectedDocIdx]

    return (
      <div className="pb-6">
        {/* Progress header */}
        <div className="px-6 pb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">
              {isDone
                ? `Selesai — ${completed} dari ${total} dokumen diproses`
                : `Memvalidasi ${total} dokumen... (${completed}/${total})`
              }
            </span>
            {isDone && (
              <Button variant="outline" size="sm" onClick={handleClearJob}>
                Validasi Baru
              </Button>
            )}
          </div>

          {/* Progress bar */}
          {!isDone && (
            <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-pkm-500 rounded-full transition-all duration-500"
                style={{ width: total > 0 ? `${(completed / total) * 100}%` : "0%" }}
              />
            </div>
          )}
        </div>

        {/* Daftar progress per dokumen */}
        <div className="border-y border-border bg-white">
          {items.map((item) => (
            <JobProgressRow key={item.id} item={item} />
          ))}
          {items.length === 0 && (
            <div className="flex items-center justify-center py-6 gap-2 text-gray-400">
              <Loader2Icon className="size-4 animate-spin" />
              <span className="text-sm">Menghubungkan ke server...</span>
            </div>
          )}
        </div>

        {/* Hasil per dokumen (muncul setelah ada yang selesai) */}
        {items.some((i) => i.status === "completed" || i.status === "failed") && (
          <>
            {/* Tab pilih dokumen */}
            <DocSelectorTab
              items={items}
              selectedIdx={selectedDocIdx}
              onSelect={(idx) => setSelectedDocIdx(idx)}
            />

            {/* Hasil dokumen yang dipilih */}
            {selectedItem && (
              <div className="mt-2">
                {selectedItem.status === "completed" && selectedItem.result ? (
                  <ValidationResultView result={selectedItem.result as ValidationResult} />
                ) : selectedItem.status === "failed" ? (
                  <div className="px-6">
                    <Alert variant="destructive">
                      <AlertCircleIcon className="size-4" />
                      <AlertTitle>Validasi Gagal</AlertTitle>
                      <AlertDescription>
                        {selectedItem.error_message ?? "Terjadi kesalahan saat memvalidasi dokumen ini."}
                      </AlertDescription>
                    </Alert>
                  </div>
                ) : null}
              </div>
            )}
          </>
        )}
      </div>
    )
  }

  // ── Render utama ──────────────────────────────────────────────────────────

  return (
    <ReviewerSurfaceCard>
      {/* Header */}
      <div className="px-6 pt-6 pb-4">
        <h3 className="text-base font-semibold flex items-center gap-2">
          <FileTextIcon className="size-5 text-primary" />
          Validasi Dokumen Otomatis
        </h3>
      </div>

      {/* Konten berdasarkan mode */}
      {mode === "single"
        ? renderSingleMode()
        : jobId
        ? renderBulkProgress()
        : renderBulkForm()
      }
    </ReviewerSurfaceCard>
  )
}
