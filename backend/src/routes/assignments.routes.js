import { Router } from "express"
import { create, list, remove, update } from "../controllers/assignment.controller.js"

const router = Router()

router.get("/", list)
router.post("/", create)
router.put("/:id", update)
router.delete("/:id", remove)

export default router