"use client"

import { useEffect, useMemo, useState } from "react"
import { ReviewerSurfaceCard } from "./shared"
import { Button } from "@/components/ui/button"
import { CalendarIcon, ChevronIcon, CheckIcon, CopyIcon, LinkIcon, Loader2Icon } from "@/components/icons/public-icons"
import { getReviewerAssignments, completeReviewerAssignment, type Assignment } from "@/lib/api/reviewer-assignments"

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString("id-ID", {
    day: "numeric",
    month: "short",
    year: "numeric",
  })
}

function calculateDuration(start: string, end: string): string {
  const startDate = new Date(start)
  const endDate = new Date(end)
  const diffTime = Math.abs(endDate.getTime() - startDate.getTime())
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  return `${diffDays} hari`
}

function isActive(start: string, end: string): boolean {
  const now = new Date()
  const startDate = new Date(start)
  const endDate = new Date(end)
  return now >= startDate && now <= endDate
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
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <Button variant="ghost" size="icon-xs" onClick={handleCopy} disabled={!text}>
      {copied ? <CheckIcon className="size-3.5 text-green-600" /> : <CopyIcon className="size-3.5" />}
    </Button>
  )
}

interface AssignmentCardProps {
  assignment: Assignment
  onComplete: (id: string) => void
  isUpdating: boolean
}

