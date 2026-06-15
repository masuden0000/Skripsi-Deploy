/**
 * Halaman utama validasi dokumen untuk role Reviewer.
 * Posisi pipeline: entry point UI → DocumentValidator → pkm.ts → Express → FastAPI.
 * Keyword: automated document validation
 */
import { DocumentValidator } from "@/components/reviewer/DocumentValidator"
import { ReviewerPageHeader } from "@/components/reviewer/shared"

export default function ReviewerValidationPage() {
  return (
    <div className="px-8 py-8">
      <ReviewerPageHeader
        title="Validasi Dokumen"
        description="Validasi format dokumen DOCX proposal PKM terhadap aturan yang berlaku pada periode aktif"
      />
      <DocumentValidator />
    </div>
  )
}
