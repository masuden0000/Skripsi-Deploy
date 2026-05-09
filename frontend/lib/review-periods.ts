export type ReviewPeriod = {
  id: string
  nama: string
  tanggalMulai: string
  tanggalSelesai: string
  createdAt: string
  updatedAt: string
}

export type ReviewPeriodFormData = {
  nama: string
  tanggalMulai: string
  tanggalSelesai: string
}

const tanggalFormatter = new Intl.DateTimeFormat("id-ID", {
  day: "numeric",
  month: "long",
  year: "numeric",
})

const waktuFormatter = new Intl.DateTimeFormat("id-ID", {
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
})

function parseDateOnly(value: string) {
  return new Date(`${value}T00:00:00`)
}

export function formatTanggal(value: string) {
  return tanggalFormatter.format(parseDateOnly(value))
}

export function formatTanggalDanWaktu(value: string) {
  const tanggal = new Date(value)
  const jam = waktuFormatter.format(tanggal).replace(":", ".")
  return `${tanggalFormatter.format(tanggal)}, ${jam}`
}

export function isOngoingReviewPeriod(periode: Pick<ReviewPeriod, "tanggalSelesai">) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  return parseDateOnly(periode.tanggalSelesai) >= today
}

export function hasReviewPeriodBeenUpdated(
  periode: Pick<ReviewPeriod, "createdAt" | "updatedAt">
) {
  return periode.updatedAt !== periode.createdAt
}
