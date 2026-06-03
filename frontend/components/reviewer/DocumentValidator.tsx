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
import { runDocumentValidation, type ValidationResult } from "@/lib/api/pkm"
import { PKM_SCHEMES } from "@/lib/constants/pkm-schemes"
import { YearPicker } from "@/components/ui/year-picker"

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

export function DocumentValidator() {
  const [selectedSchemaId, setSelectedSchemaId] = useState<string>("")
  const [selectedYear, setSelectedYear] = useState<string>("")
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ValidationResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (selected) {
      if (selected.size > MAX_FILE_SIZE) {
        setError(`Ukuran file terlalu besar. Maksimal 10MB.`)
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
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const dropped = e.dataTransfer.files?.[0]
    if (dropped) {
      const fakeEvent = {
        target: { files: [dropped] },
      } as unknown as React.ChangeEvent<HTMLInputElement>
      handleFileChange(fakeEvent)
    }
  }, [handleFileChange])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
  }, [])

  // Pipeline validasi (dipanggil saat tombol "Validasi Dokumen" ditekan):
  //   Frontend → POST /api/pkm/validation/run (Express proxy)
  //   → POST /api/validation/run (FastAPI ai-backend)
  //   → validator.py: validocx_adapter → validocx_runner → ValidationResult
  //   → Result dikembalikan sebagai JSON { valid, status, issues, checks, summary }
  const handleValidate = async () => {
    if (!selectedSchemaId || !selectedYear || !file) {
      setError("Pilih skema PKM, tahun, dan upload file proposal terlebih dahulu.")
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    const res = await runDocumentValidation({
      schemaId: selectedSchemaId,
      year: selectedYear,
      file,
    })

    setLoading(false)

    if (res.error) {
      setError(res.error)
    } else {
      // result.valid = true jika semua pengecekan lulus (status === "pass")
      // result.issues = array ValidationIssue dengan severity error/warning/info
      // result.summary = ringkasan jumlah passed/total checks
      setResult(res.data)
    }
  }

  const handleReset = () => {
    setSelectedSchemaId("")
    setSelectedYear("")
    setFile(null)
    setResult(null)
    setError(null)
  }

  return (
    <ReviewerSurfaceCard>
      <div className="px-6 pt-6 pb-4">
        <h3 className="text-base font-semibold flex items-center gap-2">
          <FileTextIcon className="size-5 text-primary" />
          Validasi Dokumen Otomatis
        </h3>
      </div>

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
                    onClick={(e) => {
                      e.stopPropagation()
                      setFile(null)
                      setResult(null)
                    }}
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
                  <p className="text-xs text-muted-foreground mt-1">
                    Format: DOCX, maks 10MB
                  </p>
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

        {result && (
          <div className="space-y-3">
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
                  {result.issues?.filter((i) => i.severity === "error").length ?? 0} error,{" "}
                  {result.issues?.filter((i) => i.severity === "warning").length ?? 0} peringatan ditemukan.
                </AlertDescription>
              </Alert>
            )}

            {result.issues && result.issues.length > 0 && (
              <div className="rounded-lg bg-gray-50">
                <div className="px-4 py-3 bg-gray-100 rounded-t-lg">
                  <h4 className="text-sm font-medium">
                    Detail Masalah ({result.issues.length})
                  </h4>
                </div>
                <div className="divide-y">
                  {result.issues.map((issue, idx) => (
                    <div key={idx} className="px-4 py-3 flex items-start gap-3">
                      <div
                        className={[
                          "shrink-0 size-5 rounded-full flex items-center justify-center text-xs font-medium mt-0.5",
                          issue.severity === "error"
                            ? "bg-red-100 text-red-700"
                            : issue.severity === "warning"
                            ? "bg-yellow-100 text-yellow-700"
                            : "bg-blue-100 text-blue-700",
                        ].join(" ")}
                      >
                        {issue.severity === "error" ? "!" : "i"}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                            {issue.category}
                          </span>
                          {issue.field && (
                            <span className="text-xs text-muted-foreground">· {issue.field}</span>
                          )}
                        </div>
                        <p className="text-sm">{issue.message}</p>
                        {(issue.expected || issue.actual) && (
                          <div className="mt-1 flex gap-3 text-xs text-muted-foreground">
                            {issue.expected && (
                              <span>
                                Diharapkan:{" "}
                                <span className="font-medium text-foreground">{issue.expected}</span>
                              </span>
                            )}
                            {issue.actual && (
                              <span>
                                Ditemukan:{" "}
                                <span className="font-medium text-foreground">{issue.actual}</span>
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </ReviewerSurfaceCard>
  )
}