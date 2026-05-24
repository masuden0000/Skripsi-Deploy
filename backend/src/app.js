/**
 * Fungsi: Konfigurasi utama aplikasi Express.
 * Digunakan oleh: server.js
 * Tujuan: Mendaftarkan semua middleware, routes, dan error handler Express.
 */

import express from "express"
import cors from "cors"
import helmet from "helmet"
import cookieParser from "cookie-parser"

import projectsRouter from "./routes/projects.routes.js"
import authRouter from "./routes/auth.routes.js"
import pkmRouter from "./routes/pkm.routes.js"
import reviewerAssignmentsRouter from "./routes/reviewer-assignments.routes.js"
import facultiesRouter from "./routes/faculties.routes.js"
import reviewerProfilesRouter from "./routes/reviewer-profiles.routes.js"
import adminAssignmentsRouter from "./routes/admin-assignments.routes.js"
import adminReviewersRouter from "./routes/admin-reviewers.routes.js"
import uploadRouter from "./routes/upload.routes.js"

import { authenticateSession } from "./middlewares/authenticate-session.js"
import { asyncHandler } from "./utils/async-handler.js"
import { AppError } from "./utils/app-error.js"

const app = express()

app.use(
  helmet({
    crossOriginResourcePolicy: { policy: "cross-origin" },
  })
)
app.use(
  cors({
    origin: true,
    credentials: true,
  })
)
app.use(cookieParser())

app.use(express.json())
app.use(express.urlencoded({ extended: true }))

app.get("/api/health", (_req, res) => {
  res.json({ status: "ok" })
})

app.use("/api/auth", authRouter)
app.use("/api/projects", express.raw({ type: "multipart/form-data", limit: "50mb" }), projectsRouter)
app.use("/api/pkm", pkmRouter)
app.use("/api/reviewer-assignments", reviewerAssignmentsRouter)
app.use("/api/faculties", facultiesRouter)
app.use("/api/reviewers", reviewerProfilesRouter)
app.use("/api/admin/assignments", adminAssignmentsRouter)
app.use("/api/admin/reviewers", adminReviewersRouter)
app.use("/api/upload", uploadRouter)

app.use((req, _res, next) => {
  next(new AppError(`Route ${req.method} ${req.path} tidak ditemukan.`, 404))
})

app.use((err, _req, res, _next) => {
  console.error("[Error]", err)

  if (err instanceof AppError) {
    return res.status(err.statusCode).json({
      error: err.message,
    })
  }

  if (err.type === "entity.parse.failed") {
    return res.status(400).json({
      error: "Request body tidak valid.",
    })
  }

  res.status(500).json({
    error: "Terjadi kesalahan internal pada server.",
  })
})

export default app