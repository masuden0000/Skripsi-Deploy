import { Router } from "express"
import { create, list, remove, update, validate } from "../controllers/assignment.controller.js"

const router = Router()

router.get("/", list)
router.post("/", create)
router.put("/:id", update)
router.delete("/:id", remove)
router.patch("/:id/validate", validate)

export default router