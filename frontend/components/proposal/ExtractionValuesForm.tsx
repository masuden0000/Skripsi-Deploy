/**
 * Form untuk menampilkan dan mengedit hasil ekstraksi metadata dokumen.
 *
 * Peran dalam pipeline:
 *   - Menerima `data` (ExtractionPayload) dari halaman proposal setelah pipeline ekstraksi selesai
 *   - Setiap perubahan field langsung di-propagate ke parent via `onChange`
 *   - Parent menyimpan perubahan ke Supabase document_metadata.payload melalui Express backend
 *   - Data yang tersimpan dipakai sebagai input untuk render_proposal_docx_bytes saat generate DOCX
 *
 * Digunakan oleh: frontend/app/(dashboard)/admin/proposal/page.tsx
 *
 * Keyword: automated document generation
 */
"use client"

import { useState } from "react"
import { Info, Pencil } from "lucide-react"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { ModalSectionEditor } from "./ModalSectionEditor"

// ─── Types ──────────────────────────────────────────────────────────────────

export type PageNumberConfig = {
  format: string | null
  location: string | null
  alignment: string | null
  start_at_section: string | null
}

export type SectionItem = {
  type: string
  required: boolean | null
  number: number | null
  sub_number: string | null
  title: string | null
  lampiran_number: string | null
  is_major_section: boolean
}

