import { Router } from "express"
import { authenticateSession } from "../middlewares/authenticate-session.js"
import { requireRole } from "../middlewares/require-role.js"
import { asyncHandler } from "../utils/async-handler.js"
import { getAssignmentsByReviewerId, getActiveAssignmentsByReviewerId } from "../services/assignment.service.js"

const router = Router()

// All routes require authentication and reviewer role
router.use(authenticateSession, requireRole("reviewer"))

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

export default router