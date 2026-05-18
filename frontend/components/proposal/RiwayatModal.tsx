"use client"

import { useState, useEffect } from "react"
import { AdminModalShell } from "@/components/admin/shared"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { DownloadIcon, Loader2Icon } from "@/components/icons/public-icons"

type HistoryItem = {
  id: string
  skema: string
  tahun: string
  result_url: string
}

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

const SKEMA_LABEL: Record<string, string> = Object.fromEntries(
  PKM_SCHEMES.map((s) => [s.value, s.value.toUpperCase()])
)

export function RiwayatModal({
  open,
  onClose,
}: {
  open: boolean
  onClose: () => void
}) {
  const [filterSkema, setFilterSkema] = useState("all")
  const [filterTahun, setFilterTahun] = useState("all")
  const [data, setData] = useState<HistoryItem[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [fetchError, setFetchError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setIsLoading(true)
    setFetchError(null)

    const params = new URLSearchParams()
    if (filterSkema !== "all") params.set("skema", filterSkema)
    if (filterTahun !== "all") params.set("tahun", filterTahun)

    fetch(`/api/projects/history?${params.toString()}`)
      .then((res) => res.json())
      .then((json) => setData(json.data ?? []))
      .catch(() => setFetchError("Gagal memuat riwayat. Coba lagi."))
      .finally(() => setIsLoading(false))
  }, [open, filterSkema, filterTahun])

  if (!open) return null

  return (
    <AdminModalShell
      title="Riwayat Template Proposal"
      description="Daftar template proposal PKM yang telah berhasil dibuat"
      onClose={onClose}
      maxWidthClassName="max-w-2xl"
    >
      <div className="space-y-4 px-6 py-5">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-gray-600">Skema PKM</p>
            <Select value={filterSkema} onValueChange={setFilterSkema}>
              <SelectTrigger>
                <SelectValue placeholder="Semua skema" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Semua Skema</SelectItem>
                {PKM_SCHEMES.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <p className="text-xs font-medium text-gray-600">Tahun</p>
            <Select value={filterTahun} onValueChange={setFilterTahun}>
              <SelectTrigger>
                <SelectValue placeholder="Semua tahun" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Semua Tahun</SelectItem>
                {YEARS.map((y) => (
                  <SelectItem key={y.value} value={y.value}>
                    {y.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-10">
            <Loader2Icon className="size-5 animate-spin text-gray-400" />
          </div>
        ) : fetchError ? (
          <p className="py-6 text-center text-sm text-red-500">{fetchError}</p>
        ) : data.length === 0 ? (
          <p className="py-6 text-center text-sm text-gray-400">
            Belum ada template proposal yang tersedia.
          </p>
        ) : (
          <div className="overflow-hidden rounded-lg border border-gray-100">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">
                    Nama Skema
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">
                    Tahun
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500">
                    Template
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {data.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50/50">
                    <td className="px-4 py-3 font-medium text-gray-700">
                      {SKEMA_LABEL[item.skema] ?? item.skema.toUpperCase()}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{item.tahun}</td>
                    <td className="px-4 py-3 text-right">
                      <a
                        href={item.result_url}
                        download
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Button size="sm" variant="outline" className="gap-1.5">
                          <DownloadIcon className="size-3.5" />
                          Download
                        </Button>
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AdminModalShell>
  )
}
