"use client"

import { useState, useRef, useEffect } from "react"
import {
  AdminPageHeader,
  AdminSurfaceCard,
} from "@/components/admin/shared"
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
import { DocumentIcon, FileTextIcon, UploadIcon, CheckCircleIcon, AlertCircleIcon, Loader2Icon } from "@/components/icons/public-icons"

// Types
type ProjectStatus = "pending" | "uploading" | "extracting" | "extracted" | "generating" | "completed" | "failed"

type ProjectResponse = {
  data: {
    id: string
    skema: string
    tahun: string
    judul: string
    source_file: string | null
    source_url: string | null
    status: ProjectStatus
    error_message: string | null
    result_url: string | null
    created_at: string
    updated_at: string
  }
  message?: string
}

type DocumentResult = {
  projectId: string
  fileName: string
  title: string
  skema: string
  tahun: string
  sourceUrl: string | null
  resultUrl: string | null
  status: ProjectStatus
  errorMessage: string | null
  createdAt: string
}

const PKM_SCHEMES = [
  { value: "pkm-volid", label: "PKM Vokasi" },
  { value: "pkm-kc", label: "PKM Karsa Ceatera (KC)" },
  { value: "pkm-penelitian", label: "PKM Penelitian" },
  { value: "pkm-artikel", label: "PKM Artikel Ilmiah" },
  { value: "pkm-gtk", label: "PKM Griefing dan Teknologi Tepat Guna" },
  { value: "pkm-mbkm", label: "PKM MBKM" },
]

const YEARS = Array.from({ length: 5 }, (_, i) => {
  const year = new Date().getFullYear() + 1 - i
  return { value: String(year), label: String(year) }
})

