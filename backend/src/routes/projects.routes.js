/**
 * Projects Routes
 * Semua HTTP untuk projects masuk melalui Express, diteruskan ke AI Backend
 */
import { Router } from "express"
import * as projectsService from "../services/projects.service.js"

const router = Router()

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

    const data = await aiResponse.json()
    res.status(aiResponse.status).json(data)
  } catch (error) {
    console.error("[ProjectsRoute] Error proxying to AI Backend:", error)
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : "Failed to connect to AI backend",
    })
  }
})

// POST /upload-url - Create project and return signed upload URL
router.post("/upload-url", async (req, res, next) => {
  try {
    const rawBody = req.body // Buffer from express.raw()
    const contentType = req.headers["content-type"] || ""

    const aiResponse = await fetch(`${projectsService.AI_BACKEND_URL}/api/projects/upload-url`, {
      method: "POST",
      body: rawBody,
      headers: {
        "Content-Type": contentType,
      },
    })

    const data = await aiResponse.json()
    res.status(aiResponse.status).json(data)
  } catch (error) {
    console.error("[ProjectsRoute] Error proxying to AI Backend:", error)
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : "Failed to connect to AI backend",
    })
  }
})

// POST /confirm-upload - Confirm uploaded file and start pipeline
router.post("/confirm-upload", async (req, res, next) => {
  try {
    const rawBody = req.body // Buffer from express.raw()
    const contentType = req.headers["content-type"] || ""

    const aiResponse = await fetch(`${projectsService.AI_BACKEND_URL}/api/projects/confirm-upload`, {
      method: "POST",
      body: rawBody,
      headers: {
        "Content-Type": contentType,
      },
    })

    const data = await aiResponse.json()
    res.status(aiResponse.status).json(data)
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

// GET /:id/logs - SSE stream for real-time project logs
router.get("/:id/logs", async (req, res, next) => {
  try {
    const { id } = req.params

    // Set SSE headers
    res.setHeader("Content-Type", "text/event-stream")
    res.setHeader("Cache-Control", "no-cache")
    res.setHeader("Connection", "keep-alive")
    res.setHeader("X-Accel-Buffering", "no")

    // Send initial connection message
    res.write("event: connected\ndata: {\"status\":\"connected\"}\n\n")

    // Track last log ID to detect new logs
    let lastLogId = 0

    const fetchLogs = async () => {
      try {
        const response = await fetch(`${projectsService.AI_BACKEND_URL}/api/projects/${id}/logs`)
        if (!response.ok) return

        const data = await response.json()
        if (!data.success || !data.data) return

        const logs = data.data

        // Send only new logs
        const newLogs = logs.filter(log => log.id > lastLogId)
        if (newLogs.length > 0) {
          lastLogId = newLogs[newLogs.length - 1].id

          for (const log of newLogs) {
            res.write(`event: log\ndata: ${JSON.stringify(log)}\n\n`)
          }
        }
      } catch (error) {
        console.error("[ProjectsRoute] Error fetching logs:", error)
      }
    }

    // Poll for logs every 1 second
    const intervalId = setInterval(fetchLogs, 1000)

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
