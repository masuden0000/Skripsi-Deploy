"use client"

import { useState } from "react"
import { ChevronDown, ChevronUp } from "lucide-react"
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
    heading_bold: boolean | null
    heading_all_caps: boolean | null
  }
  page_layout: {
    margin_top_cm: number | null
    margin_bottom_cm: number | null
    margin_left_cm: number | null
    margin_right_cm: number | null
    paper_size: string | null
    orientation: string | null
    columns: number | null
  }
  spacing: {
    line_spacing: number | null
    line_spacing_rule: string | null
    paragraph_alignment: string | null
    first_line_indent_cm: number | null
    references_hanging_indent: boolean | null
  }
  document_structure_proposal: {
    halaman_sampul: boolean | null
    halaman_pengesahan: boolean | null
    ringkasan: boolean | null
    sections: SectionItem[]
    max_halaman_inti: number | null
    format_nama_file: string | null
  }
  numbering: {
    preliminary: PageNumberConfig | null
    content: PageNumberConfig | null
    chapter_format: string | null
    sub_chapter_format: string | null
    figure_format: string | null
    table_format: string | null
  }
  figures_and_tables: {
    table_caption_position: string | null
    figure_caption_position: string | null
    caption_format_figure: string | null
    caption_format_table: string | null
    source_required_if_not_own: boolean | null
    max_width_constraint: string | null
  }
  page_count_limits: {
    proposal_halaman_inti_maks: number | null
    definisi_halaman_inti: string | null
    lampiran_excluded: boolean | null
    judul_maks_kata: number | null
  }
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function SectionHeader({
  title,
  open,
  onToggle,
}: {
  title: string
  open: boolean
  onToggle: () => void
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="flex w-full items-center justify-between rounded-lg bg-muted/50 px-4 py-3 text-left text-sm font-semibold transition-colors hover:bg-muted"
    >
      {title}
      {open ? <ChevronUp className="size-4 shrink-0" /> : <ChevronDown className="size-4 shrink-0" />}
    </button>
  )
}

function FieldRow({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">{children}</div>
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
}: {
  label: string
  value: number | null
  onChange: (v: number | null) => void
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <Input
        type="number"
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
        className="h-8 text-sm"
      />
    </div>
  )
}

