import { DocumentValidator } from "@/components/reviewer/DocumentValidator"

export default function ReviewerValidationPage() {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Validasi Dokumen</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Validasi format dokumen DOCX proposal PKM terhadap aturan yang berlaku pada periode aktif
        </p>
      </div>

      <div className="max-w-2xl">
        <DocumentValidator />
      </div>
    </div>
  )
}
