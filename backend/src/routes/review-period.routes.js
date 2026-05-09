import { Router } from "express"
import * as reviewPeriodController from "../controllers/review-period.controller.js"
import { authenticateSession } from "../middlewares/authenticate-session.js"
import { requireRole } from "../middlewares/require-role.js"
import { asyncHandler } from "../utils/async-handler.js"

const router = Router()

router.use(authenticateSession, requireRole("admin"))

router.get("/", asyncHandler(reviewPeriodController.list))
router.get("/:id", asyncHandler(reviewPeriodController.getById))
router.post("/", asyncHandler(reviewPeriodController.create))
router.put("/:id", asyncHandler(reviewPeriodController.update))

export default router
