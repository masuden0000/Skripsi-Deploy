import { adminClient } from "../config/supabase.js"
import { AppError } from "../utils/app-error.js"

const REVIEW_PERIOD_TABLE = "pkm_review_periods"
const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

function isValidDateString(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return false
  }

  const parsed = new Date(`${value}T00:00:00Z`)
  return !Number.isNaN(parsed.getTime())
}

function validateReviewPeriodId(id) {
  if (!UUID_PATTERN.test(id)) {
    throw new AppError("Periode review tidak ditemukan.", 404)
  }
}

function mapReviewPeriod(row) {
  return {
    id: row.id,
    nama: row.nama,
    tanggalMulai: row.tanggal_mulai,
    tanggalSelesai: row.tanggal_selesai,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  }
}

function normalizeReviewPeriodPayload(payload) {
  const nama = typeof payload.nama === "string" ? payload.nama.trim() : ""
  const tanggalMulai = payload.tanggalMulai
  const tanggalSelesai = payload.tanggalSelesai

  if (!nama) {
    throw new AppError("Nama periode wajib diisi.", 400)
  }

  if (!isValidDateString(tanggalMulai)) {
    throw new AppError("Tanggal mulai tidak valid.", 400)
  }

  if (!isValidDateString(tanggalSelesai)) {
    throw new AppError("Tanggal selesai tidak valid.", 400)
  }

  if (tanggalSelesai < tanggalMulai) {
    throw new AppError("Tanggal selesai tidak boleh lebih awal dari tanggal mulai.", 400)
  }

  return {
    nama,
    tanggal_mulai: tanggalMulai,
    tanggal_selesai: tanggalSelesai,
  }
}

function handleDatabaseError(error, fallbackMessage) {
  if (!error) {
    return
  }

  if (error.code === "PGRST116") {
    throw new AppError("Periode review tidak ditemukan.", 404)
  }

  throw new AppError(fallbackMessage, 500)
}

export async function listReviewPeriods() {
  const { data, error } = await adminClient
    .from(REVIEW_PERIOD_TABLE)
    .select("id, nama, tanggal_mulai, tanggal_selesai, created_at, updated_at")
    .order("tanggal_mulai", { ascending: false })

  handleDatabaseError(error, "Gagal mengambil daftar periode review.")

  return (data ?? []).map(mapReviewPeriod)
}

export async function getReviewPeriodById(id) {
  validateReviewPeriodId(id)

  const { data, error } = await adminClient
    .from(REVIEW_PERIOD_TABLE)
    .select("id, nama, tanggal_mulai, tanggal_selesai, created_at, updated_at")
    .eq("id", id)
    .single()

  handleDatabaseError(error, "Gagal mengambil detail periode review.")

  return mapReviewPeriod(data)
}

export async function createReviewPeriod(payload) {
  const values = normalizeReviewPeriodPayload(payload)

  const { data, error } = await adminClient
    .from(REVIEW_PERIOD_TABLE)
    .insert(values)
    .select("id, nama, tanggal_mulai, tanggal_selesai, created_at, updated_at")
    .single()

  handleDatabaseError(error, "Gagal membuat periode review.")

  return mapReviewPeriod(data)
}

export async function updateReviewPeriod(id, payload) {
  validateReviewPeriodId(id)
  const values = normalizeReviewPeriodPayload(payload)

  const { data, error } = await adminClient
    .from(REVIEW_PERIOD_TABLE)
    .update(values)
    .eq("id", id)
    .select("id, nama, tanggal_mulai, tanggal_selesai, created_at, updated_at")
    .single()

  handleDatabaseError(error, "Gagal memperbarui periode review.")

  return mapReviewPeriod(data)
}

export async function deleteReviewPeriod(id) {
  validateReviewPeriodId(id)

  const { data, error } = await adminClient
    .from(REVIEW_PERIOD_TABLE)
    .delete()
    .eq("id", id)
    .select("id, nama, tanggal_mulai, tanggal_selesai, created_at, updated_at")
    .single()

  handleDatabaseError(error, "Gagal menghapus periode review.")

  return mapReviewPeriod(data)
}