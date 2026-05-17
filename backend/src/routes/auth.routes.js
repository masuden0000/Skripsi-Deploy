import { Router } from "express"
import * as authController from "../controllers/auth.controller.js"
import { authenticateSession } from "../middlewares/authenticate-session.js"
import { asyncHandler } from "../utils/async-handler.js"

const router = Router()

router.post("/login", asyncHandler(authController.login))
router.post("/logout", asyncHandler(authController.logout))
router.get("/session", authenticateSession, asyncHandler(authController.getSession))
router.patch("/profile", authenticateSession, asyncHandler(authController.updateProfile))

export default router
