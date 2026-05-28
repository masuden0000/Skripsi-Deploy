/**
 * Daftar skema PKM sebagai single source of truth.
 * Dipakai di: admin/proposal (buat dokumen), reviewer/validation (validasi dokumen).
 *
 * `value` harus cocok dengan kolom `projects.skema` di database.
 */
export const PKM_SCHEMES = [
  { value: "pkm-re",  label: "PKM-RE: Riset Eksakta" },
  { value: "pkm-rsh", label: "PKM-RSH: Riset Sosial Humaniora" },
  { value: "pkm-k",   label: "PKM-K: Kewirausahaan" },
  { value: "pkm-pm",  label: "PKM-PM: Pengabdian Kepada Masyarakat" },
  { value: "pkm-pi",  label: "PKM-PI: Penerapan Iptek" },
  { value: "pkm-kc",  label: "PKM-KC: Karsa Cipta" },
  { value: "pkm-ki",  label: "PKM-KI: Karya Inovatif" },
  { value: "pkm-vgk", label: "PKM-VGK: Video Gagasan Konstruktif" },
  { value: "pkm-ai",  label: "PKM-AI: Artikel Ilmiah" },
  { value: "pkm-gft", label: "PKM-GFT: Gagasan Futuristik Tertulis" },
] as const

export type PkmSchemeValue = (typeof PKM_SCHEMES)[number]["value"]

/** Kembalikan label lengkap dari value, atau value itu sendiri jika tidak ditemukan. */
export function getPkmSchemeLabel(value: string): string {
  return PKM_SCHEMES.find((s) => s.value === value)?.label ?? value
}
