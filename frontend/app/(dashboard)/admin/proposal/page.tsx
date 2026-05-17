"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { getSupabaseBrowserClient } from "@/lib/supabase/browser-client"
import {
  AdminPageHeader,
  AdminSurfaceCard,
} from "@/components/admin/shared"
import { Button } from "@/components/ui/button"
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
type ProjectStatus = "pending" | "uploading" | "extracting" | "extracted" | "generating" | "completed" | "failed" | "pending_upload"

type ProjectResponse = {
  data: {
    id: string
    skema: string
    tahun: string
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
  skema: string
  tahun: string
  sourceUrl: string | null
  resultUrl: string | null
  status: ProjectStatus
  errorMessage: string | null
  createdAt: string
}

type LogEntry = {
  id: number
  project_id: string
  step: string
  message: string
  timestamp: string
}

const ACTIVE_PROJECT_KEY = "proposal_active_project_id"
const RUN_SINCE_KEY = "proposal_run_since_id"

const PKM_SCHEMES = [
  { value: "pkm-re", label: "PKM-RE: Riset Eksakta" },
  { value: "pkm-rsh", label: "PKM-RSH: Riset Sosial Humaniora" },
  { value: "pkm-k", label: "PKM-K: Kewirausahaan" },
  { value: "pkm-pm", label: "PKM-PM: Pengabdian Kepada Masyarakat" },
  { value: "pkm-pi", label: "PKM-PI: Penerapan Iptek" },
  { value: "pkm-kc", label: "PKM-KC: Karsa Cipta" },
  { value: "pkm-ki", label: "PKM-KI: Karya Inovatif" },
  { value: "pkm-vgk", label: "PKM-VGK: Video Gagasan Konstruktif" },
  { value: "pkm-ai", label: "PKM-AI: Artikel Ilmiah" },
  { value: "pkm-gft", label: "PKM-GFT: Gagasan Futuristik Tertulis" },
]

const YEARS = Array.from({ length: 5 }, (_, i) => {
  const year = new Date().getFullYear() + 1 - i
  return { value: String(year), label: String(year) }
})

function isPdfFile(file: File): boolean {
  return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")
}

export default function ProposalDocumentPage() {
  const [skema, setSkema] = useState("")
  const [tahun, setTahun] = useState("")
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [result, setResult] = useState<DocumentResult | null>(null)
  const [currentProjectId, setCurrentProjectId] = useState<string | null>(null)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [isRestoring, setIsRestoring] = useState(true)
  const logsEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const maxLogIdRef = useRef<number>(0)
  const resultStatus = result?.status

  const applyStatusUpdate = useCallback((status: ProjectStatus, resultUrl: string | null, errorMessage: string | null) => {
    setResult((prev) =>
      prev ? { ...prev, status, resultUrl, errorMessage } : null
    )
    if (status === "completed" || status === "failed") {
      setIsUploading(false)
      localStorage.removeItem(ACTIVE_PROJECT_KEY)
      // Persist max log ID so next run starts filtering from here
      localStorage.setItem(RUN_SINCE_KEY, String(maxLogIdRef.current))
    }
  }, [])

  // Restore in-progress project on page load
  useEffect(() => {
    const savedId = localStorage.getItem(ACTIVE_PROJECT_KEY)
    if (!savedId) {
      setIsRestoring(false)
      return
    }

    fetch(`/api/projects/${savedId}`)
      .then((res) => res.json())
      .then((data) => {
        const project = data?.data
        if (!project) {
          localStorage.removeItem(ACTIVE_PROJECT_KEY)
          return
        }

        const status: ProjectStatus = project.status
        if (status === "completed" || status === "failed") {
          localStorage.removeItem(ACTIVE_PROJECT_KEY)
        }

        setCurrentProjectId(savedId)
        setResult({
          projectId: savedId,
          fileName: project.source_file ?? "",
          skema: PKM_SCHEMES.find((s) => s.value === project.skema)?.label ?? project.skema,
          tahun: project.tahun,
          sourceUrl: project.source_url,
          resultUrl: project.result_url,
          status,
          errorMessage: project.error_message,
          createdAt: project.created_at,
        })

        if (status !== "completed" && status !== "failed") {
          setIsUploading(true)
        }

        // Muat log dari run saat ini saja (filter by since_id)
        const sinceId = parseInt(localStorage.getItem(RUN_SINCE_KEY) || "0") || 0
        const sinceParam = sinceId > 0 ? `?since_id=${sinceId}` : ""
        fetch(`/api/projects/${savedId}/logs${sinceParam}`, {
          headers: { accept: "application/json" },
        })
          .then((r) => r.json())
          .then((logData) => {
            if (Array.isArray(logData?.data) && logData.data.length > 0) {
              const maxId = Math.max(...logData.data.map((l: LogEntry) => l.id))
              maxLogIdRef.current = maxId
              setLogs(logData.data)
            }
          })
          .catch(() => {})
      })
      .catch(() => {
        localStorage.removeItem(ACTIVE_PROJECT_KEY)
      })
      .finally(() => {
        setIsRestoring(false)
      })
  }, [])

  // Auto-scroll logs when new entries are added
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }, [logs])

  // Supabase Realtime — subscribe to project status changes
  useEffect(() => {
    if (!currentProjectId) return
    if (resultStatus === "completed" || resultStatus === "failed") return

    const supabase = getSupabaseBrowserClient()

    const channel = supabase
      .channel(`project-status-${currentProjectId}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "projects",
          filter: `id=eq.${currentProjectId}`,
        },
        (payload) => {
          const project = payload.new as {
            status: ProjectStatus
            result_url: string | null
            error_message: string | null
          }
          applyStatusUpdate(project.status, project.result_url, project.error_message)
        }
      )
      .subscribe(() => {
        // Setelah subscription established, fetch status terkini untuk menangkap
        // event yang mungkin terlewat selama jeda setup WebSocket.
        fetch(`/api/projects/${currentProjectId}`)
          .then((res) => res.json())
          .then((data) => {
            const project = data?.data
            if (!project) return
            applyStatusUpdate(project.status, project.result_url, project.error_message)
          })
          .catch(() => {})
      })

    return () => {
      supabase.removeChannel(channel)
    }
  }, [currentProjectId, resultStatus, applyStatusUpdate])


  // SSE log streaming effect
  useEffect(() => {
    if (!currentProjectId) return
    if (resultStatus === "completed" || resultStatus === "failed") return

    let eventSource: EventSource | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null

    const connectSSE = () => {
      const since = parseInt(localStorage.getItem(RUN_SINCE_KEY) || "0") || 0
      const sinceParam = since > 0 ? `?since_id=${since}` : ""
      eventSource = new EventSource(`/api/projects/${currentProjectId}/logs${sinceParam}`)

      eventSource.addEventListener("log", (event) => {
        try {
          const logEntry: LogEntry = JSON.parse(event.data)
          if (logEntry.id > maxLogIdRef.current) {
            maxLogIdRef.current = logEntry.id
          }
          setLogs((prev) => {
            // Dedup by ID — mencegah duplikat antara log historis (preload) dan SSE
            if (prev.some((l) => l.id === logEntry.id)) return prev
            return [...prev, logEntry]
          })
        } catch (error) {
          console.error("Error parsing log:", error)
        }
      })

      eventSource.addEventListener("status", (event) => {
        try {
          const project = JSON.parse(event.data)
          applyStatusUpdate(project.status, project.result_url, project.error_message)
        } catch (error) {
          console.error("Error parsing status event:", error)
        }
      })

      eventSource.onerror = () => {
        eventSource?.close()
        reconnectTimer = setTimeout(connectSSE, 3000)
      }
    }

    connectSSE()

    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer)
      eventSource?.close()
    }
  }, [currentProjectId, resultStatus, applyStatusUpdate])

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (file && isPdfFile(file)) {
      setSelectedFile(file)
      setUploadError(null)
      return
    }

    if (file) {
      setUploadError("Hanya file PDF yang diizinkan.")
    }
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault()
    const file = event.dataTransfer.files?.[0]
    if (file && isPdfFile(file)) {
      setSelectedFile(file)
      setUploadError(null)
    } else {
      setUploadError("Hanya file PDF yang diizinkan.")
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

    // Capture max log ID before clearing — used to filter old logs on next run
    const prevSinceId = parseInt(localStorage.getItem(RUN_SINCE_KEY) || "0") || 0
    const currentMaxId = logs.length > 0 ? Math.max(...logs.map(l => l.id)) : 0
    const runSinceId = Math.max(prevSinceId, currentMaxId)

    setIsUploading(true)
    setUploadError(null)
    setUploadProgress(0)
    setResult(null)
    setCurrentProjectId(null)
    setLogs([])

    try {
      // Step 1: Create project and get signed upload URL
      setUploadProgress(10)
      const formData = new FormData()
      formData.append("skema", skema)
      formData.append("tahun", tahun)
      formData.append("file_name", selectedFile.name)

      const response = await fetch("/api/projects", {
        method: "PUT",
        body: formData,
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

      setUploadProgress(75)

      // Step 3: Confirm upload so AI backend starts the pipeline
      const confirmFormData = new FormData()
      confirmFormData.append("project_id", project_id)
      confirmFormData.append("file_name", selectedFile.name)

      const confirmResponse = await fetch("/api/projects/confirm-upload", {
        method: "POST",
        body: confirmFormData,
      })

      setUploadProgress(90)

      if (!confirmResponse.ok) {
        const errorText = await confirmResponse.text()
        throw new Error(errorText || "Gagal mengonfirmasi upload file")
      }

      const confirmData: ProjectResponse = await confirmResponse.json()
      const confirmedProject = confirmData.data

      // Initialize result state — store since_id so SSE & restore only show this run's logs
      localStorage.setItem(RUN_SINCE_KEY, String(runSinceId))
      maxLogIdRef.current = runSinceId
      localStorage.setItem(ACTIVE_PROJECT_KEY, project_id)
      setCurrentProjectId(project_id)
      setResult({
        projectId: project_id,
        fileName: confirmedProject.source_file ?? selectedFile.name,
        skema: PKM_SCHEMES.find((scheme) => scheme.value === confirmedProject.skema)?.label ?? confirmedProject.skema,
        tahun: confirmedProject.tahun,
        sourceUrl: confirmedProject.source_url,
        resultUrl: confirmedProject.result_url,
        status: confirmedProject.status,
        errorMessage: confirmedProject.error_message,
        createdAt: confirmedProject.created_at,
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
    localStorage.removeItem(ACTIVE_PROJECT_KEY)
    setSkema("")
    setTahun("")
    setSelectedFile(null)
    setResult(null)
    setCurrentProjectId(null)
    setIsUploading(false)
    setUploadProgress(0)
    setUploadError(null)
    setLogs([])
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

  if (isRestoring) {
    return (
      <div className="px-8 py-8">
        <AdminPageHeader
          title="Buat Dokumen Proposal"
          description="Upload dokumen proposal PKM untuk diproses dan divisualisasikan"
        />
        <div className="flex items-center justify-center py-24">
          <Loader2Icon className="size-6 animate-spin text-gray-400" />
        </div>
      </div>
    )
  }

  return (
    <div className="px-8 py-8">
      <AdminPageHeader
        title="Buat Dokumen Proposal"
        description="Upload dokumen proposal PKM untuk diproses dan divisualisasikan"
      />

      {!result ? (
        <div className="grid gap-6">
          <AdminSurfaceCard>
            <div className="border-b border-gray-100 px-5 py-4">
              <h2 className="text-sm font-semibold text-gray-700">Form Upload</h2>
              <p className="mt-0.5 text-xs text-[rgba(0,0,0,0.4)]">
                Upload file proposal untuk diproses
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

              <div className="space-y-1.5 full-width">
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
                        accept=".pdf"
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
                       Mendukung file PDF
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

              <div className="flex justify-end gap-3 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleReset}
                  disabled={isUploading || (!selectedFile && !skema && !tahun)}
                >
                  Reset
                </Button>
                <Button type="submit" disabled={isUploading || !selectedFile || !skema || !tahun}>
                  {isUploading ? "Memproses..." : "Buat Dokumen"}
                </Button>
              </div>
            </form>
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
                    ? "Dokumen berhasil diproses"
                    : result.status === "failed"
                      ? "Terjadi kesalahan saat memproses dokumen"
                      : getStatusLabel(result.status)}
                </p>
              </div>
            </div>

            <div className="px-5 py-5">
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="rounded-xl border border-gray-100 bg-gray-50/50 p-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Skema</p>
                  <p className="mt-1 text-sm font-medium text-gray-800">{result.skema}</p>
                </div>
                <div className="rounded-xl border border-gray-100 bg-gray-50/50 p-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Tahun</p>
                  <p className="mt-1 text-sm font-medium text-gray-800">{result.tahun}</p>
                </div>
                <div className="rounded-xl border border-gray-100 bg-gray-50/50 p-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Nama File</p>
                  <p className="mt-1 text-sm font-medium text-gray-800">{result.fileName}</p>
                </div>
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

              {/* Terminal Log Display */}
              {logs.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-2">Log Proses</p>
                  <div className="bg-gray-900 rounded-xl border border-gray-700 p-4 max-h-64 overflow-y-auto font-mono text-xs">
                    {logs.map((log, index) => (
                      <div
                        key={log.id}
                        className={`flex gap-3 py-1 ${
                          log.step === "pipeline" ? "text-cyan-400" :
                          log.step === "setup" ? "text-green-400" :
                          log.step === "extraction" ? "text-yellow-400" :
                          log.step === "docx" ? "text-purple-400" :
                          log.step === "download" ? "text-blue-400" :
                          "text-gray-300"
                        }`}
                      >
                        <span className="text-gray-500 shrink-0">[{index + 1}]</span>
                        <span className="text-gray-400 shrink-0">{new Date(log.timestamp).toLocaleTimeString("id-ID")}</span>
                        <span className="uppercase shrink-0 font-bold opacity-70">[{log.step}]</span>
                        <span className="text-gray-100">{log.message}</span>
                      </div>
                    ))}
                    <div ref={logsEndRef} />
                  </div>
                </div>
              )}

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
