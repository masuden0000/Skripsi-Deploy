import { Router } from "express"
import { authenticateSession } from "../middlewares/authenticate-session.js"
import { requireRole } from "../middlewares/require-role.js"
import { asyncHandler } from "../utils/async-handler.js"
import { getAssignmentsByReviewerId, getActiveAssignmentsByReviewerId, completeAssignment } from "../services/assignment.service.js"
import { getReviewerProfile } from "../services/reviewer.service.js"

const router = Router()

// All routes require authentication and reviewer role
router.use(authenticateSession, requireRole("reviewer"))

// GET /api/reviewer-assignments/profile - Get current reviewer's name and faculty
router.get("/profile", asyncHandler(async (req, res) => {
  const profile = await getReviewerProfile(req.user.id)
  res.status(200).json({ data: profile })
}))

// GET /api/reviewer-assignments - Get all assignments for current reviewer
router.get("/", asyncHandler(async (req, res) => {
  const assignments = await getAssignmentsByReviewerId(req.user.id)
  res.status(200).json({ data: assignments })
}))

// GET /api/reviewer-assignments/active - Get active assignments for current reviewer
router.get("/active", asyncHandler(async (req, res) => {
  const assignments = await getActiveAssignmentsByReviewerId(req.user.id)
  res.status(200).json({ data: assignments })
}))

// PATCH /api/reviewer-assignments/:id/complete - Mark assignment as completed
router.patch("/:id/complete", asyncHandler(async (req, res) => {
  const assignment = await completeAssignment(req.params.id, req.user.id)
  res.status(200).json({ data: assignment, message: "Tugas berhasil ditandai selesai." })
}))

export default router