export type ExtractionPayload = {
  document_type: string | null
  source_document: string | null
  typography: {
    font_family: string | null
    font_size_body_pt: number | null
    font_size_heading_pt: number | null
    heading_1_case: "UPPERCASE" | "LOWERCASE" | "SENTENCE_CASE" | "TOGGLE_CASE" | null
    heading_2_case: "UPPERCASE" | "LOWERCASE" | "SENTENCE_CASE" | "TOGGLE_CASE" | null
    heading_3_case: "UPPERCASE" | "LOWERCASE" | "SENTENCE_CASE" | "TOGGLE_CASE" | null
    heading_4_case: "UPPERCASE" | "LOWERCASE" | "SENTENCE_CASE" | "TOGGLE_CASE" | null
    heading_5_case: "UPPERCASE" | "LOWERCASE" | "SENTENCE_CASE" | "TOGGLE_CASE" | null
  }
  page_layout: {
    margin_top_cm: number | null
    margin_bottom_cm: number | null
    margin_left_cm: number | null
    margin_right_cm: number | null
    paper_size: string | null
    orientation: string | null
  }
  spacing: {
    line_spacing: number | null
    line_spacing_rule: string | null
    paragraph_alignment: string | null
  }
  document_structure_proposal: {
    sections: SectionItem[]
    format_nama_file: string | null
    lampiran_heading_separator: string | null
    user_placeholders?: Record<string, string>
  }
  numbering: {
    preliminary: PageNumberConfig | null
    content: PageNumberConfig | null
    chapter_format: string | null
    sub_chapter_format: string | null
  }
  figures_and_tables: {
    table_caption_position: string | null
    figure_caption_position: string | null
    caption_format_figure: string | null
    caption_format_table: string | null
    caption_format_lampiran: string | null
    caption_alignment_figure: "CENTER" | "LEFT" | "RIGHT" | "JUSTIFY" | null
    caption_alignment_table: "CENTER" | "LEFT" | "RIGHT" | "JUSTIFY" | null
    caption_alignment_lampiran: "CENTER" | "LEFT" | "RIGHT" | "JUSTIFY" | null
  }
  page_count_limits: {
    proposal_halaman_inti_maks: number | null
    halaman_inti_mulai: string | null
    halaman_inti_selesai: string | null
  }
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function SectionHeader({ title }: { title: string }) {
  return (
    <div className="rounded-lg bg-muted/50 px-4 py-3 text-sm font-semibold">
      {title}
    </div>
  )
}

function FieldRow({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-2 gap-x-6 gap-y-4">{children}</div>
}

function TextFieldInput({
  label,
  value,
  onChange,
}: {
  label: string
  value: string | null
  onChange: (v: string) => void
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <Input
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        className="h-8 text-sm"
      />
    </div>
  )
}

function NumberFieldInput({
  label,
  value,
  onChange,
  disabled,
  placeholder,
  hint,
}: {
  label: string
  value: number | null
  onChange: (v: number | null) => void
  disabled?: boolean
  placeholder?: string
  hint?: string
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label className={`text-xs ${disabled ? "text-muted-foreground/40" : "text-muted-foreground"}`}>
        {label}
      </Label>
      <Input
        type="number"
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
        className="h-8 text-sm"
        disabled={disabled}
        placeholder={placeholder}
      />
      {hint && <p className="text-[10px] text-muted-foreground/60 leading-tight">{hint}</p>}
    </div>
  )
}

function SelectFieldInput({
  label,
  value,
  options,
  onChange,
  disabled,
}: {
  label: string
  value: string | null
  options: { value: string; label: string }[]
  onChange: (v: string) => void
  disabled?: boolean
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <Select value={value ?? ""} onValueChange={onChange} disabled={disabled}>
        <SelectTrigger className="h-8 text-sm">
          <SelectValue placeholder="—" />
        </SelectTrigger>
        <SelectContent>
          {options.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

function BoolFieldInput({
  label,
  value,
  onChange,
}: {
  label: string
  value: boolean | null
  onChange: (v: boolean) => void
}) {
  return (
    <div className="flex items-center gap-2 pt-5">
      <Checkbox
        id={label}
        checked={value ?? false}
        onCheckedChange={(checked) => onChange(checked === true)}
      />
      <Label htmlFor={label} className="text-xs text-muted-foreground cursor-pointer">
        {label}
      </Label>
    </div>
  )
}


/**
 * Ekivalen Python str.title() — dipakai renderer docx untuk lampiran & sub-bab.
 * Frontend menampilkan transformasi yang sama agar preview sesuai dokumen.
 */
function toTitleCase(str: string | null | undefined): string {
  if (!str) return ""
  return str.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())
}

const HEADING_CASE_OPTIONS = [
  { value: "UPPERCASE",     label: "Uppercase — SEMUA KAPITAL" },
  { value: "LOWERCASE",     label: "Lowercase — semua kecil" },
  { value: "SENTENCE_CASE", label: "Sentence case — Huruf pertama besar" },
  { value: "TOGGLE_CASE",   label: "tOGGLE cASE — Balik huruf" },
]

const TYPE_LABEL_MAP: Record<string, string> = {
  daftar_isi: "Daftar Isi",
  daftar_gambar: "Daftar Gambar",
  daftar_tabel: "Daftar Tabel",
  daftar_lampiran: "Daftar Lampiran",
  bab: "BAB",
  sub_bab: "Sub-BAB",
  daftar_pustaka: "Daftar Pustaka",
  lampiran: "Lampiran",
  item_lampiran: "Item Lampiran",
}

// ─── Main Component ──────────────────────────────────────────────────────────

type Props = {
  data: ExtractionPayload
  onChange: (updated: ExtractionPayload) => void
  projectId?: string | null
}

export function ExtractionValuesForm({ data, onChange, projectId }: Props) {
  const [showSectionModal, setShowSectionModal] = useState(false)
  const [showFormatInfo, setShowFormatInfo] = useState(false)

  // Helper: update satu field nested di ExtractionPayload dan propagate ke parent
  // Parent (page.tsx) menyimpan hasilnya ke Supabase document_metadata.payload
  function patch<K extends keyof ExtractionPayload>(
    key: K,
    value: Partial<ExtractionPayload[K]>
  ) {
    onChange({ ...data, [key]: { ...(data[key] as object), ...value } })
  }

  return (
    <div className="flex flex-col gap-3">
      {/* ── 1. Tipografi ── */}
      <div>
        <SectionHeader title="1. Tipografi" />
        <div className="mt-3 px-1">
          <FieldRow>
            <TextFieldInput
              label="Font Family"
              value={data.typography.font_family}
              onChange={(v) => patch("typography", { font_family: v })}
            />
            <NumberFieldInput
              label="Ukuran Body (pt)"
              value={data.typography.font_size_body_pt}
              onChange={(v) => patch("typography", { font_size_body_pt: v })}
            />
            <NumberFieldInput
              label="Ukuran Heading (pt)"
              value={data.typography.font_size_heading_pt}
              onChange={(v) => patch("typography", { font_size_heading_pt: v })}
            />
          </FieldRow>
        </div>
      </div>

      {/* ── 2. Layout Halaman ── */}
      <div>
        <SectionHeader title="2. Layout Halaman" />
        <div className="mt-3 px-1">
          <FieldRow>
            <NumberFieldInput
              label="Margin Atas (cm)"
              value={data.page_layout.margin_top_cm}
              onChange={(v) => patch("page_layout", { margin_top_cm: v })}
            />
            <NumberFieldInput
              label="Margin Bawah (cm)"
              value={data.page_layout.margin_bottom_cm}
              onChange={(v) => patch("page_layout", { margin_bottom_cm: v })}
            />
            <NumberFieldInput
              label="Margin Kiri (cm)"
              value={data.page_layout.margin_left_cm}
              onChange={(v) => patch("page_layout", { margin_left_cm: v })}
            />
            <NumberFieldInput
              label="Margin Kanan (cm)"
              value={data.page_layout.margin_right_cm}
              onChange={(v) => patch("page_layout", { margin_right_cm: v })}
            />
            <SelectFieldInput
              label="Ukuran Kertas"
              value={data.page_layout.paper_size}
              options={[
                { value: "A4", label: "A4" },
                { value: "Letter", label: "Letter" },
                { value: "Legal", label: "Legal" },
              ]}
              onChange={(v) => patch("page_layout", { paper_size: v })}
              disabled
            />
            <SelectFieldInput
              label="Orientasi"
              value={data.page_layout.orientation}
              options={[
                { value: "Portrait", label: "Portrait" },
                { value: "Landscape", label: "Landscape" },
              ]}
              onChange={(v) => patch("page_layout", { orientation: v })}
              disabled
            />
          </FieldRow>
        </div>
      </div>

      {/* ── 3. Spasi ── */}
      {(() => {
        const rule = data.spacing.line_spacing_rule?.toUpperCase() ?? null
        const GRUP_A = ["SINGLE", "ONE_POINT_FIVE", "DOUBLE"]
        const GRUP_C = ["AT_LEAST", "EXACTLY"]
        const isGrupA = rule !== null && GRUP_A.includes(rule)
        const isGrupC = rule !== null && GRUP_C.includes(rule)
        const spasiBarisHint = isGrupA
          ? "Dinonaktifkan — nilai sudah ditentukan oleh aturan"
          : isGrupC
          ? "Nilai dalam satuan pt (contoh: 14.0)"
          : "Pengali desimal (contoh: 1.15)"
        return (
          <div>
            <SectionHeader title="3. Spasi" />
            <div className="mt-3 px-1">
              <FieldRow>
                <SelectFieldInput
                  label="Aturan Spasi"
                  value={rule}
                  options={[
                    { value: "SINGLE",          label: "Tunggal" },
                    { value: "ONE_POINT_FIVE",  label: "1.5 Baris" },
                    { value: "DOUBLE",          label: "Ganda" },
                    { value: "MULTIPLE",        label: "Beberapa" },
                    { value: "AT_LEAST",        label: "Sedikitnya" },
                    { value: "EXACTLY",         label: "Tepat" },
                  ]}
                  onChange={(v) => {
                    const grupA = ["SINGLE", "ONE_POINT_FIVE", "DOUBLE"]
                    patch("spacing", {
                      line_spacing_rule: v,
                      ...(grupA.includes(v) ? { line_spacing: null } : {}),
                    })
                  }}
                />
                <NumberFieldInput
                  label={isGrupC ? "Spasi Baris (pt)" : "Spasi Baris"}
                  value={data.spacing.line_spacing}
                  onChange={(v) => patch("spacing", { line_spacing: v })}
                  disabled={isGrupA}
                  placeholder={isGrupA ? "—" : isGrupC ? "contoh: 14.0" : "contoh: 1.15"}
                  hint={spasiBarisHint}
                />
                <SelectFieldInput
                  label="Alignment Paragraf"
                  value={data.spacing.paragraph_alignment?.toUpperCase() ?? null}
                  options={[
                    { value: "JUSTIFY", label: "Justify" },
                    { value: "LEFT",    label: "Left" },
                    { value: "CENTER",  label: "Center" },
                    { value: "RIGHT",   label: "Right" },
                  ]}
                  onChange={(v) => patch("spacing", { paragraph_alignment: v })}
                />
              </FieldRow>
            </div>
          </div>
        )
      })()}

      {/* ── 4. Struktur Dokumen ── */}
      <div>
        <SectionHeader title="4. Struktur Dokumen" />
        <div className="mt-3 px-1 gap-4">
          <TextFieldInput
            label="Format Nama File"
            value={data.document_structure_proposal.format_nama_file}
            onChange={(v) => patch("document_structure_proposal", { format_nama_file: v })}
          />

          <div>
            <div className="flex items-center justify-between mb-2 mt-3">
              <p className="text-xs font-medium text-muted-foreground">Struktur Dokumen</p>
              <Button
                size="xs"
                variant="outline"
                onClick={() => setShowSectionModal(true)}
              >
                <Pencil className="size-3" />
                Edit
              </Button>
            </div>
            {data.document_structure_proposal.sections.length > 0 ? (
              <div className="rounded-md bg-muted/30 text-xs max-h-48 overflow-y-auto">
                <div className="sticky top-0 flex gap-2 bg-muted/60 px-3 py-1.5 font-medium text-[10px] uppercase tracking-wide text-muted-foreground">
                  <span className="w-28 shrink-0">Jenis</span>
                  <span>Nilai</span>
                </div>
                {data.document_structure_proposal.sections.map((s, i) => {
                  // Renderer docx menerapkan .title() pada item_lampiran dan sub_bab
                  // agar preview frontend sesuai dengan tampilan di dokumen
                  const usesTitleCase = s.type === "item_lampiran" || s.type === "sub_bab"
                  const displayTitle = usesTitleCase ? toTitleCase(s.title) : (s.title ?? "")
                  const displayLampiranNum = usesTitleCase ? toTitleCase(s.lampiran_number) : (s.lampiran_number ?? "")

                  return (
                    <div key={i} className="flex gap-2 px-3 py-1 text-foreground/80 odd:bg-transparent even:bg-muted/20">
                      <span className="w-28 shrink-0 text-muted-foreground">{TYPE_LABEL_MAP[s.type] ?? s.type}</span>
                      <span>
                        {s.type === "bab" && s.number != null ? `BAB ${s.number}` : ""}
                        {s.sub_number ? s.sub_number : ""}
                        {displayLampiranNum ? displayLampiranNum : ""}
                        {displayTitle ? ` ${displayTitle}` : ""}
                      </span>
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">Belum ada section.</p>
            )}
          </div>

          {showSectionModal && (
            <ModalSectionEditor
              sections={data.document_structure_proposal.sections}
              userPlaceholders={data.document_structure_proposal.user_placeholders ?? {}}
              projectId={projectId}
              chapterFormat={data.numbering.chapter_format}
              onSave={(newSections, newPlaceholders) => {
                patch("document_structure_proposal", {
                  sections: newSections,
                  user_placeholders: newPlaceholders,
                })
                setShowSectionModal(false)
              }}
              onClose={() => setShowSectionModal(false)}
            />
          )}
        </div>
      </div>

      {/* ── 5. Penomoran ── */}
      <div>
        <SectionHeader title="5. Penomoran" />
        <div className="mt-3 px-1 flex flex-col gap-4">
          <p className="text-xs font-medium text-muted-foreground">Halaman Pendahuluan</p>
          <FieldRow>
            <SelectFieldInput
              label="Format"
              value={data.numbering.preliminary?.format ?? null}
              options={[
                { value: "lowerRoman",  label: "lowerRoman  (i, ii, iii)" },
                { value: "upperRoman",  label: "upperRoman  (I, II, III)" },
                { value: "decimal",     label: "decimal     (1, 2, 3)" },
                { value: "lowerLetter", label: "lowerLetter (a, b, c)" },
                { value: "upperLetter", label: "upperLetter (A, B, C)" },
              ]}
              onChange={(v) =>
                patch("numbering", {
                  preliminary: { ...data.numbering.preliminary, format: v } as PageNumberConfig,
                })
              }
            />
            <SelectFieldInput
              label="Lokasi"
              value={data.numbering.preliminary?.location?.toUpperCase() ?? null}
              options={[
                { value: "FOOTER", label: "Footer" },
                { value: "HEADER", label: "Header" },
              ]}
              onChange={(v) =>
                patch("numbering", {
                  preliminary: { ...data.numbering.preliminary, location: v } as PageNumberConfig,
                })
              }
            />
            <SelectFieldInput
              label="Alignment"
              value={data.numbering.preliminary?.alignment?.toUpperCase() ?? null}
              options={[
                { value: "CENTER", label: "Center" },
                { value: "RIGHT",  label: "Right" },
                { value: "LEFT",   label: "Left" },
              ]}
              onChange={(v) =>
                patch("numbering", {
                  preliminary: { ...data.numbering.preliminary, alignment: v } as PageNumberConfig,
                })
              }
            />
          </FieldRow>

          <p className="text-xs font-medium text-muted-foreground">Halaman Isi</p>
          <FieldRow>
            <SelectFieldInput
              label="Format"
              value={data.numbering.content?.format ?? null}
              options={[
                { value: "lowerRoman",  label: "lowerRoman  (i, ii, iii)" },
                { value: "upperRoman",  label: "upperRoman  (I, II, III)" },
                { value: "decimal",     label: "decimal     (1, 2, 3)" },
                { value: "lowerLetter", label: "lowerLetter (a, b, c)" },
                { value: "upperLetter", label: "upperLetter (A, B, C)" },
              ]}
              onChange={(v) =>
                patch("numbering", {
                  content: { ...data.numbering.content, format: v } as PageNumberConfig,
                })
              }
            />
            <SelectFieldInput
              label="Lokasi"
              value={data.numbering.content?.location?.toUpperCase() ?? null}
              options={[
                { value: "FOOTER", label: "Footer" },
                { value: "HEADER", label: "Header" },
              ]}
              onChange={(v) =>
                patch("numbering", {
                  content: { ...data.numbering.content, location: v } as PageNumberConfig,
                })
              }
            />
            <SelectFieldInput
              label="Alignment"
              value={data.numbering.content?.alignment?.toUpperCase() ?? null}
              options={[
                { value: "CENTER", label: "Center" },
                { value: "RIGHT",  label: "Right" },
                { value: "LEFT",   label: "Left" },
              ]}
              onChange={(v) =>
                patch("numbering", {
                  content: { ...data.numbering.content, alignment: v } as PageNumberConfig,
                })
              }
            />
          </FieldRow>

          <p className="text-xs font-medium text-muted-foreground">Format Penomoran</p>
          <FieldRow>
            <TextFieldInput
              label="Format Bab"
              value={data.numbering.chapter_format}
              onChange={(v) => patch("numbering", { chapter_format: v })}
            />
            <TextFieldInput
              label="Format Sub-Bab"
              value={data.numbering.sub_chapter_format}
              onChange={(v) => patch("numbering", { sub_chapter_format: v })}
            />

          </FieldRow>
        </div>
      </div>

      {/* ── 6. Gambar & Tabel ── */}
      <div>
        <div className="flex items-center gap-2">
          <SectionHeader title="6. Gambar, Tabel & Lampiran" />
          <button
            type="button"
            onClick={() => setShowFormatInfo((v) => !v)}
            className="text-muted-foreground hover:text-foreground"
            aria-label="Panduan format"
          >
            <Info className="size-3.5" />
          </button>
        </div>

        {showFormatInfo && (
          <div className="mt-2 rounded-md bg-muted/40 px-3 py-2.5 text-xs text-muted-foreground leading-relaxed">
            <p className="mb-2 font-medium text-foreground">Placeholder yang dikenali sistem</p>
            <p className="mb-1.5">
              Hanya placeholder berikut yang akan <strong>diganti otomatis</strong> saat dokumen di-generate.
              Nilai lain dalam kurung kurawal akan muncul <em>apa adanya</em> di dokumen.
            </p>
            <div className="mb-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
              <code className="rounded bg-muted px-1 self-start">{"{n}"}</code>
              <span>Nomor urut gambar / tabel / lampiran (1, 2, 3, …)</span>
              <code className="rounded bg-muted px-1 self-start">{"{title}"}</code>
              <span>Judul gambar / tabel / lampiran</span>
              <code className="rounded bg-muted px-1 self-start">{"{source}"}</code>
              <span>Sumber / credit — khusus gambar</span>
              <code className="rounded bg-muted px-1 self-start">{"{bab}"}</code>
              <span>Nomor BAB induk — khusus tabel</span>
            </div>
            <p className="text-[10px]">
              Contoh gambar:{" "}
              <code className="rounded bg-muted px-1">{"Gambar {n}. {title}."}</code>
              {" "}→ <em>Gambar 1. Arsitektur Sistem.</em>
            </p>
            <p className="mt-0.5 text-[10px]">
              Contoh tabel:{" "}
              <code className="rounded bg-muted px-1">{"Tabel {bab}.{n}. {title}"}</code>
              {" "}→ <em>Tabel 2.1. Rincian Data.</em>
            </p>
            <p className="mt-0.5 text-[10px]">
              Contoh gambar dengan sumber:{" "}
              <code className="rounded bg-muted px-1">{"Gambar {n}. {title} (Sumber: {source})"}</code>
              {" "}→ <em>Gambar 3. Diagram Alir (Sumber: Dokumentasi Tim).</em>
            </p>
            <p className="mt-0.5 text-[10px]">
              Contoh lampiran:{" "}
              <code className="rounded bg-muted px-1">{"Lampiran {n}. {title}"}</code>
              {" "}→ <em>Lampiran 1. Biodata Tim Pengusul.</em>
            </p>
            <p className="mt-1.5 text-[10px] text-muted-foreground">
              <strong>Lampiran:</strong> Format ini digunakan untuk entri di Daftar Lampiran dan heading tiap lampiran.
              Gunakan <code className="rounded bg-muted px-1">{"{n}"}</code> untuk nomor lampiran
              dan <code className="rounded bg-muted px-1">{"{title}"}</code> untuk judul.
            </p>
          </div>
        )}

        <div className="mt-3 px-1">
          <FieldRow>
            <SelectFieldInput
              label="Posisi Keterangan Gambar"
              value={data.figures_and_tables.figure_caption_position?.toUpperCase() ?? null}
              options={[
                { value: "ABOVE", label: "Atas (Above)" },
                { value: "BELOW", label: "Bawah (Below)" },
              ]}
              onChange={(v) => patch("figures_and_tables", { figure_caption_position: v })}
            />
            <SelectFieldInput
              label="Posisi Keterangan Tabel"
              value={data.figures_and_tables.table_caption_position?.toUpperCase() ?? null}
              options={[
                { value: "ABOVE", label: "Atas (Above)" },
                { value: "BELOW", label: "Bawah (Below)" },
              ]}
              onChange={(v) => patch("figures_and_tables", { table_caption_position: v })}
            />
            <SelectFieldInput
              label="Alignment Keterangan Gambar"
              value={data.figures_and_tables.caption_alignment_figure ?? null}
              options={[
                { value: "CENTER",  label: "Center" },
                { value: "LEFT",    label: "Left" },
                { value: "RIGHT",   label: "Right" },
                { value: "JUSTIFY", label: "Justify" },
              ]}
              onChange={(v) => patch("figures_and_tables", { caption_alignment_figure: v as ExtractionPayload["figures_and_tables"]["caption_alignment_figure"] })}
            />
            <SelectFieldInput
              label="Alignment Keterangan Tabel"
              value={data.figures_and_tables.caption_alignment_table ?? null}
              options={[
                { value: "CENTER",  label: "Center" },
                { value: "LEFT",    label: "Left" },
                { value: "RIGHT",   label: "Right" },
                { value: "JUSTIFY", label: "Justify" },
              ]}
              onChange={(v) => patch("figures_and_tables", { caption_alignment_table: v as ExtractionPayload["figures_and_tables"]["caption_alignment_table"] })}
            />
            <SelectFieldInput
              label="Alignment Heading Lampiran"
              value={data.figures_and_tables.caption_alignment_lampiran ?? null}
              options={[
                { value: "CENTER",  label: "Center" },
                { value: "LEFT",    label: "Left" },
                { value: "RIGHT",   label: "Right" },
                { value: "JUSTIFY", label: "Justify" },
              ]}
              onChange={(v) => patch("figures_and_tables", { caption_alignment_lampiran: v as ExtractionPayload["figures_and_tables"]["caption_alignment_lampiran"] })}
            />
            <TextFieldInput
              label="Format Keterangan Gambar"
              value={data.figures_and_tables.caption_format_figure}
              onChange={(v) => patch("figures_and_tables", { caption_format_figure: v })}
            />
            <TextFieldInput
              label="Format Keterangan Tabel"
              value={data.figures_and_tables.caption_format_table}
              onChange={(v) => patch("figures_and_tables", { caption_format_table: v })}
            />
            <TextFieldInput
              label="Format Judul Lampiran"
              value={data.figures_and_tables.caption_format_lampiran}
              onChange={(v) => patch("figures_and_tables", { caption_format_lampiran: v })}
              placeholder="contoh: Lampiran {n}. {title}"
              hint="Gunakan {n} untuk nomor dan {title} untuk judul. Klik ⓘ untuk panduan lengkap."
            />
          </FieldRow>
        </div>
      </div>

      {/* ── 7. Pengaturan Format ── */}
      <div>
        <SectionHeader title="7. Pengaturan Format" />
        <div className="mt-3 px-1">
          <FieldRow>
            <SelectFieldInput
              label="Style Huruf Heading 1"
              value={data.typography.heading_1_case ?? ""}
              options={HEADING_CASE_OPTIONS}
              onChange={(v) => patch("typography", { heading_1_case: (v || null) as ExtractionPayload["typography"]["heading_1_case"] })}
            />
            <SelectFieldInput
              label="Style Huruf Heading 2"
              value={data.typography.heading_2_case ?? "SENTENCE_CASE"}
              options={HEADING_CASE_OPTIONS}
              onChange={(v) => patch("typography", { heading_2_case: (v || null) as ExtractionPayload["typography"]["heading_2_case"] })}
            />
          </FieldRow>
          <FieldRow>
            <SelectFieldInput
              label="Style Huruf Heading 3"
              value={data.typography.heading_3_case ?? "SENTENCE_CASE"}
              options={HEADING_CASE_OPTIONS}
              onChange={(v) => patch("typography", { heading_3_case: (v || null) as ExtractionPayload["typography"]["heading_3_case"] })}
            />
            <SelectFieldInput
              label="Style Huruf Heading 4"
              value={data.typography.heading_4_case ?? "SENTENCE_CASE"}
              options={HEADING_CASE_OPTIONS}
              onChange={(v) => patch("typography", { heading_4_case: (v || null) as ExtractionPayload["typography"]["heading_4_case"] })}
            />
            <SelectFieldInput
              label="Style Huruf Heading 5"
              value={data.typography.heading_5_case ?? "SENTENCE_CASE"}
              options={HEADING_CASE_OPTIONS}
              onChange={(v) => patch("typography", { heading_5_case: (v || null) as ExtractionPayload["typography"]["heading_5_case"] })}
            />
          </FieldRow>
        </div>
      </div>

      {/* ── 8. Batas Halaman ── */}
      <div>
        <SectionHeader title="8. Batas Halaman" />
        <div className="mt-3 px-1">
          <FieldRow>
            <NumberFieldInput
              label="Maks. Halaman Inti"
              value={data.page_count_limits.proposal_halaman_inti_maks}
              onChange={(v) => patch("page_count_limits", { proposal_halaman_inti_maks: v })}
            />
            <SelectFieldInput
              label="Halaman Inti Mulai Dari"
              value={data.page_count_limits.halaman_inti_mulai}
              options={[
                { value: "bab", label: "BAB" },
                { value: "daftar_isi", label: "Daftar Isi" },
                { value: "daftar_pustaka", label: "Daftar Pustaka" },
                { value: "lampiran", label: "Lampiran" },
              ]}
              onChange={(v) => patch("page_count_limits", { halaman_inti_mulai: v })}
            />
            <SelectFieldInput
              label="Halaman Inti Selesai Di"
              value={data.page_count_limits.halaman_inti_selesai}
              options={[
                { value: "bab", label: "BAB" },
                { value: "daftar_isi", label: "Daftar Isi" },
                { value: "daftar_pustaka", label: "Daftar Pustaka" },
                { value: "lampiran", label: "Lampiran" },
              ]}
              onChange={(v) => patch("page_count_limits", { halaman_inti_selesai: v })}
            />
          </FieldRow>
        </div>
      </div>

    </div>
  )
}
