import { Router } from "express"
import * as reviewerController from "../controllers/reviewer.controller.js"
import { authenticateSession } from "../middlewares/authenticate-session.js"
import { requireRole } from "../middlewares/require-role.js"
import { asyncHandler } from "../utils/async-handler.js"

const router = Router()

router.use(authenticateSession, requireRole("admin"))

router.get("/", asyncHandler(reviewerController.list))
router.post("/", asyncHandler(reviewerController.create))
router.put("/:id", asyncHandler(reviewerController.update))
router.delete("/:id", asyncHandler(reviewerController.remove))

export default router
