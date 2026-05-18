# Riwayat Template Proposal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tambah tombol "Riwayat" di halaman Buat Dokumen Proposal yang membuka modal berisi daftar template proposal yang berhasil dibuat, dengan filter skema/tahun dan tombol download.

**Architecture:** API route baru (`GET /api/projects/history`) query tabel `projects` dengan filter status=completed dan result_url not null. Modal menggunakan `AdminModalShell` yang sudah ada. Tombol "Riwayat" ditempatkan di `AdminPageHeader` via prop `action` yang sudah tersedia.

**Tech Stack:** Next.js App Router, Supabase JS client, Tailwind CSS, komponen admin yang sudah ada (`AdminModalShell`, `AdminPageHeader`, `Button`, `Select`).

---

## File Map

| Status | File | Tanggung jawab |
|--------|------|----------------|
| Create | `frontend/app/api/projects/history/route.ts` | GET endpoint — query projects completed + result_url |
| Create | `frontend/components/proposal/RiwayatModal.tsx` | Modal dengan filter + tabel + download |
| Modify | `frontend/components/icons/public-icons.tsx` | Tambah `HistoryIcon` dan `DownloadIcon` |
| Modify | `frontend/app/(dashboard)/admin/proposal/page.tsx` | Tambah state + tombol + render modal |

---

## Task 1: Tambah HistoryIcon dan DownloadIcon

**Files:**
- Modify: `frontend/components/icons/public-icons.tsx`

- [ ] **Step 1: Tambah dua icon baru di akhir file**

Buka `frontend/components/icons/public-icons.tsx`, tambahkan setelah `XIcon`:

```tsx
export function HistoryIcon({ className }: IconProps) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className={cn("size-4", className)}>
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
      <path d="M3 3v5h5" />
      <path d="M12 7v5l4 2" />
    </svg>
  )
}

export function DownloadIcon({ className }: IconProps) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className={cn("size-4", className)}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  )
}
```

- [ ] **Step 2: Pastikan `cn` sudah di-import di file tersebut**

Cek baris pertama file — jika belum ada `import { cn } from "@/lib/utils"`, tambahkan. (Biasanya sudah ada karena icon lain menggunakannya.)

- [ ] **Step 3: Commit**

```bash
git add frontend/components/icons/public-icons.tsx
git commit -m "feat: add HistoryIcon and DownloadIcon to public-icons"
```

---

## Task 2: API Route GET /api/projects/history

**Files:**
- Create: `frontend/app/api/projects/history/route.ts`

Context: Tabel `projects` memiliki kolom `id`, `skema`, `tahun`, `result_url`, `status`. Bucket `ai-output-files` bersifat public — `result_url` yang tersimpan di DB sudah merupakan URL publik yang bisa langsung digunakan sebagai link download. API ini hanya perlu query DB dan return data; tidak perlu generate signed URL.

- [ ] **Step 1: Buat file API route**

Buat `frontend/app/api/projects/history/route.ts`:

```typescript
import { createClient } from "@supabase/supabase-js"
import { NextResponse } from "next/server"

function getSupabase() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url)
  const skema = searchParams.get("skema")
  const tahun = searchParams.get("tahun")

  const supabase = getSupabase()

  let query = supabase
    .from("projects")
    .select("id, skema, tahun, result_url")
    .eq("status", "completed")
    .not("result_url", "is", null)
    .order("tahun", { ascending: false })
    .order("skema", { ascending: true })

  if (skema) query = query.eq("skema", skema)
  if (tahun) query = query.eq("tahun", tahun)

  const { data, error } = await query

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ data: data ?? [] })
}
```

- [ ] **Step 2: Verifikasi manual (opsional)**

Jika dev server berjalan, buka browser ke `http://localhost:3000/api/projects/history`. Harus return `{ "data": [...] }` atau `{ "data": [] }` jika belum ada project completed.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/api/projects/history/route.ts
git commit -m "feat: add GET /api/projects/history endpoint"
```

---

## Task 3: Komponen RiwayatModal

**Files:**
- Create: `frontend/components/proposal/RiwayatModal.tsx`

Context penting:
- `AdminModalShell` ada di `@/components/admin/shared` — menerima `title`, `description`, `onClose`, `maxWidthClassName`
- `Select`, `SelectContent`, `SelectItem`, `SelectTrigger`, `SelectValue` ada di `@/components/ui/select`
- `Button` ada di `@/components/ui/button`
- Skema yang valid sama persis dengan `PKM_SCHEMES` di proposal page (didefinisikan ulang di sini agar komponen tidak bergantung ke page)
- `result_url` adalah URL publik Supabase — bisa langsung dijadikan `href` link download

- [ ] **Step 1: Buat file komponen**

Buat `frontend/components/proposal/RiwayatModal.tsx`:

```tsx
"use client"

