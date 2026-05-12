"use client"

import { useCallback, useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
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
import { getPkmSchemas, runDocumentValidation, type ValidationResult, type PkmSchema } from "@/lib/api/pkm"

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

export function DocumentValidator() {
  const [schemas, setSchemas] = useState<PkmSchema[]>([])
  const [selectedSchemaId, setSelectedSchemaId] = useState<string>("")
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [schemasLoading, setSchemasLoading] = useState(true)
  const [schemasError, setSchemasError] = useState<string | null>(null)
  const [result, setResult] = useState<ValidationResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadSchemas() {
      const res = await getPkmSchemas()
      if (res.error) {
        setSchemasError(res.error)
      } else {
        setSchemas(res.data || [])
      }
      setSchemasLoading(false)
    }
    loadSchemas()
  }, [])

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (selected) {
      if (selected.size > MAX_FILE_SIZE) {
        setError(`Ukuran file terlalu besar. Maksimal 10MB.`)
        setFile(null)
        return
      }
      if (selected.type !== "application/pdf") {
        setError("Hanya file PDF yang diterima.")
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

  const handleValidate = async () => {
    if (!selectedSchemaId || !file) {
      setError("Pilih skema PKM dan upload file proposal terlebih dahulu.")
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    const res = await runDocumentValidation({
      schemaId: selectedSchemaId,
      file,
    })

    setLoading(false)

    if (res.error) {
      setError(res.error)
    } else {
      setResult(res.data)
    }
  }

  const handleReset = () => {
    setSelectedSchemaId("")
    setFile(null)
    setResult(null)
    setError(null)
  }

  return (
    <Card>
      <CardHeader className="pb-4">
        <CardTitle className="text-base flex items-center gap-2">
          <FileTextIcon className="size-5 text-primary" />
          Validasi Dokumen Otomatis
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4 pt-0">
        <div className="space-y-2">
          <label className="text-sm font-medium">1. Pilih Skema PKM</label>
          {schemasLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2Icon className="size-4 animate-spin" />
              Memuat skema...
            </div>
          ) : schemasError ? (
            <p className="text-sm text-destructive">{schemasError}</p>
          ) : (
            <Select value={selectedSchemaId} onValueChange={setSelectedSchemaId}>
              <SelectTrigger>
                <SelectValue placeholder="Pilih jenis PKM" />
              </SelectTrigger>
              <SelectContent>
                {schemas.map((schema) => (
                  <SelectItem key={schema.id} value={schema.id}>
                    {schema.nama} ({schema.singkatan})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">2. Upload Proposal</label>
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
              accept=".pdf,application/pdf"
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
                    Format: PDF, maks 10MB
                  </p>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            onClick={handleValidate}
            disabled={!selectedSchemaId || !file || loading}
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
                  Dokumen proposal telah memenuhi semua persyaratan validasi.
                </AlertDescription>
              </Alert>
            ) : (
              <Alert variant="destructive">
                <AlertCircleIcon className="size-4" />
                <AlertTitle>Ditemukan Masalah</AlertTitle>
                <AlertDescription>
                  Dokumen tidak memenuhi beberapa persyaratan.
                </AlertDescription>
              </Alert>
            )}

            {result.errors && result.errors.length > 0 && (
              <div className="rounded-lg border bg-card">
                <div className="px-4 py-3 border-b bg-muted/50">
                  <h4 className="text-sm font-medium">
                    Detail Masalah ({result.errors.length})
                  </h4>
                </div>
                <div className="divide-y">
                  {result.errors.map((err, idx) => (
                    <div key={idx} className="px-4 py-3 flex items-start gap-3">
                      <div
                        className={[
                          "shrink-0 size-5 rounded-full flex items-center justify-center text-xs font-medium",
                          err.severity === "error"
                            ? "bg-red-100 text-red-700"
                            : err.severity === "warning"
                            ? "bg-yellow-100 text-yellow-700"
                            : "bg-blue-100 text-blue-700",
                        ].join(" ")}
                      >
                        {err.severity === "error" ? "!" : "i"}
                      </div>
                      <div className="flex-1 min-w-0">
                        {err.field && (
                          <p className="text-xs font-medium text-muted-foreground mb-0.5">
                            {err.field}
                          </p>
                        )}
                        <p className="text-sm">{err.message}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          Rule: {err.rule}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}