"use client"

import { useEffect, useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Loader2Icon, CalendarIcon, LinkIcon, CopyIcon, CheckIcon } from "@/components/icons/public-icons"
import { getReviewerAssignments, type Assignment } from "@/lib/api/reviewer-assignments"

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
}

function AssignmentCard({ assignment }: AssignmentCardProps) {
  const active = isActive(assignment.periodMulai || "", assignment.periodSelesai || "")

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-4 space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-base truncate">{assignment.period}</h3>
            <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
              <CalendarIcon className="size-3.5 flex-none" />
              <span>
                {formatDate(assignment.periodMulai || "")} — {formatDate(assignment.periodSelesai || "")}
              </span>
            </div>
          </div>
          <span
            className={`shrink-0 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
              active
                ? "bg-green-100 text-green-700"
                : "bg-muted text-muted-foreground"
            }`}
          >
            {active ? "Aktif" : "Selesai"}
          </span>
        </div>

        {/* Info */}
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <span className="size-1.5 rounded-full bg-muted-foreground/30" />
            <span>{calculateDuration(assignment.periodMulai || "", assignment.periodSelesai || "")}</span>
          </div>
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <span className="size-1.5 rounded-full bg-muted-foreground/30" />
            <span>{assignment.fakultas}</span>
          </div>
        </div>

        {/* Links */}
        <div className="space-y-2 pt-2 border-t">
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
      </CardContent>
    </Card>
  )
}

export function AssignmentsList() {
  const [assignments, setAssignments] = useState<Assignment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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
      <Card>
        <CardContent className="p-6 text-center">
          <p className="text-destructive">{error}</p>
        </CardContent>
      </Card>
    )
  }

  if (assignments.length === 0) {
    return (
      <Card>
        <CardContent className="p-6 text-center">
          <CalendarIcon className="size-10 mx-auto text-muted-foreground/50 mb-3" />
          <p className="text-muted-foreground">Belum ada penugasan</p>
          <p className="text-sm text-muted-foreground mt-1">
            Anda belum ditugaskan ke periode review manapun
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {assignments.map((assignment) => (
        <AssignmentCard key={assignment.id} assignment={assignment} />
      ))}
    </div>
  )
}