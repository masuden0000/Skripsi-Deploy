import { Router } from "express"
import * as facultyController from "../controllers/faculty.controller.js"
import { authenticateSession } from "../middlewares/authenticate-session.js"
import { requireRole } from "../middlewares/require-role.js"
import { asyncHandler } from "../utils/async-handler.js"

const router = Router()

router.use(authenticateSession, requireRole("admin"))

router.get("/", asyncHandler(facultyController.list))

export default router
