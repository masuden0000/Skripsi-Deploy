"use client"

import { useEffect, useRef, useState } from "react"
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core"
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { GripVertical, Plus, Trash2, X } from "lucide-react"
import { Button } from "@/components/ui/button"

// ─── Types ────────────────────────────────────────────────────────────────────

export type SectionItem = {
  type: string
  required: boolean | null
  number: number | null
  sub_number: string | null
  title: string | null
  lampiran_number: string | null
  is_major_section: boolean
}

type Props = {
  sections: SectionItem[]
  userPlaceholders: Record<string, string>
  projectId?: string | null
  chapterFormat?: string | null
  onSave: (sections: SectionItem[], userPlaceholders: Record<string, string>) => void
  onClose: () => void
}

// ─── Constants ────────────────────────────────────────────────────────────────

const TYPE_LABELS: Record<string, string> = {
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

const TYPE_BADGE_COLOR: Record<string, string> = {
  bab: "bg-blue-100 text-blue-700",
  sub_bab: "bg-blue-50 text-blue-600",
  daftar_isi: "bg-slate-100 text-slate-600",
  daftar_gambar: "bg-slate-100 text-slate-600",
  daftar_tabel: "bg-slate-100 text-slate-600",
  daftar_lampiran: "bg-slate-100 text-slate-600",
  daftar_pustaka: "bg-red-100 text-red-600",
  lampiran: "bg-amber-100 text-amber-700",
  item_lampiran: "bg-amber-50 text-amber-600",
}

// Types whose title is fixed (not editable)
const FIXED_TITLE = new Set([
  "daftar_isi",
  "daftar_gambar",
  "daftar_tabel",
  "daftar_lampiran",
  "daftar_pustaka",
  "lampiran",
])

// ─── Helpers ─────────────────────────────────────────────────────────────────

function isTitleEditable(s: SectionItem): boolean {
  return !FIXED_TITLE.has(s.type)
}

function isDeletable(s: SectionItem): boolean {
  return s.required !== true
}

/** Auto-generate sub_number for new sub_bab at insertIndex */
function computeSubNumber(sections: SectionItem[], insertIndex: number): string {
  const above = sections.slice(0, insertIndex)
  const parentBab = [...above].reverse().find((s) => s.type === "bab")
  if (!parentBab || parentBab.number == null) return "?.?"
  const siblingCount = above.filter(
    (s) => s.type === "sub_bab" && s.sub_number?.startsWith(`${parentBab.number}.`)
  ).length
  return `${parentBab.number}.${siblingCount + 1}`
}

/** Recalculate all sub_number values after reorder/delete */
function recalculateSubNumbers(sections: SectionItem[]): SectionItem[] {
  const result = [...sections]
  const babCounters: Record<number, number> = {}
  for (let i = 0; i < result.length; i++) {
    if (result[i].type === "sub_bab") {
      const parentBab = result.slice(0, i).reverse().find((s) => s.type === "bab")
      const babNum = parentBab?.number ?? 0
      babCounters[babNum] = (babCounters[babNum] ?? 0) + 1
      result[i] = { ...result[i], sub_number: `${babNum}.${babCounters[babNum]}` }
    }
  }
  return result
}

/** Generate instruction key matching Python's make_instruction_key logic */
function makeInstructionKey(type: string, title: string | null, number?: number | null): string {
  const normalized = ((title || "").trim().toUpperCase()).replace(/\s+/g, " ")
  if (type === "bab") return `bab::${number ?? 0}::${normalized}`
  return `${type}::${normalized}`
}

/** Build instruction key for any SectionItem — must match canonical Python make_instruction_key logic */
function getSectionKey(s: SectionItem, chapterFormat = "BAB {n}"): string {
  if (s.type === "bab") {
    const babLabel = chapterFormat.replace("{n}", String(s.number ?? 0))
    const heading = `${babLabel} ${s.title || ""}`.trim()
    return makeInstructionKey("bab", heading, s.number)
  }
  if (s.type === "sub_bab")
    return makeInstructionKey("sub_bab", `${s.sub_number || ""} ${s.title || ""}`.trim())
  if (s.type === "item_lampiran")
    return makeInstructionKey("item_lampiran", `${s.lampiran_number || ""}. ${s.title || ""}`.trim())
  return makeInstructionKey(s.type, s.title)
}

/** Human-readable label for a section (used in Placeholder "Mengacu") */
function getSectionLabel(s: SectionItem): string {
  if (s.type === "bab") return `BAB ${s.number ?? "?"} ${s.title || ""}`.trim()
  if (s.type === "sub_bab") return `${s.sub_number || "?"} ${s.title || ""}`.trim()
  if (s.type === "item_lampiran") return `${s.lampiran_number || ""} ${s.title || ""}`.trim()
  return s.title || TYPE_LABELS[s.type] || s.type.toUpperCase()
}

/** Generate a unique dnd id per section */
function sectionDndId(s: SectionItem, idx: number): string {
  return `${s.type}-${idx}`
}

// ─── SortableRow ──────────────────────────────────────────────────────────────

function SortableRow({
  id,
  section,
  onTitleChange,
  onDelete,
}: {
  id: string
  section: SectionItem
  onTitleChange: (title: string) => void
  onDelete: () => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id,
  })
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-2 rounded-md bg-muted/30 px-2 py-1.5 text-xs"
    >
      {/* Drag handle */}
      <button
        className="cursor-grab touch-none text-muted-foreground hover:text-foreground"
        {...attributes}
        {...listeners}
        aria-label="drag"
      >
        <GripVertical className="size-3.5" />
      </button>

      {/* Type badge */}
      <span
        className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${TYPE_BADGE_COLOR[section.type] ?? "bg-muted text-foreground"}`}
      >
        {TYPE_LABELS[section.type] ?? section.type}
      </span>

      {/* Sub-number / lampiran-number display */}
      {section.sub_number && (
        <span className="shrink-0 text-muted-foreground">{section.sub_number}</span>
      )}
      {section.lampiran_number && (
        <span className="shrink-0 text-muted-foreground">{section.lampiran_number}</span>
      )}
      {section.number != null && section.type === "bab" && (
        <span className="shrink-0 text-muted-foreground">BAB {section.number}</span>
      )}

      {/* Title — editable or fixed */}
      {isTitleEditable(section) ? (
        <input
          className="min-w-0 flex-1 bg-transparent outline-none placeholder:text-muted-foreground"
          value={section.title ?? ""}
          onChange={(e) => onTitleChange(e.target.value)}
          placeholder="Judul section..."
        />
      ) : (
        <span className="min-w-0 flex-1 text-muted-foreground">{section.title || "—"}</span>
      )}

      {/* Delete button */}
      {isDeletable(section) && (
        <button
          className="ml-auto shrink-0 text-muted-foreground hover:text-destructive"
          onClick={onDelete}
          aria-label="hapus"
        >
          <Trash2 className="size-3.5" />
        </button>
      )}
    </div>
  )
}

// ─── Tab 1: Struktur Dokumen ──────────────────────────────────────────────────

function StrukturTab({
  sections,
  onChange,
}: {
  sections: SectionItem[]
  onChange: (s: SectionItem[]) => void
}) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  const ids = sections.map((s, i) => sectionDndId(s, i))

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIndex = ids.indexOf(active.id as string)
    const newIndex = ids.indexOf(over.id as string)
    const reordered = arrayMove(sections, oldIndex, newIndex)
    onChange(recalculateSubNumbers(reordered))
  }

  function updateTitle(idx: number, title: string) {
    const updated = sections.map((s, i) => (i === idx ? { ...s, title } : s))
    onChange(updated)
  }

  function deleteSection(idx: number) {
    const updated = sections.filter((_, i) => i !== idx)
    onChange(recalculateSubNumbers(updated))
  }

  function addSubBab(afterBabIndex: number) {
    const insertIndex = (() => {
      let i = afterBabIndex + 1
      while (i < sections.length && sections[i].type === "sub_bab") i++
      return i
    })()
    const sub_number = computeSubNumber(sections, insertIndex)
    const newSubBab: SectionItem = {
      type: "sub_bab",
      required: null,
      number: null,
      sub_number,
      title: "",
      lampiran_number: null,
      is_major_section: true,
    }
    const updated = [
      ...sections.slice(0, insertIndex),
      newSubBab,
      ...sections.slice(insertIndex),
    ]
    onChange(recalculateSubNumbers(updated))
  }

  function addItemLampiran(afterLampiranIndex: number) {
    const insertIndex = (() => {
      let i = afterLampiranIndex + 1
      while (i < sections.length && sections[i].type === "item_lampiran") i++
      return i
    })()
    const existingCount = sections.filter((s) => s.type === "item_lampiran").length
    const newItem: SectionItem = {
      type: "item_lampiran",
      required: null,
      number: null,
      sub_number: null,
      title: "",
      lampiran_number: `Lampiran ${existingCount + 1}`,
      is_major_section: false,
    }
    const updated = [
      ...sections.slice(0, insertIndex),
      newItem,
      ...sections.slice(insertIndex),
    ]
    onChange(updated)
  }

  function addBab() {
    // Hitung nomor BAB berikutnya
    const existingBabNums = sections
      .filter((s) => s.type === "bab" && s.number != null)
      .map((s) => s.number as number)
    const nextNum = existingBabNums.length > 0 ? Math.max(...existingBabNums) + 1 : 1

    // Sisipkan sebelum daftar_pustaka / lampiran / item_lampiran / daftar_lampiran di akhir
    const trailingTypes = new Set(["daftar_pustaka", "lampiran", "item_lampiran", "daftar_lampiran"])
    let insertIndex = sections.length
    while (insertIndex > 0 && trailingTypes.has(sections[insertIndex - 1].type)) {
      insertIndex--
    }

    const newBab: SectionItem = {
      type: "bab",
      required: null,
      number: nextNum,
      sub_number: null,
      title: "",
      lampiran_number: null,
      is_major_section: true,
    }
    onChange([...sections.slice(0, insertIndex), newBab, ...sections.slice(insertIndex)])
  }

  return (
    <div className="flex flex-col gap-3">
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={ids} strategy={verticalListSortingStrategy}>
          <div className="flex flex-col gap-1.5">
            {sections.map((s, i) => (
              <div key={ids[i]}>
                <SortableRow
                  id={ids[i]}
                  section={s}
                  onTitleChange={(title) => updateTitle(i, title)}
                  onDelete={() => deleteSection(i)}
                />
                {/* "+ Sub-BAB" button after each BAB */}
                {s.type === "bab" && (
                  <button
                    className="mt-1 ml-8 flex items-center gap-1 text-[10px] text-muted-foreground hover:text-primary"
                    onClick={() => addSubBab(i)}
                  >
                    <Plus className="size-3" /> Sub-BAB
                  </button>
                )}
                {/* "+ Item Lampiran" button after lampiran section */}
                {s.type === "lampiran" && (
                  <button
                    className="mt-1 ml-8 flex items-center gap-1 text-[10px] text-muted-foreground hover:text-primary"
                    onClick={() => addItemLampiran(i)}
                  >
                    <Plus className="size-3" /> Item Lampiran
                  </button>
                )}
              </div>
            ))}
          </div>
        </SortableContext>
      </DndContext>

      {/* Tambah BAB baru */}
      <button
        className="flex items-center gap-1 self-start text-[11px] text-muted-foreground hover:text-primary"
        onClick={addBab}
      >
        <Plus className="size-3" /> Tambah BAB
      </button>
    </div>
  )
}

// ─── Tab 2: Placeholder ───────────────────────────────────────────────────────

type PlaceholderData = {
  generated: Record<string, string>
  user_overrides: Record<string, string>
}

function PlaceholderTab({
  sections,
  userPlaceholders,
  projectId,
  chapterFormat,
  onChange,
}: {
  sections: SectionItem[]
  userPlaceholders: Record<string, string>
  projectId?: string | null
  chapterFormat?: string | null
  onChange: (overrides: Record<string, string>) => void
}) {
  const [placeholderData, setPlaceholderData] = useState<PlaceholderData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fetchedRef = useRef(false)
  const [addForm, setAddForm] = useState<{ sectionIdx: number; value: string } | null>(null)

  useEffect(() => {
    if (!projectId || fetchedRef.current) return
    fetchedRef.current = true
    setLoading(true)
    fetch(`/api/projects/${projectId}/placeholders`)
      .then((r) => r.json())
      .then((json) => {
        if (json.success) setPlaceholderData(json.data)
        else setError(json.error ?? "Gagal memuat placeholder")
      })
      .catch(() => setError("Gagal terhubung ke server"))
      .finally(() => setLoading(false))
  }, [projectId])

  const fmt = chapterFormat || "BAB {n}"

  // Auto-generated rows from relevant section types
  const PLACEHOLDER_EXCLUDED = new Set(["daftar_isi", "daftar_gambar", "daftar_tabel", "daftar_lampiran"])

  const autoRows = sections
    .filter((s) =>
      ["bab", "sub_bab", "daftar_pustaka", "lampiran", "item_lampiran"].includes(s.type)
    )
    .map((s) => {
      const key = getSectionKey(s, fmt)
      const generated = placeholderData?.generated?.[key] ?? ""
      const userValue = userPlaceholders[key] ?? ""
      const label = getSectionLabel(s)
      return { key, label, generated, userValue }
    })

  // Extra rows: user-added placeholders not covered by auto rows
  const autoKeys = new Set(autoRows.map((r) => r.key))
  const extraRows = Object.entries(userPlaceholders)
    .filter(([key]) => !autoKeys.has(key))
    .map(([key, userValue]) => {
      const parts = key.split("::")
      const label = parts[parts.length - 1] || key
      return { key, label, generated: "", userValue }
    })

  const allRows = [...autoRows, ...extraRows]

  function handleChange(key: string, value: string) {
    const updated = { ...userPlaceholders }
    if (value.trim() === "") {
      delete updated[key]
    } else {
      updated[key] = value
    }
    onChange(updated)
  }

  function handleAdd() {
    if (addForm === null) return
    const s = sections[addForm.sectionIdx]
    if (!s || !addForm.value.trim() || PLACEHOLDER_EXCLUDED.has(s.type)) return
    const key = getSectionKey(s, fmt)
    onChange({ ...userPlaceholders, [key]: addForm.value.trim() })
    setAddForm(null)
  }

  if (!projectId) {
    return (
      <p className="py-4 text-center text-xs text-muted-foreground">
        Project ID tidak tersedia.
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {loading && (
        <p className="py-2 text-center text-xs text-muted-foreground">Memuat placeholder...</p>
      )}
      {error && <p className="py-2 text-xs text-destructive">{error}</p>}

      {allRows.map(({ key, label, generated, userValue }) => (
        <div key={key} className="flex flex-col gap-1.5 rounded-md bg-muted/30 p-3">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
              Mengacu
            </span>
            <span className="text-xs font-medium">{label}</span>
            {userValue && (
              <span className="ml-auto text-[10px] text-primary">diubah</span>
            )}
          </div>
          <textarea
            className="min-h-[72px] w-full resize-none rounded bg-muted/50 px-2.5 py-1.5 text-xs outline-none focus:ring-1 focus:ring-ring/30"
            placeholder={generated || "Belum ada placeholder — ketik untuk menambahkan override"}
            value={userValue}
            onChange={(e) => handleChange(key, e.target.value)}
          />
          {userValue && (
            <button
              className="self-end text-[10px] text-muted-foreground hover:text-destructive"
              onClick={() => handleChange(key, "")}
            >
              Hapus
            </button>
          )}
        </div>
      ))}

      {/* Add placeholder form */}
      {addForm !== null ? (
        <div className="flex flex-col gap-2 rounded-md bg-muted/30 p-3">
          <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            Tambah Placeholder
          </span>
          <select
            className="rounded bg-muted/50 px-2.5 py-1.5 text-xs outline-none"
            value={addForm.sectionIdx}
            onChange={(e) => setAddForm({ ...addForm, sectionIdx: Number(e.target.value) })}
          >
            {sections.map((s, i) =>
              PLACEHOLDER_EXCLUDED.has(s.type) ? null : (
                <option key={i} value={i}>
                  {getSectionLabel(s) || TYPE_LABELS[s.type] || s.type}
                </option>
              )
            )}
          </select>
          <textarea
            className="min-h-[60px] w-full resize-none rounded bg-muted/50 px-2.5 py-1.5 text-xs outline-none focus:ring-1 focus:ring-ring/30"
            placeholder="Isi placeholder..."
            value={addForm.value}
            onChange={(e) => setAddForm({ ...addForm, value: e.target.value })}
          />
          <div className="flex justify-end gap-3">
            <button
              className="text-[11px] text-muted-foreground hover:text-foreground"
              onClick={() => setAddForm(null)}
            >
              Batal
            </button>
            <button
              className="text-[11px] font-medium text-primary hover:text-primary/80"
              onClick={handleAdd}
            >
              Tambah
            </button>
          </div>
        </div>
      ) : (
        <button
          className="flex items-center gap-1 self-start text-[11px] text-muted-foreground hover:text-primary"
          onClick={() => {
            const firstAllowed = sections.findIndex((s) => !PLACEHOLDER_EXCLUDED.has(s.type))
            setAddForm({ sectionIdx: firstAllowed >= 0 ? firstAllowed : 0, value: "" })
          }}
        >
          <Plus className="size-3" /> Tambah Placeholder
        </button>
      )}
    </div>
  )
}

// ─── Main Modal ───────────────────────────────────────────────────────────────

export function ModalSectionEditor({
  sections,
  userPlaceholders,
  projectId,
  chapterFormat,
  onSave,
  onClose,
}: Props) {
  const [tab, setTab] = useState<"struktur" | "placeholder">("struktur")
  const [localSections, setLocalSections] = useState<SectionItem[]>(sections)
  const [localPlaceholders, setLocalPlaceholders] =
    useState<Record<string, string>>(userPlaceholders)

  // Close on Escape
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose()
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="flex max-h-[90vh] w-full max-w-2xl flex-col rounded-xl bg-background shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 pb-2 pt-4">
          <h2 className="text-sm font-semibold">Edit Struktur Dokumen</h2>
          <button
            className="text-muted-foreground hover:text-foreground"
            onClick={onClose}
            aria-label="tutup"
          >
            <X className="size-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-0 px-5">
          {(["struktur", "placeholder"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`border-b-2 px-4 py-2.5 text-xs font-medium transition-colors ${
                tab === t
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {t === "struktur" ? "Struktur Dokumen" : "Placeholder"}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {tab === "struktur" ? (
            <StrukturTab sections={localSections} onChange={setLocalSections} />
          ) : (
            <PlaceholderTab
              sections={localSections}
              userPlaceholders={localPlaceholders}
              projectId={projectId}
              chapterFormat={chapterFormat}
              onChange={setLocalPlaceholders}
            />
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-5 pb-4 pt-2">
          <Button variant="outline" size="sm" onClick={onClose}>
            Batal
          </Button>
          <Button
            size="sm"
            onClick={() => onSave(localSections, localPlaceholders)}
          >
            Simpan
          </Button>
        </div>
      </div>
    </div>
  )
}
