"use client"

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
    max_width_constraint: string | null
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

export function ExtractionValuesForm({ data, onChange }: Props) {
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
          </FieldRow>
        </div>
      </div>

      {/* ── 3. Spasi ── */}
      <div>
        <SectionHeader title="3. Spasi" />
        <div className="mt-3 px-1">
          <FieldRow>
            <NumberFieldInput
              label="Spasi Baris"
              value={data.spacing.line_spacing}
              onChange={(v) => patch("spacing", { line_spacing: v })}
            />
            <SelectFieldInput
              label="Aturan Spasi"
              value={data.spacing.line_spacing_rule?.toUpperCase() ?? null}
              options={[
                { value: "SINGLE",   label: "Single" },
                { value: "DOUBLE",   label: "Double" },
                { value: "MULTIPLE", label: "Multiple" },
                { value: "AT_LEAST", label: "At Least" },
                { value: "EXACT",    label: "Exact" },
              ]}
              onChange={(v) => patch("spacing", { line_spacing_rule: v })}
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
            <NumberFieldInput
              label="Indentasi Baris Pertama (cm)"
              value={data.spacing.first_line_indent_cm}
              onChange={(v) => patch("spacing", { first_line_indent_cm: v })}
            />
          </FieldRow>
        </div>
      </div>

      {/* ── 4. Struktur Dokumen ── */}
      <div>
        <SectionHeader title="4. Struktur Dokumen" />
        <div className="mt-3 px-1 flex flex-col gap-4">
          <FieldRow>
            <NumberFieldInput
              label="Maks. Halaman Inti"
              value={data.document_structure_proposal.max_halaman_inti}
              onChange={(v) => patch("document_structure_proposal", { max_halaman_inti: v })}
            />
            <TextFieldInput
              label="Format Nama File"
              value={data.document_structure_proposal.format_nama_file}
              onChange={(v) => patch("document_structure_proposal", { format_nama_file: v })}
            />
          </FieldRow>

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
      </div>

      {/* ── 6. Gambar & Tabel ── */}
      <div>
        <SectionHeader title="6. Gambar & Tabel" />
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
              label="Batas Lebar Maksimum"
              value={data.figures_and_tables.max_width_constraint}
              onChange={(v) => patch("figures_and_tables", { max_width_constraint: v })}
            />
          </FieldRow>
        </div>
      </div>

      {/* ── 7. Pengaturan Format ── */}
      <div>
        <SectionHeader title="7. Pengaturan Format" />
        <div className="mt-3 px-1 flex flex-col">
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
          <BoolFieldInput
            label="Hanging Indent Referensi"
            value={data.spacing.references_hanging_indent}
            onChange={(v) => patch("spacing", { references_hanging_indent: v })}
          />
          <BoolFieldInput
            label="Halaman Sampul"
            value={data.document_structure_proposal.halaman_sampul}
            onChange={(v) => patch("document_structure_proposal", { halaman_sampul: v })}
          />
          <BoolFieldInput
            label="Halaman Pengesahan"
            value={data.document_structure_proposal.halaman_pengesahan}
            onChange={(v) => patch("document_structure_proposal", { halaman_pengesahan: v })}
          />
          <BoolFieldInput
            label="Ringkasan"
            value={data.document_structure_proposal.ringkasan}
            onChange={(v) => patch("document_structure_proposal", { ringkasan: v })}
          />
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
