/**
 * Fungsi: Router Express untuk endpoint PKM (Program Kreativitas Mahasiswa).
 * Digunakan oleh: frontend/lib/api/pkm.ts
 * Tujuan: Menyediakan daftar skema PKM dan proxy validasi ke AI backend.
 */

import { Router } from "express"
import { adminClient } from "../config/supabase.js"
import { env } from "../config/env.js"

const router = Router()

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

router.get("/schemas", async (req, res, next) => {
  try {
    const { data, error } = await adminClient
      .from("pkm_schemas")
      .select("id, nama, singkatan, created_at, updated_at")
      .order("nama", { ascending: true })

    if (error) {
      return res.status(500).json({ error: "Gagal mengambil daftar skema PKM." })
    }

    const mapped = (data ?? []).map((row) => ({
      id: row.id,
      nama: row.nama,
      singkatan: row.singkatan,
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    }))

    res.json({ data: mapped })
  } catch (error) {
    next(error)
  }
})

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

export default router