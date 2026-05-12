/**
 * Projects Controller
 * Handle HTTP requests untuk projects
 */
import * as projectsService from "../services/projects.service.js"

async function createProject(req, res, next) {
  try {
    const { skema, tahun, judul } = req.body
    const file = req.file

    if (!skema || !tahun || !judul) {
      res.status(400).json({
        success: false,
        error: "Missing required fields: skema, tahun, judul",
      })
      return
    }

    const result = await projectsService.createProject(
      { skema, tahun, judul },
      file
    )

    if (!result.success) {
      res.status(500).json(result)
      return
    }

    res.status(201).json(result)
  } catch (error) {
    next(error)
  }
}

async function getProject(req, res, next) {
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
}

async function listProjects(req, res, next) {
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
}

async function deleteProject(req, res, next) {
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
}

export { createProject, getProject, listProjects, deleteProject }