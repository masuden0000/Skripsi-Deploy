"use client"

import { AssignmentsList } from "@/components/reviewer/AssignmentsList"

export default function ReviewerAssignmentsPage() {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Daftar Penugasan</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Daftar periode review yang telah ditugaskan kepada Anda
        </p>
      </div>

      <AssignmentsList />
    </div>
  )
}