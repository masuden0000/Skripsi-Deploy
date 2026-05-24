/**
 * Fungsi: Router Express untuk endpoint proyek (CRUD dan upload).
 * Digunakan oleh: frontend/lib/api/projects.ts
 * Tujuan: Mengatur route proyek dan meneruskan request ke controller terkait.
 */

import { Router } from "express"
import { authenticateSession } from "../middlewares/authenticate-session.js"
import { asyncHandler } from "../utils/async-handler.js"
import {
  getProjectsByUserId,
  getProjectById,
  getAllProjects,
  createProject,
  updateProject,
  deleteProject,
  getUploadUrl,
  createProjectAndUpload,
  validateDocument,
} from "../services/projects.service.js"

const router = Router()

router.use(authenticateSession)

router.get("/", asyncHandler(async (req, res) => {
  if (req.user.role === "admin") {
    const page = parseInt(req.query.page) || 1
    const limit = parseInt(req.query.limit) || 20
    const search = req.query.search || ""
    const status = req.query.status || ""
    const periodId = req.query.period_id || ""

    const result = await getAllProjects({ page, limit, search, status, periodId })
    return res.status(200).json(result)
  }

  const projects = await getProjectsByUserId(req.user.id)
  res.status(200).json({ data: projects })
}))

router.get("/:id", asyncHandler(async (req, res) => {
  const project = await getProjectById(req.params.id)
  res.status(200).json({ data: project })
}))

router.post("/", asyncHandler(async (req, res) => {
  const project = await createProject(req.user.id, req.body)
  res.status(201).json({ data: project })
}))

router.put("/:id", asyncHandler(async (req, res) => {
  const project = await updateProject(req.params.id, req.user.id, req.body)
  res.status(200).json({ data: project })
}))

router.delete("/:id", asyncHandler(async (req, res) => {
  await deleteProject(req.params.id, req.user.id)
  res.status(204).send()
}))

router.post("/validate/:id", asyncHandler(async (req, res) => {
  const result = await validateDocument(req.params.id, req.user.id)
  res.status(200).json(result)
}))

export default router