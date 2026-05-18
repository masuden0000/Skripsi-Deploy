"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { AdminPageHeader, AdminSurfaceCard } from "@/components/admin/shared"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { YearPicker } from "@/components/ui/year-picker"
import { DownloadIcon, Loader2Icon, ArrowLeftIcon } from "@/components/icons/public-icons"


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

const SKEMA_LABEL: Record<string, string> = Object.fromEntries(
  PKM_SCHEMES.map((s) => [s.value, s.value.toUpperCase()])
)

export default function RiwayatPage() {
  const router = useRouter()
  const [filterSkema, setFilterSkema] = useState("all")
  const [filterTahun, setFilterTahun] = useState("")
  const [data, setData] = useState<HistoryItem[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [fetchError, setFetchError] = useState<string | null>(null)

  useEffect(() => {
    setIsLoading(true)
    setFetchError(null)

    const params = new URLSearchParams()
    if (filterSkema !== "all") params.set("skema", filterSkema)
    if (filterTahun) params.set("tahun", filterTahun)

    fetch(`/api/projects/history?${params.toString()}`)
      .then((res) => res.json())
      .then((json) => setData(json.data ?? []))
      .catch(() => setFetchError("Gagal memuat riwayat. Coba lagi."))
      .finally(() => setIsLoading(false))
  }, [filterSkema, filterTahun])

  return (
    <div className="px-8 py-8">
      <div className="mb-6">
        <Button
          type="button"
          variant="ghost"
          onClick={() => router.push("/admin/proposal")}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-800 px-0 hover:bg-transparent"
        >
          <ArrowLeftIcon className="size-4" />
          Kembali
        </Button>
      </div>

      <AdminPageHeader
        title="Riwayat Template Proposal"
        description="Daftar template proposal PKM yang telah berhasil dibuat"
      />

      <AdminSurfaceCard>
        <div className="border-b border-gray-100 px-5 py-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-gray-600">Skema PKM</Label>
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
              <Label className="text-xs font-medium text-gray-600">Tahun</Label>
              <YearPicker
                value={filterTahun}
                onChange={setFilterTahun}
                placeholder="Semua tahun"
              />
            </div>
          </div>
        </div>

        <div className="px-5 py-4">
          {isLoading ? (
            <div className="flex justify-center py-10">
              <Loader2Icon className="size-5 animate-spin text-gray-400" />
            </div>
          ) : fetchError ? (
            <p className="py-8 text-center text-sm text-red-500">{fetchError}</p>
          ) : data.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-400">
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
      </AdminSurfaceCard>
    </div>
  )
}
