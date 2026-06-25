/**
 * Projects Routes
 * Semua HTTP untuk projects masuk melalui Express, diteruskan ke AI Backend
 *
 * Keyword: automated document generation
 */
import { Router } from "express"
import * as projectsService from "../services/projects.service.js"

const router = Router()

async function parseAiResponse(aiResponse) {
  const text = await aiResponse.text()
  try {
    return { ok: true, data: JSON.parse(text), status: aiResponse.status }
  } catch {
    return { ok: false, data: { success: false, error: text || "AI backend returned non-JSON response" }, status: aiResponse.status || 502 }
  }
}

// POST - Forward directly to AI Backend as multipart
// Use express.raw() to get the raw body buffer
router.post("/", async (req, res, next) => {
  try {
    const rawBody = req.body // Buffer from express.raw()
    const contentType = req.headers["content-type"] || ""

    const aiResponse = await fetch(`${projectsService.AI_BACKEND_URL}/api/projects/`, {
      method: "POST",
      body: rawBody,
      headers: {
        "Content-Type": contentType,
      },
    })

    const { data, status } = await parseAiResponse(aiResponse)
    res.status(status).json(data)
  } catch (error) {
    console.error("[ProjectsRoute] Error proxying to AI Backend:", error)
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : "Failed to connect to AI backend",
    })
  }
})

router.get("/", async (req, res, next) => {
  try {
    const result = await projectsService.listProjects()
    if (!result.success) {
      res.status(500).json(result)
      return
    }
    res.json(result)
  } catch (error) {
    next(error)
  }
})

router.get("/:id", async (req, res, next) => {
  try {
    const { id } = req.params
    const result = await projectsService.getProject(id)
    if (!result.success) {
      res.status(404).json(result)
      return
    }
    res.json(result)
  } catch (error) {
    next(error)
  }
})

// GET /:id/logs - SSE stream (or JSON snapshot when Accept: application/json)
router.get("/:id/logs", async (req, res, next) => {
  try {
    const { id } = req.params
    const sinceId = parseInt(req.query.since_id) || 0
    const sinceParam = sinceId > 0 ? `?since_id=${sinceId}` : ""

    // JSON fallback — digunakan saat halaman di-restore untuk memuat log historis
    if (!req.headers.accept?.includes("text/event-stream")) {
      const response = await fetch(`${projectsService.AI_BACKEND_URL}/api/projects/${id}/logs${sinceParam}`)
      const data = await response.json()
      return res.json(data)
    }

    // Set SSE headers
    res.setHeader("Content-Type", "text/event-stream")
    res.setHeader("Cache-Control", "no-cache")
    res.setHeader("Connection", "keep-alive")
    res.setHeader("X-Accel-Buffering", "no")

    // Send initial connection message
    res.write("event: connected\ndata: {\"status\":\"connected\"}\n\n")

    // Track last log ID and last known status to detect changes
    // Initialize lastLogId from sinceId so SSE only streams logs from the current run
    let lastLogId = sinceId
    let lastStatus = null

    const fetchLogs = async () => {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 8000)
      try {
        const [logsResponse, statusResponse] = await Promise.all([
          fetch(`${projectsService.AI_BACKEND_URL}/api/projects/${id}/logs${sinceParam}`, { signal: controller.signal }),
          fetch(`${projectsService.AI_BACKEND_URL}/api/projects/${id}`, { signal: controller.signal }),
        ])
        clearTimeout(timeoutId)

        if (logsResponse.ok) {
          const data = await logsResponse.json()
          if (data.success && data.data) {
            const newLogs = data.data.filter(log => log.id > lastLogId)
            if (newLogs.length > 0) {
              lastLogId = newLogs[newLogs.length - 1].id
              for (const log of newLogs) {
                res.write(`event: log\ndata: ${JSON.stringify(log)}\n\n`)
              }
            }
          }
        }

        if (statusResponse.ok) {
          const statusData = await statusResponse.json()
          const project = statusData?.data
          if (project && project.status !== lastStatus) {
            lastStatus = project.status
            res.write(`event: status\ndata: ${JSON.stringify(project)}\n\n`)
            if (project.status === 'completed' || project.status === 'failed' || project.status === 'extracted') {
              clearInterval(intervalId)
              res.end()
              return
            }
          }
        }
      } catch (error) {
        clearTimeout(timeoutId)
        if (error.name !== "AbortError") {
          console.error("[ProjectsRoute] Error fetching logs:", error)
        }
      }
    }

    // Poll setiap 3 detik — cukup untuk update real-time tanpa membebani AI service
    // yang sedang menjalankan pipeline berat (LLM extraction, subprocess).
    const intervalId = setInterval(fetchLogs, 3000)

    // Also fetch immediately on connection
    fetchLogs()

    // Clean up on client disconnect
    req.on("close", () => {
      clearInterval(intervalId)
      res.end()
    })
  } catch (error) {
    next(error)
  }
})

// POST /:id/generate - Trigger DOCX generation after extraction confirmed
router.post("/:id/generate", async (req, res, next) => {
  try {
    const { id } = req.params
    const aiResponse = await fetch(`${projectsService.AI_BACKEND_URL}/api/projects/${id}/generate`, {
      method: "POST",
    })
    const { data, status } = await parseAiResponse(aiResponse)
    res.status(status).json(data)
  } catch (error) {
    console.error("[ProjectsRoute] Error proxying generate to AI Backend:", error)
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : "Failed to connect to AI backend",
    })
  }
})

// GET /:id/placeholders - Ambil instructional placeholder (LLM fallback + user overrides)
router.get("/:id/placeholders", async (req, res, next) => {
  try {
    const { id } = req.params
    const aiResponse = await fetch(`${projectsService.AI_BACKEND_URL}/api/projects/${id}/placeholders`)
    const data = await aiResponse.json()
    res.status(aiResponse.status).json(data)
  } catch (error) {
    console.error("[ProjectsRoute] Error proxying placeholders to AI Backend:", error)
    res.status(500).json({ success: false, error: "Gagal mengambil placeholder dari AI backend" })
  }
})

router.delete("/:id", async (req, res, next) => {
  try {
    const { id } = req.params
    const result = await projectsService.deleteProject(id)
    if (!result.success) {
      res.status(404).json(result)
      return
    }
    res.json(result)
  } catch (error) {
    next(error)
  }
})

export default router
