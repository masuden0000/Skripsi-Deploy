import cookieParser from "cookie-parser"
import cors from "cors"
import express from "express"
import { env } from "./config/env.js"
import assignmentsRoutes from "./routes/assignments.routes.js"
import reviewerAssignmentsRoutes from "./routes/reviewer-assignments.routes.js"
import authRoutes from "./routes/auth.routes.js"
import facultyRoutes from "./routes/faculty.routes.js"
import pkmRoutes from "./routes/pkm.routes.js"
import projectsRoutes from "./routes/projects.routes.js"
import reviewPeriodRoutes from "./routes/review-period.routes.js"
import reviewerRoutes from "./routes/reviewer.routes.js"
import { errorHandler, notFoundHandler } from "./middlewares/error-handler.js"

const app = express()
const allowedOrigins = new Set(env.FRONTEND_URLS)

app.use(
  cors({
    origin(origin, callback) {
      // Request dari browser membawa header Origin; health check dan server-to-server biasanya tidak.
      if (!origin || allowedOrigins.has(origin)) {
        callback(null, true)
        return
      }

      callback(new Error(`Origin tidak diizinkan oleh CORS: ${origin}`))
    },
    credentials: true,
  })
)
app.use(express.json())
app.use(cookieParser())

// Special middleware for projects route - keep raw body for multipart
app.use("/api/projects", express.raw({ type: "multipart/form-data", limit: "50mb" }))
app.use("/api/pkm/validation/run",  express.raw({ type: "multipart/form-data", limit: "20mb"  }))
app.use("/api/pkm/validation/bulk", express.raw({ type: "multipart/form-data", limit: "200mb" }))

app.get("/", (_req, res) => {
  res.status(200).json({
    ok: true,
    service: "backend",
    message: "Backend aktif. Gunakan /api/health untuk health check.",
  })
})

app.get("/api/health", (_req, res) => {
  res.status(200).json({
    ok: true,
    service: "backend",
  })
})

app.use("/api/assignments", assignmentsRoutes)
app.use("/api/reviewer-assignments", reviewerAssignmentsRoutes)
app.use("/api/auth", authRoutes)
app.use("/api/faculties", facultyRoutes)
app.use("/api/pkm", pkmRoutes)
app.use("/api/projects", projectsRoutes)
app.use("/api/review-periods", reviewPeriodRoutes)
app.use("/api/reviewers", reviewerRoutes)

app.use(notFoundHandler)
app.use(errorHandler)

export default app