import { useState, useEffect } from "react"
import {
  AdminModalShell,
} from "@/components/admin/shared"
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
      <div className="px-6 py-5 space-y-4">
        {/* Filters */}
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

        {/* Table */}
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/proposal/RiwayatModal.tsx
git commit -m "feat: add RiwayatModal component with filter and download table"
```

---

## Task 4: Integrasi ke Halaman Proposal

**Files:**
- Modify: `frontend/app/(dashboard)/admin/proposal/page.tsx`

Context: `AdminPageHeader` sudah punya prop `action?: ReactNode` yang merender elemen di kanan atas. State `showRiwayat` perlu ditambah. Ada 3 tempat `AdminPageHeader` di-render dalam file ini (loading state, normal state, result state) — semua perlu tombol.

- [ ] **Step 1: Tambah import**

Di bagian import atas file (setelah baris import icon yang sudah ada):

```tsx
// Tambah HistoryIcon ke import icon yang sudah ada:
import { DocumentIcon, FileTextIcon, UploadIcon, CheckCircleIcon, AlertCircleIcon, Loader2Icon, HistoryIcon } from "@/components/icons/public-icons"
// Tambah import RiwayatModal:
import { RiwayatModal } from "@/components/proposal/RiwayatModal"
```

- [ ] **Step 2: Tambah state showRiwayat**

Di dalam `ProposalDocumentPage`, setelah baris `const resultStatus = result?.status`:

```tsx
const [showRiwayat, setShowRiwayat] = useState(false)
```

- [ ] **Step 3: Buat helper tombol Riwayat**

Tambahkan variabel ini di dalam komponen, sebelum `return`:

```tsx
const riwayatButton = (
  <Button
    type="button"
    variant="outline"
    size="sm"
    className="gap-1.5"
    onClick={() => setShowRiwayat(true)}
  >
    <HistoryIcon className="size-4" />
    Riwayat
  </Button>
)
```

- [ ] **Step 4: Pasang tombol di semua AdminPageHeader**

Cari semua kemunculan `<AdminPageHeader` di file ini (ada 3: loading state, result state, normal return). Tambahkan prop `action={riwayatButton}` ke ketiganya:

```tsx
// Contoh perubahan:
<AdminPageHeader
  title="Buat Dokumen Proposal"
  description="Upload dokumen proposal PKM untuk diproses dan divisualisasikan"
  action={riwayatButton}
/>
```

- [ ] **Step 5: Render RiwayatModal**

Di akhir return utama (sebelum `</div>` penutup terluar), tambahkan:

```tsx
<RiwayatModal open={showRiwayat} onClose={() => setShowRiwayat(false)} />
```

- [ ] **Step 6: Commit**

```bash
git add frontend/app/(dashboard)/admin/proposal/page.tsx
git commit -m "feat: integrate RiwayatModal with Riwayat button on proposal page"
```

---

## Verifikasi End-to-End

1. Jalankan dev server: `cd frontend && npm run dev`
2. Login sebagai admin → navigasi ke **Buat Dokumen Proposal**
3. Tombol **Riwayat** muncul di kanan atas header, sejajar horizontal dengan judul halaman
4. Klik tombol → modal **Riwayat Template Proposal** terbuka
5. Modal menampilkan dropdown Skema PKM dan Tahun
6. Pilih filter → tabel terupdate (refetch ke `/api/projects/history?skema=...&tahun=...`)
7. Jika ada project completed: baris tabel tampil dengan nama skema, tahun, dan tombol **Download**
8. Klik **Download** → file `.docx` terunduh dari URL Supabase bucket `ai-output-files`
9. Jika tidak ada data: tampil pesan "Belum ada template proposal yang tersedia."
10. Klik backdrop atau tombol × → modal tertutup
