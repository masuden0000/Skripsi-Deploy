/**
 * Fungsi: Router Express untuk endpoint penugasan reviewer.
 * Digunakan oleh: frontend/lib/api/reviewer-assignments.ts
 * Tujuan: Menyediakan endpoint bagi reviewer untuk melihat daftar penugasan mereka.
 */

import { Router } from "express"
import { authenticateSession } from "../middlewares/authenticate-session.js"
import { requireRole } from "../middlewares/require-role.js"
import { asyncHandler } from "../utils/async-handler.js"
import { getAssignmentsByReviewerId, getActiveAssignmentsByReviewerId } from "../services/assignment.service.js"

const router = Router()

router.use(authenticateSession, requireRole("reviewer"))

router.get("/", asyncHandler(async (req, res) => {
  const assignments = await getAssignmentsByReviewerId(req.user.id)
  res.status(200).json({ data: assignments })
}))

router.get("/active", asyncHandler(async (req, res) => {
  const assignments = await getActiveAssignmentsByReviewerId(req.user.id)
  res.status(200).json({ data: assignments })
}))

export default router