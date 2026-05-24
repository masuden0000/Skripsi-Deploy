/**
 * Fungsi: Menangani request HTTP terkait proyek (create, read, upload).
 * Digunakan oleh: routes/projects.routes.js
 * Tujuan: Menjadi jembatan antara route dan service untuk operasi proyek.
 */

import { asyncHandler } from "../utils/async-handler.js"
import {
  getProjectsByUserId,
  getProjectById,
  getAllProjects,
  createProject,
  updateProject,
  deleteProject,
  validateDocument,
  getUploadUrl,
  createProjectAndUpload,
} from "../services/projects.service.js"

export async function listProjects(req, res) {
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
}

export async function getProject(req, res) {
  const project = await getProjectById(req.params.id)
  res.status(200).json({ data: project })
}

export async function createNewProject(req, res) {
  const project = await createProject(req.user.id, req.body)
  res.status(201).json({ data: project })
}

export async function updateExistingProject(req, res) {
  const project = await updateProject(req.params.id, req.user.id, req.body)
  res.status(200).json({ data: project })
}

export async function deleteExistingProject(req, res) {
  await deleteProject(req.params.id, req.user.id)
  res.status(204).send()
}

export async function validateProjectDocument(req, res) {
  const result = await validateDocument(req.params.id, req.user.id)
  res.status(200).json(result)
}

export async function getSignedUploadUrl(req, res) {
  const result = await getUploadUrl(req.params.id, req.user.id)
  res.status(200).json(result)
}

export async function uploadProjectProposal(req, res) {
  const fields = req.body.fields ? JSON.parse(req.body.fields) : req.body
  const fileBuffer = req.file?.buffer || Buffer.from([])

  const project = await createProjectAndUpload(req.user.id, { fields, fileBuffer })
  res.status(201).json({ data: project })
}