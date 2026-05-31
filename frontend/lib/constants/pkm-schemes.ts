/**
 * Daftar skema PKM sebagai single source of truth.
 * Dipakai di: admin/proposal (buat dokumen), reviewer/validation (validasi dokumen).
 *
 * `value` harus cocok dengan kolom `projects.skema` di database.
 */
export const PKM_SCHEMES = [
  { value: "PKM-RE",  label: "PKM-RE: Riset Eksakta" },
  { value: "PKM-RSH", label: "PKM-RSH: Riset Sosial Humaniora" },
  { value: "PKM-K",   label: "PKM-K: Kewirausahaan" },
  { value: "PKM-PM",  label: "PKM-PM: Pengabdian Kepada Masyarakat" },
  { value: "PKM-PI",  label: "PKM-PI: Penerapan Iptek" },
  { value: "PKM-KC",  label: "PKM-KC: Karsa Cipta" },
  { value: "PKM-KI",  label: "PKM-KI: Karya Inovatif" },
  { value: "PKM-VGK", label: "PKM-VGK: Video Gagasan Konstruktif" },
  { value: "PKM-AI",  label: "PKM-AI: Artikel Ilmiah" },
  { value: "PKM-GFT", label: "PKM-GFT: Gagasan Futuristik Tertulis" },
] as const

export type PkmSchemeValue = (typeof PKM_SCHEMES)[number]["value"]

/** Kembalikan label lengkap dari value, atau value itu sendiri jika tidak ditemukan. */
export function getPkmSchemeLabel(value: string): string {
  return PKM_SCHEMES.find((s) => s.value === value)?.label ?? value
}