function SelectFieldInput({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string | null
  options: { value: string; label: string }[]
  onChange: (v: string) => void
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <Select value={value ?? ""} onValueChange={onChange}>
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

// ─── Main Component ──────────────────────────────────────────────────────────

type Props = {
  data: ExtractionPayload
  onChange: (updated: ExtractionPayload) => void
}

const SECTIONS = [
  "Tipografi",
  "Layout Halaman",
  "Spasi",
  "Struktur Dokumen",
  "Penomoran",
  "Gambar & Tabel",
]

export function ExtractionValuesForm({ data, onChange }: Props) {
  const [openSections, setOpenSections] = useState<boolean[]>(SECTIONS.map(() => true))

  function toggle(i: number) {
    setOpenSections((prev) => prev.map((v, idx) => (idx === i ? !v : v)))
  }

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
        <SectionHeader title="1. Tipografi" open={openSections[0]} onToggle={() => toggle(0)} />
        {openSections[0] && (
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
              <BoolFieldInput
                label="Heading Bold"
                value={data.typography.heading_bold}
                onChange={(v) => patch("typography", { heading_bold: v })}
              />
              <BoolFieldInput
                label="Heading All Caps"
                value={data.typography.heading_all_caps}
                onChange={(v) => patch("typography", { heading_all_caps: v })}
              />
            </FieldRow>
          </div>
        )}
      </div>

      {/* ── 2. Layout Halaman ── */}
      <div>
        <SectionHeader title="2. Layout Halaman" open={openSections[1]} onToggle={() => toggle(1)} />
        {openSections[1] && (
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
              />
              <SelectFieldInput
                label="Orientasi"
                value={data.page_layout.orientation}
                options={[
                  { value: "Portrait", label: "Portrait" },
                  { value: "Landscape", label: "Landscape" },
                ]}
                onChange={(v) => patch("page_layout", { orientation: v })}
              />
              <NumberFieldInput
                label="Jumlah Kolom"
                value={data.page_layout.columns}
                onChange={(v) => patch("page_layout", { columns: v })}
              />
            </FieldRow>
          </div>
        )}
      </div>

      {/* ── 3. Spasi ── */}
      <div>
        <SectionHeader title="3. Spasi" open={openSections[2]} onToggle={() => toggle(2)} />
        {openSections[2] && (
          <div className="mt-3 px-1">
            <FieldRow>
              <NumberFieldInput
                label="Spasi Baris"
                value={data.spacing.line_spacing}
                onChange={(v) => patch("spacing", { line_spacing: v })}
              />
              <SelectFieldInput
                label="Aturan Spasi"
                value={data.spacing.line_spacing_rule}
                options={[
                  { value: "single", label: "Single" },
                  { value: "at least", label: "At Least" },
                  { value: "double", label: "Double" },
                  { value: "multiple", label: "Multiple" },
                ]}
                onChange={(v) => patch("spacing", { line_spacing_rule: v })}
              />
              <SelectFieldInput
                label="Alignment Paragraf"
                value={data.spacing.paragraph_alignment}
                options={[
                  { value: "justify", label: "Justify" },
                  { value: "left", label: "Left" },
                  { value: "center", label: "Center" },
                  { value: "right", label: "Right" },
                ]}
                onChange={(v) => patch("spacing", { paragraph_alignment: v })}
              />
              <NumberFieldInput
                label="Indentasi Baris Pertama (cm)"
                value={data.spacing.first_line_indent_cm}
                onChange={(v) => patch("spacing", { first_line_indent_cm: v })}
              />
              <BoolFieldInput
                label="Hanging Indent Referensi"
                value={data.spacing.references_hanging_indent}
                onChange={(v) => patch("spacing", { references_hanging_indent: v })}
              />
            </FieldRow>
          </div>
        )}
      </div>

      {/* ── 4. Struktur Dokumen ── */}
      <div>
        <SectionHeader
          title="4. Struktur Dokumen"
          open={openSections[3]}
          onToggle={() => toggle(3)}
        />
        {openSections[3] && (
          <div className="mt-3 px-1 flex flex-col gap-4">
            <FieldRow>
              <BoolFieldInput
                label="Halaman Sampul"
                value={data.document_structure_proposal.halaman_sampul}
                onChange={(v) =>
                  patch("document_structure_proposal", { halaman_sampul: v })
                }
              />
              <BoolFieldInput
                label="Halaman Pengesahan"
                value={data.document_structure_proposal.halaman_pengesahan}
                onChange={(v) =>
                  patch("document_structure_proposal", { halaman_pengesahan: v })
                }
              />
              <BoolFieldInput
                label="Ringkasan"
                value={data.document_structure_proposal.ringkasan}
                onChange={(v) =>
                  patch("document_structure_proposal", { ringkasan: v })
                }
              />
              <NumberFieldInput
                label="Maks. Halaman Inti"
                value={data.document_structure_proposal.max_halaman_inti}
                onChange={(v) =>
                  patch("document_structure_proposal", { max_halaman_inti: v })
                }
              />
              <TextFieldInput
                label="Format Nama File"
                value={data.document_structure_proposal.format_nama_file}
                onChange={(v) =>
                  patch("document_structure_proposal", { format_nama_file: v })
                }
              />
            </FieldRow>

            {/* Sections (read-only) */}
            {data.document_structure_proposal.sections.length > 0 && (
              <div>
                <p className="mb-2 text-xs font-medium text-muted-foreground">
                  Daftar Section (read-only)
                </p>
                <div className="rounded-md border bg-muted/30 p-3 text-xs space-y-1 max-h-48 overflow-y-auto">
                  {data.document_structure_proposal.sections.map((s, i) => (
                    <div key={i} className="flex gap-2 text-foreground/80">
                      <span className="w-24 shrink-0 text-muted-foreground">{s.type}</span>
                      <span>
                        {s.number != null ? `BAB ${s.number}` : ""}
                        {s.sub_number ? ` ${s.sub_number}` : ""}
                        {s.title ? ` — ${s.title}` : ""}
                        {s.lampiran_number ? ` (${s.lampiran_number})` : ""}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── 5. Penomoran ── */}
      <div>
        <SectionHeader title="5. Penomoran" open={openSections[4]} onToggle={() => toggle(4)} />
        {openSections[4] && (
          <div className="mt-3 px-1 flex flex-col gap-4">
            <p className="text-xs font-medium text-muted-foreground">Halaman Pendahuluan</p>
            <FieldRow>
              <TextFieldInput
                label="Format"
                value={data.numbering.preliminary?.format ?? null}
                onChange={(v) =>
                  patch("numbering", {
                    preliminary: { ...data.numbering.preliminary, format: v } as PageNumberConfig,
                  })
                }
              />
              <SelectFieldInput
                label="Lokasi"
                value={data.numbering.preliminary?.location ?? null}
                options={[
                  { value: "footer", label: "Footer" },
                  { value: "header", label: "Header" },
                ]}
                onChange={(v) =>
                  patch("numbering", {
                    preliminary: { ...data.numbering.preliminary, location: v } as PageNumberConfig,
                  })
                }
              />
              <SelectFieldInput
                label="Alignment"
                value={data.numbering.preliminary?.alignment ?? null}
                options={[
                  { value: "center", label: "Center" },
                  { value: "right", label: "Right" },
                  { value: "left", label: "Left" },
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
              <TextFieldInput
                label="Format"
                value={data.numbering.content?.format ?? null}
                onChange={(v) =>
                  patch("numbering", {
                    content: { ...data.numbering.content, format: v } as PageNumberConfig,
                  })
                }
              />
              <SelectFieldInput
                label="Lokasi"
                value={data.numbering.content?.location ?? null}
                options={[
                  { value: "footer", label: "Footer" },
                  { value: "header", label: "Header" },
                ]}
                onChange={(v) =>
                  patch("numbering", {
                    content: { ...data.numbering.content, location: v } as PageNumberConfig,
                  })
                }
              />
              <SelectFieldInput
                label="Alignment"
                value={data.numbering.content?.alignment ?? null}
                options={[
                  { value: "center", label: "Center" },
                  { value: "right", label: "Right" },
                  { value: "left", label: "Left" },
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
              <TextFieldInput
                label="Format Gambar"
                value={data.numbering.figure_format}
                onChange={(v) => patch("numbering", { figure_format: v })}
              />
              <TextFieldInput
                label="Format Tabel"
                value={data.numbering.table_format}
                onChange={(v) => patch("numbering", { table_format: v })}
              />
            </FieldRow>
          </div>
        )}
      </div>

      {/* ── 6. Gambar & Tabel ── */}
      <div>
        <SectionHeader
          title="6. Gambar & Tabel"
          open={openSections[5]}
          onToggle={() => toggle(5)}
        />
        {openSections[5] && (
          <div className="mt-3 px-1">
            <FieldRow>
              <SelectFieldInput
                label="Posisi Keterangan Gambar"
                value={data.figures_and_tables.figure_caption_position}
                options={[
                  { value: "atas", label: "Atas" },
                  { value: "bawah", label: "Bawah" },
                ]}
                onChange={(v) =>
                  patch("figures_and_tables", { figure_caption_position: v })
                }
              />
              <SelectFieldInput
                label="Posisi Keterangan Tabel"
                value={data.figures_and_tables.table_caption_position}
                options={[
                  { value: "atas", label: "Atas" },
                  { value: "bawah", label: "Bawah" },
                ]}
                onChange={(v) =>
                  patch("figures_and_tables", { table_caption_position: v })
                }
              />
              <TextFieldInput
                label="Format Keterangan Gambar"
                value={data.figures_and_tables.caption_format_figure}
                onChange={(v) =>
                  patch("figures_and_tables", { caption_format_figure: v })
                }
              />
              <TextFieldInput
                label="Format Keterangan Tabel"
                value={data.figures_and_tables.caption_format_table}
                onChange={(v) =>
                  patch("figures_and_tables", { caption_format_table: v })
                }
              />
              <TextFieldInput
                label="Batas Lebar Maksimum"
                value={data.figures_and_tables.max_width_constraint}
                onChange={(v) =>
                  patch("figures_and_tables", { max_width_constraint: v })
                }
              />
              <BoolFieldInput
                label="Sumber Wajib (bukan milik sendiri)"
                value={data.figures_and_tables.source_required_if_not_own}
                onChange={(v) =>
                  patch("figures_and_tables", { source_required_if_not_own: v })
                }
              />
            </FieldRow>
          </div>
        )}
      </div>

    </div>
  )
}