function AssignmentCard({ assignment, onComplete, isUpdating }: AssignmentCardProps) {
  const active = isActive(assignment.periodMulai || "", assignment.periodSelesai || "")

  return (
    <ReviewerSurfaceCard className="hover:shadow-md transition-shadow">
      <div className="p-4 space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-base truncate">{assignment.period}</h3>
            <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
              <CalendarIcon className="size-3.5 flex-none" />
              <span>
                {formatDate(assignment.periodMulai || "")} – {formatDate(assignment.periodSelesai || "")}
              </span>
              <span>
                ({calculateDuration(assignment.periodMulai || "", assignment.periodSelesai || "")})
              </span>
            </div>
          </div>
          <span
            className={[
              "shrink-0 inline-flex items-center rounded-full px-3 py-1 text-xs font-medium",
              active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500",
            ].join(" ")}
          >
            {active ? "Aktif" : "Tidak Aktif"}
          </span>
        </div>

        {/* Info + completion action */}
        <div className="flex items-center justify-between gap-4 text-sm">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <span className="size-1.5 rounded-full bg-muted-foreground/30" />
            <span>{assignment.fakultas}</span>
          </div>
          {assignment.reviewStatus === "selesai" ? (
            <span className="shrink-0 inline-flex items-center gap-1.5 rounded-full bg-pkm-100 px-3 py-1 text-xs font-semibold text-pkm-700">
              <CheckIcon className="size-3" />
              Selesai
            </span>
          ) : assignment.reviewStatus === "menunggu_validasi" ? (
            <span className="shrink-0 inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700">
              Menunggu Validasi
            </span>
          ) : active ? (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onComplete(assignment.id)}
              disabled={isUpdating}
              className="shrink-0 h-7 gap-1.5 border-pkm-300 text-pkm-700 hover:bg-pkm-50 text-xs"
            >
              {isUpdating
                ? <Loader2Icon className="size-3.5 animate-spin" />
                : <CheckIcon className="size-3.5" />}
              Tandai Selesai
            </Button>
          ) : null}
        </div>

        {/* Links */}
        <div className="rounded-lg bg-gray-50 px-3 py-3 space-y-2">
          <div className="flex items-center gap-2">
            <LinkIcon className="size-4 flex-none text-muted-foreground" />
            <span className="text-sm font-medium min-w-32">URL Proposal:</span>
            {assignment.proposalLink ? (
              <div className="flex items-center gap-1 flex-1 min-w-0">
                <a
                  href={assignment.proposalLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-primary hover:underline truncate"
                >
                  {assignment.proposalLink}
                </a>
                <CopyButton text={assignment.proposalLink} />
              </div>
            ) : (
              <span className="text-sm text-muted-foreground italic">Belum diatur</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <LinkIcon className="size-4 flex-none text-muted-foreground" />
            <span className="text-sm font-medium min-w-32">URL Pengumpulan:</span>
            {assignment.assessmentLink ? (
              <div className="flex items-center gap-1 flex-1 min-w-0">
                <a
                  href={assignment.assessmentLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-primary hover:underline truncate"
                >
                  {assignment.assessmentLink}
                </a>
                <CopyButton text={assignment.assessmentLink} />
              </div>
            ) : (
              <span className="text-sm text-muted-foreground italic">Belum diatur</span>
            )}
          </div>
        </div>
      </div>
    </ReviewerSurfaceCard>
  )
}

interface SectionProps {
  title: string
  count: number
  expanded: boolean
  onToggle: () => void
  children: React.ReactNode
}

function CollapsibleSection({ title, count, expanded, onToggle, children }: SectionProps) {
  return (
    <div>
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between py-3"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-700">{title}</span>
          <span className="inline-flex rounded-full bg-pkm-100 px-2 py-0.5 text-xs font-medium text-pkm-700">
            {count}
          </span>
        </div>
        <ChevronIcon open={expanded} className="size-4 text-gray-400" />
      </button>
      {expanded && (
        <div className="space-y-3 pt-3">
          {children}
        </div>
      )}
    </div>
  )
}

export function AssignmentsList() {
  const [assignments, setAssignments] = useState<Assignment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedYear, setSelectedYear] = useState<string>("all")
  const [activeExpanded, setActiveExpanded] = useState(true)
  const [inactiveExpanded, setInactiveExpanded] = useState(false)
  const [updatingId, setUpdatingId] = useState<string | null>(null)
  const [completeError, setCompleteError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchAssignments() {
      const result = await getReviewerAssignments()
      if (result.error) {
        setError(result.error)
      } else {
        setAssignments(result.data || [])
      }
      setLoading(false)
    }
    fetchAssignments()
  }, [])

  async function handleComplete(id: string) {
    setUpdatingId(id)
    setCompleteError(null)
    const result = await completeReviewerAssignment(id)
    if (result.error) {
      setCompleteError(result.error)
    } else {
      setAssignments(prev => prev.map(a => a.id === id ? { ...a, reviewStatus: "menunggu_validasi" as const } : a))
    }
    setUpdatingId(null)
  }

  const availableYears = useMemo(() => {
    const years = assignments
      .map(a => (a.periodMulai ? new Date(a.periodMulai).getFullYear().toString() : null))
      .filter((y): y is string => y !== null)
    return [...new Set(years)].sort((a, b) => Number(b) - Number(a))
  }, [assignments])

  const filteredAssignments = useMemo(() => {
    if (selectedYear === "all") return assignments
    return assignments.filter(a => {
      const year = a.periodMulai ? new Date(a.periodMulai).getFullYear().toString() : null
      return year === selectedYear
    })
  }, [assignments, selectedYear])

  const activeAssignments = useMemo(
    () => filteredAssignments.filter(a => isActive(a.periodMulai || "", a.periodSelesai || "")),
    [filteredAssignments]
  )

  const inactiveAssignments = useMemo(
    () => filteredAssignments.filter(a => !isActive(a.periodMulai || "", a.periodSelesai || "")),
    [filteredAssignments]
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 gap-3">
        <Loader2Icon className="size-5 animate-spin text-muted-foreground" />
        <span className="text-muted-foreground">Memuat penugasan...</span>
      </div>
    )
  }

  if (error) {
    return (
      <ReviewerSurfaceCard>
        <div className="p-6 text-center">
          <p className="text-destructive">{error}</p>
        </div>
      </ReviewerSurfaceCard>
    )
  }

  if (assignments.length === 0) {
    return (
      <ReviewerSurfaceCard>
        <div className="p-6 text-center">
          <CalendarIcon className="size-10 mx-auto text-muted-foreground/50 mb-3" />
          <p className="text-muted-foreground">Belum ada penugasan</p>
          <p className="text-sm text-muted-foreground mt-1">
            Anda belum ditugaskan ke periode review manapun
          </p>
        </div>
      </ReviewerSurfaceCard>
    )
  }

  return (
    <div className="space-y-4">
      {completeError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700">
          {completeError}
        </div>
      ) : null}

      {availableYears.length > 1 && (
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => setSelectedYear("all")}
            className={[
              "rounded-full px-3 py-1 text-xs font-medium transition-colors",
              selectedYear === "all"
                ? "bg-pkm-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200",
            ].join(" ")}
          >
            Semua
          </button>
          {availableYears.map(year => (
            <button
              key={year}
              type="button"
              onClick={() => setSelectedYear(year)}
              className={[
                "rounded-full px-3 py-1 text-xs font-medium transition-colors",
                selectedYear === year
                  ? "bg-pkm-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200",
              ].join(" ")}
            >
              {year}
            </button>
          ))}
        </div>
      )}

      <div className="space-y-1">
        <CollapsibleSection
          title="Aktif"
          count={activeAssignments.length}
          expanded={activeExpanded}
          onToggle={() => setActiveExpanded(v => !v)}
        >
          {activeAssignments.length === 0 ? (
            <p className="text-sm text-muted-foreground py-2">Tidak ada penugasan aktif.</p>
          ) : (
            activeAssignments.map(assignment => (
              <AssignmentCard
                key={assignment.id}
                assignment={assignment}
                onComplete={handleComplete}
                isUpdating={updatingId === assignment.id}
              />
            ))
          )}
        </CollapsibleSection>

        <CollapsibleSection
          title="Tidak Aktif"
          count={inactiveAssignments.length}
          expanded={inactiveExpanded}
          onToggle={() => setInactiveExpanded(v => !v)}
        >
          {inactiveAssignments.length === 0 ? (
            <p className="text-sm text-muted-foreground py-2">Tidak ada penugasan tidak aktif.</p>
          ) : (
            inactiveAssignments.map(assignment => (
              <AssignmentCard
                key={assignment.id}
                assignment={assignment}
                onComplete={handleComplete}
                isUpdating={updatingId === assignment.id}
              />
            ))
          )}
        </CollapsibleSection>
      </div>
    </div>
  )
}
