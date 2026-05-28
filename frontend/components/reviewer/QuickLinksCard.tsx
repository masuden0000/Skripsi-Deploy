"use client"

import { useEffect, useState } from "react"
import { ReviewerSurfaceCard } from "./shared"
import { Button } from "@/components/ui/button"
import { Loader2Icon } from "@/components/icons/public-icons"
import {
  DocumentIcon,
  ReviewIcon,
  LinkIcon,
  CopyIcon,
  CheckIcon,
} from "@/components/icons/public-icons"
import { getActiveAssignments, type Assignment } from "@/lib/api/reviewer-assignments"

interface QuickLinksCardProps {
  className?: string
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    if (!text) return

    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      const textarea = document.createElement("textarea")
      textarea.value = text
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand("copy")
      document.body.removeChild(textarea)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={handleCopy}
      disabled={!text}
      className="shrink-0"
    >
      {copied ? (
        <>
          <CheckIcon className="size-4 text-green-600" />
          <span className="text-xs text-green-600">Tersalin</span>
        </>
      ) : (
        <>
          <CopyIcon className="size-4" />
          <span className="text-xs">Salin</span>
        </>
      )}
    </Button>
  )
}

interface QuickLinkItem {
  id: string
  label: string
  description: string
  url: string
  icon: React.ReactNode
}

function QuickLinkCard({ item, url }: { item: QuickLinkItem; url: string }) {
  const linkUrl = url || "#"

  return (
    <div className="group relative rounded-lg bg-gray-50 p-4 transition-all hover:shadow-sm">
      <div className="flex items-start gap-4">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          {item.icon}
        </div>

        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium">{item.label}</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {item.description}
          </p>

          {url && (
            <a
              href={linkUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline"
            >
              <LinkIcon className="size-3" />
              <span className="truncate max-w-[200px]">{url}</span>
            </a>
          )}

          {!url && (
            <p className="mt-2 text-xs italic text-muted-foreground">
              URL belum dikonfigurasi
            </p>
          )}
        </div>

        <CopyButton text={url} />
      </div>
    </div>
  )
}

const defaultLinks: QuickLinkItem[] = [
  {
    id: "proposal",
    label: "URL Proposal",
    description: "Tautan ke halaman pengumpulan proposal",
    url: "",
    icon: <DocumentIcon className="size-5" />,
  },
  {
    id: "review",
    label: "URL Pengumpulan Penilaian",
    description: "Tautan ke halaman pengisian nilai/review",
    url: "",
    icon: <ReviewIcon className="size-5" />,
  },
]

export function QuickLinksCard({ className }: QuickLinksCardProps) {
  const [assignments, setAssignments] = useState<Assignment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchAssignments() {
      const result = await getActiveAssignments()
      if (result.error) {
        setError(result.error)
      } else {
        setAssignments(result.data || [])
      }
      setLoading(false)
    }

    fetchAssignments()
  }, [])

  if (loading) {
    return (
      <ReviewerSurfaceCard className={className}>
        <div className="px-6 pt-6 pb-3">
          <h3 className="text-base font-semibold">Tautan Cepat</h3>
        </div>
        <div className="px-6 pb-6 flex items-center gap-3">
          <Loader2Icon className="size-5 animate-spin text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Memuat tautan...</span>
        </div>
      </ReviewerSurfaceCard>
    )
  }

  if (error) {
    return (
      <ReviewerSurfaceCard className={className}>
        <div className="px-6 pt-6 pb-3">
          <h3 className="text-base font-semibold">Tautan Cepat</h3>
        </div>
        <div className="px-6 pb-6">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      </ReviewerSurfaceCard>
    )
  }

  // Get links from first active assignment (or use empty)
  const firstAssignment = assignments.length > 0 ? assignments[0] : null
  const links: QuickLinkItem[] = [
    {
      ...defaultLinks[0],
      url: firstAssignment?.proposalLink ?? "",
    },
    {
      ...defaultLinks[1],
      url: firstAssignment?.assessmentLink ?? "",
    },
  ]

  if (assignments.length === 0) {
    return (
      <ReviewerSurfaceCard className={className}>
        <div className="px-6 pt-6 pb-3">
          <h3 className="text-base font-semibold">Tautan Cepat</h3>
        </div>
        <div className="px-6 pb-6 space-y-3">
          {links.map((link) => (
            <div
              key={link.id}
              className="rounded-lg bg-gray-50 p-4 opacity-60"
            >
              <div className="flex items-start gap-4">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                  {link.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-medium text-muted-foreground">
                    {link.label}
                  </h3>
                  <p className="mt-0.5 text-xs italic text-muted-foreground">
                    Tidak ada tautan yang dikonfigurasi
                  </p>
                </div>
                <Button variant="outline" size="sm" disabled className="shrink-0">
                  <CopyIcon className="size-4" />
                  <span className="text-xs">Salin</span>
                </Button>
              </div>
            </div>
          ))}
        </div>
      </ReviewerSurfaceCard>
    )
  }

  return (
    <ReviewerSurfaceCard className={className}>
      <div className="px-6 pt-6 pb-3">
        <h3 className="text-base font-semibold">Tautan Cepat</h3>
      </div>
      <div className="px-6 pb-6 space-y-3">
        {links.map((link) => (
          <QuickLinkCard key={link.id} item={link} url={link.url} />
        ))}
      </div>
    </ReviewerSurfaceCard>
  )
}