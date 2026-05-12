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