export default function ProposalDocumentPage() {
  const [title, setTitle] = useState("")
  const [skema, setSkema] = useState("")
  const [tahun, setTahun] = useState("")
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [result, setResult] = useState<DocumentResult | null>(null)
  const [currentProjectId, setCurrentProjectId] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Status polling effect
  useEffect(() => {
    if (!currentProjectId) return
    if (result && result.status === "completed") return
    if (result && result.status === "failed") return

    const pollStatus = async () => {
      try {
        const response = await fetch(`/api/projects/${currentProjectId}`)
        if (!response.ok) return

        const data: ProjectResponse = await response.json()
        const project = data.data

        setResult((prev) => prev ? {
          ...prev,
          status: project.status,
          resultUrl: project.result_url,
          errorMessage: project.error_message,
        } : null)

        // Stop polling if completed or failed
        if (project.status === "completed" || project.status === "failed") {
          setIsUploading(false)
        }
      } catch (error) {
        console.error("Error polling status:", error)
      }
    }

    // Poll every 3 seconds
    const interval = setInterval(pollStatus, 3000)
    return () => clearInterval(interval)
  }, [currentProjectId, result?.status])

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      setUploadError(null)
    }
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault()
    const file = event.dataTransfer.files?.[0]
    if (file && (file.type === "application/vnd.openxmlformats-officedocument.wordprocessingml.document" || file.type === "application/pdf")) {
      setSelectedFile(file)
      setUploadError(null)
    } else {
      setUploadError("Hanya file DOCX dan PDF yang diizinkan.")
    }
  }

  function handleDragOver(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault()
  }

  function handleRemoveFile() {
    setSelectedFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!title.trim()) {
      setUploadError("Judul proposal wajib diisi.")
      return
    }

    if (!skema) {
      setUploadError("Skema PKM wajib dipilih.")
      return
    }

    if (!tahun) {
      setUploadError("Tahun wajib dipilih.")
      return
    }

    if (!selectedFile) {
      setUploadError("File proposal wajib diupload.")
      return
    }

    setIsUploading(true)
    setUploadError(null)
    setUploadProgress(0)
    setResult(null)

    try {
      // Step 1: Create project and get signed upload URL
      setUploadProgress(10)
      const formData = new FormData()
      formData.append("skema", skema)
      formData.append("tahun", tahun)
      formData.append("judul", title.trim())
      formData.append("file_name", selectedFile.name)

      const response = await fetch("/api/projects", {
        method: "PUT",
        body: JSON.stringify({
          bucket: "ai-source-files",
          projectId: "new",
          fileName: selectedFile.name,
        }),
        headers: {
          "Content-Type": "application/json",
        },
      })

      setUploadProgress(20)

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(errorText || "Gagal membuat project")
      }

      const data = await response.json()
      const { project_id, signed_url } = data.data

      if (!signed_url) {
        throw new Error("Tidak dapat membuat signed URL")
      }

      // Step 2: Upload file directly to Supabase Storage using signed URL
      setUploadProgress(40)

      const uploadResponse = await fetch(signed_url, {
        method: "PUT",
        body: selectedFile,
        headers: {
          "Content-Type": selectedFile.type || "application/octet-stream",
        },
      })

      if (!uploadResponse.ok) {
        throw new Error("Gagal upload file ke Supabase Storage")
      }

      setUploadProgress(80)

      // Initialize result state
      setCurrentProjectId(project_id)
      setResult({
        projectId: project_id,
        fileName: selectedFile.name,
        title: title.trim(),
        skema: PKM_SCHEMES.find(s => s.value === skema)?.label ?? skema,
        tahun: tahun,
        sourceUrl: null,
        resultUrl: null,
        status: "pending",
        errorMessage: null,
        createdAt: new Date().toISOString(),
      })

      setUploadProgress(100)
    } catch (error) {
      console.error("Error creating project:", error)
      setUploadError(error instanceof Error ? error.message : "Terjadi kesalahan saat membuat dokumen")
      setIsUploading(false)
      setResult(null)
    }
  }

  function handleReset() {
    setTitle("")
    setSkema("")
    setTahun("")
    setSelectedFile(null)
    setResult(null)
    setCurrentProjectId(null)
    setUploadProgress(0)
    setUploadError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  function getStatusLabel(status: ProjectStatus): string {
    switch (status) {
      case "pending": return "Menunggu..."
      case "uploading": return "Mengupload file..."
      case "extracting": return "Mengekstrak konten..."
      case "extracted": return "Ekstraksi selesai"
      case "generating": return "Menghasilkan dokumen..."
      case "completed": return "Selesai"
      case "failed": return "Gagal"
      default: return status
    }
  }

  function getStatusColor(status: ProjectStatus): string {
    switch (status) {
      case "completed": return "text-green-600 bg-green-50 border-green-200"
      case "failed": return "text-red-600 bg-red-50 border-red-200"
      case "extracting":
      case "generating":
      case "uploading": return "text-amber-600 bg-amber-50 border-amber-200"
      default: return "text-gray-600 bg-gray-50 border-gray-200"
    }
  }

  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  function formatDateTime(isoString: string): string {
    const date = new Date(isoString)
    return date.toLocaleString("id-ID", {
      day: "numeric",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })
  }

  return (
    <div className="px-8 py-8">
      <AdminPageHeader
        title="Buat Dokumen Proposal"
        description="Upload dokumen proposal PKM untuk diproses dan divisualisasikan"
      />

      {!result ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <AdminSurfaceCard>
            <div className="border-b border-gray-100 px-5 py-4">
              <h2 className="text-sm font-semibold text-gray-700">Form Upload</h2>
              <p className="mt-0.5 text-xs text-[rgba(0,0,0,0.4)]">
                Masukkan judul dan upload file proposal
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5 px-5 py-5">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="proposal-skema" className="text-xs font-medium text-gray-600">
                    Skema PKM
                  </Label>
                  <Select value={skema || undefined} onValueChange={setSkema} disabled={isUploading}>
                    <SelectTrigger>
                      <SelectValue placeholder="Pilih skema" />
                    </SelectTrigger>
                    <SelectContent>
                      {PKM_SCHEMES.map((s) => (
                        <SelectItem key={s.value} value={s.value}>
                          {s.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="proposal-tahun" className="text-xs font-medium text-gray-600">
                    Tahun
                  </Label>
                  <Select value={tahun || undefined} onValueChange={setTahun} disabled={isUploading}>
                    <SelectTrigger>
                      <SelectValue placeholder="Pilih tahun" />
                    </SelectTrigger>
                    <SelectContent>
                      {YEARS.map((y) => (
                        <SelectItem key={y.value} value={y.value}>
                          {y.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="proposal-title" className="text-xs font-medium text-gray-600">
                  Judul Proposal
                </Label>
                <Input
                  id="proposal-title"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="cth. Analisis Perbandingan Algoritma Sorting"
                  disabled={isUploading}
                />
                <p className="text-xs text-gray-400">Masukkan judul proposal yang akan diproses</p>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-medium text-gray-600">Buku Panduan PKM (sesuai skema yang dipilih)</Label>

                {!selectedFile ? (
                  <div
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    className={`relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
                      isUploading
                        ? "cursor-not-allowed border-gray-200 bg-gray-50"
                        : "cursor-pointer border-gray-200 bg-gray-50/50 hover:border-pkm-200 hover:bg-pkm-50/30"
                    }`}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".docx,.pdf"
                      onChange={handleFileChange}
                      disabled={isUploading}
                      className="absolute inset-0 cursor-pointer opacity-0"
                    />
                    <div className="flex size-12 items-center justify-center rounded-full bg-pkm-100">
                      <UploadIcon className="size-5 text-pkm-700" />
                    </div>
                    <p className="mt-3 text-sm font-medium text-gray-700">
                      Drop file di sini atau klik untuk upload
                    </p>
                    <p className="mt-1 text-xs text-gray-400">
                      Mendukung file DOCX dan PDF
                    </p>
                  </div>
                ) : (
                  <div className="flex items-center gap-3 rounded-xl border border-gray-100 bg-gray-50/50 px-4 py-3">
                    <div className="flex size-10 items-center justify-center rounded-lg bg-pkm-100">
                      <FileTextIcon className="size-5 text-pkm-700" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">{selectedFile.name}</p>
                      <p className="text-xs text-gray-400">{formatFileSize(selectedFile.size)}</p>
                    </div>
                    {!isUploading && (
                      <button
                        type="button"
                        onClick={handleRemoveFile}
                        className="flex-shrink-0 rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                      >
                        <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    )}
                  </div>
                )}
              </div>

              {uploadError ? (
                <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {uploadError}
                </div>
              ) : null}

              {isUploading && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">Mengupload dan memproses...</span>
                    <span className="font-medium text-pkm-700">{uploadProgress}%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-gray-100">
                    <div
                      className="h-full rounded-full bg-pkm-500 transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleReset}
                  disabled={isUploading || (!title && !selectedFile && !skema && !tahun)}
                >
                  Reset
                </Button>
                <Button type="submit" disabled={isUploading || !title || !selectedFile || !skema || !tahun}>
                  {isUploading ? "Memproses..." : "Buat Dokumen"}
                </Button>
              </div>
            </form>
          </AdminSurfaceCard>

          <AdminSurfaceCard>
            <div className="flex h-full items-center justify-center px-5 py-12">
              <div className="text-center">
                <div className="mx-auto flex size-16 items-center justify-center rounded-full bg-gray-100">
                  <DocumentIcon className="size-8 text-gray-400" />
                </div>
                <h3 className="mt-4 text-sm font-medium text-gray-700">Preview Dokumen</h3>
                <p className="mt-1 text-xs text-gray-400">
                  Dokumen yang sudah diproses akan muncul di sini
                </p>
              </div>
            </div>
          </AdminSurfaceCard>
        </div>
      ) : (
        <div className="grid gap-6">
          <AdminSurfaceCard>
            <div className="flex items-center gap-4 border-b border-gray-100 px-5 py-4">
              <div className={`flex size-12 items-center justify-center rounded-full ${
                result.status === "completed"
                  ? "bg-green-100"
                  : result.status === "failed"
                    ? "bg-red-100"
                    : "bg-amber-100"
              }`}>
                {result.status === "completed" ? (
                  <CheckCircleIcon className="size-6 text-green-600" />
                ) : result.status === "failed" ? (
                  <AlertCircleIcon className="size-6 text-red-600" />
                ) : (
                  <Loader2Icon className="size-6 text-amber-600 animate-spin" />
                )}
              </div>
              <div>
                <h2 className="text-base font-semibold text-gray-800">
                  {result.status === "completed"
                    ? "Dokumen Berhasil Dibuat"
                    : result.status === "failed"
                      ? "Dokumen Gagal Diproses"
                      : "Memproses Dokumen..."}
                </h2>
                <p className="mt-0.5 text-sm text-gray-500">
                  {result.status === "completed"
                    ? `Proposal "${result.title}" telah berhasil diproses`
                    : result.status === "failed"
                      ? result.errorMessage || "Terjadi kesalahan saat memproses dokumen"
                      : getStatusLabel(result.status)}
                </p>
              </div>
            </div>

            <div className="px-5 py-5">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-xl border border-gray-100 bg-gray-50/50 p-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Skema</p>
                  <p className="mt-1 text-sm font-medium text-gray-800">{result.skema}</p>
                </div>
                <div className="rounded-xl border border-gray-100 bg-gray-50/50 p-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Tahun</p>
                  <p className="mt-1 text-sm font-medium text-gray-800">{result.tahun}</p>
                </div>
                <div className="rounded-xl border border-gray-100 bg-gray-50/50 p-4 sm:col-span-2">
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Judul</p>
                  <p className="mt-1 text-sm font-medium text-gray-800">{result.title}</p>
                </div>
              </div>

              <div className="mt-4 rounded-xl border border-gray-100 bg-gray-50/50 p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Nama File</p>
                <p className="mt-1 text-sm font-medium text-gray-800">{result.fileName}</p>
              </div>

              <div className={`mt-4 flex items-center justify-between rounded-xl border px-4 py-3 ${getStatusColor(result.status)}`}>
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide">Status</p>
                  <p className="mt-0.5 text-sm font-semibold">{getStatusLabel(result.status)}</p>
                </div>
                {result.status === "completed" ? (
                  <CheckCircleIcon className="size-6 text-green-600" />
                ) : result.status === "failed" ? (
                  <AlertCircleIcon className="size-6 text-red-600" />
                ) : (
                  <Loader2Icon className="size-6 animate-spin" />
                )}
              </div>

              {result.status === "completed" && (
                <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                  <a
                    href={result.resultUrl || "#"}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center justify-center gap-2 rounded-md border border-input background-border bg-background px-4 py-2 text-sm font-medium ring-offset-background transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 flex-1"
                  >
                    <DocumentIcon className="size-4" />
                    Lihat Dokumen Proposal
                  </a>
                  <Button variant="outline" className="flex-1 gap-2">
                    <FileTextIcon className="size-4" />
                    Lihat Penilaian
                  </Button>
                </div>
              )}

              {result.status === "failed" && (
                <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4">
                  <p className="text-sm text-red-700">
                    <strong>Error:</strong> {result.errorMessage || "Terjadi kesalahan yang tidak diketahui"}
                  </p>
                </div>
              )}

              <div className="mt-5 flex justify-end">
                <Button onClick={handleReset} variant="outline">
                  {result.status === "completed" ? "Buat Dokumen Baru" : "Batal"}
                </Button>
              </div>
            </div>
          </AdminSurfaceCard>
        </div>
      )}
    </div>
  )
}
