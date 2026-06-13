/**
 * Router Express untuk endpoint PKM (Program Kreativitas Mahasiswa).
 *
 * Peran dalam pipeline:
 *   - GET  /api/pkm/schemas        → Baca daftar skema PKM langsung dari Supabase
 *   - POST /api/pkm/validation/run → Proxy multipart/form-data ke FastAPI ai-backend
 *
 * Frontend tidak memanggil ai-backend langsung; semua request melewati Express ini.
 * Digunakan oleh: frontend/lib/api/pkm.ts
 */
import { Router } from "express"
import { adminClient } from "../config/supabase.js"
import { env } from "../config/env.js"

const router = Router()

// Helper: parse response dari ai-backend secara aman (ai-backend bisa return non-JSON saat error)
async function parseAiResponse(aiResponse) {
  const text = await aiResponse.text()
  try {
    return { data: JSON.parse(text), status: aiResponse.status }
  } catch {
    return {
      data: { error: text || "AI backend returned non-JSON response" },
      status: aiResponse.status || 502,
    }
  }
}

// GET /api/pkm/schemas - Daftar skema PKM dari Supabase (dipakai dropdown pilih skema di reviewer)
router.get("/schemas", async (req, res, next) => {
  try {
    const { data, error } = await adminClient
      .from("pkm_schemas")
      .select("singkatan, nama")
      .filter("singkatan", "like", "PKM-%")
      .order("singkatan", { ascending: true })

    if (error) {
      console.error("[PkmRoute] Gagal query pkm_schemas:", error.message)
      return res.status(500).json({ error: "Gagal mengambil daftar skema PKM.", detail: error.message })
    }

    res.json({ data: data ?? [] })
  } catch (error) {
    next(error)
  }
})

// POST /api/pkm/validation/run - Proxy multipart DOCX + schema_id ke FastAPI ai-backend
// Body diteruskan as-is (raw Buffer) agar boundary multipart tidak rusak saat di-forward
router.post("/validation/run", async (req, res, next) => {
  try {
    const rawBody = req.body
    const contentType = req.headers["content-type"] || ""

    const aiResponse = await fetch(`${env.AI_BACKEND_URL}/api/validation/run`, {
      method: "POST",
      body: rawBody,
      headers: { "Content-Type": contentType },
    })

    const { data, status } = await parseAiResponse(aiResponse)
    res.status(status).json(data)
  } catch (error) {
    console.error("[PkmRoute] Error proxying validation:", error)
    res.status(500).json({
      error: error instanceof Error ? error.message : "Gagal terhubung ke AI backend.",
    })
  }
})

// POST /api/pkm/validation/bulk - Proxy multipart (banyak file) ke FastAPI ai-backend
// Body diteruskan as-is (raw Buffer) agar boundary multipart tidak rusak saat di-forward
router.post("/validation/bulk", async (req, res, next) => {
  try {
    const rawBody    = req.body
    const contentType = req.headers["content-type"] || ""

    const aiResponse = await fetch(`${env.AI_BACKEND_URL}/api/validation/bulk`, {
      method:  "POST",
      body:    rawBody,
      headers: { "Content-Type": contentType },
    })

    const { data, status } = await parseAiResponse(aiResponse)
    res.status(status).json(data)
  } catch (error) {
    console.error("[PkmRoute] Error proxying bulk validation:", error)
    res.status(500).json({
      error: error instanceof Error ? error.message : "Gagal terhubung ke AI backend.",
    })
  }
})

// POST /api/pkm/validation/summarize - Proxy JSON body ke FastAPI untuk ringkasan LLM
router.post("/validation/summarize", async (req, res, next) => {
  try {
    const aiResponse = await fetch(`${env.AI_BACKEND_URL}/api/validation/summarize`, {
      method: "POST",
      body: JSON.stringify(req.body ?? {}),
      headers: { "Content-Type": "application/json" },
    })

    const { data, status } = await parseAiResponse(aiResponse)
    res.status(status).json(data)
  } catch (error) {
    console.error("[PkmRoute] Error proxying summarize:", error)
    res.status(500).json({
      error: error instanceof Error ? error.message : "Gagal terhubung ke AI backend.",
    })
  }
})

// GET /api/pkm/validation/jobs/:jobId - Proxy status polling ke FastAPI ai-backend
router.get("/validation/jobs/:jobId", async (req, res, next) => {
  try {
    const aiResponse = await fetch(
      `${env.AI_BACKEND_URL}/api/validation/jobs/${req.params.jobId}`
    )
    const { data, status } = await parseAiResponse(aiResponse)
    res.status(status).json(data)
  } catch (error) {
    console.error("[PkmRoute] Error polling job status:", error)
    res.status(500).json({
      error: error instanceof Error ? error.message : "Gagal terhubung ke AI backend.",
    })
  }
})

export default router
