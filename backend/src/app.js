import cookieParser from "cookie-parser"
import cors from "cors"
import express from "express"
import { env } from "./config/env.js"
import authRoutes from "./routes/auth.routes.js"
import facultyRoutes from "./routes/faculty.routes.js"
import reviewPeriodRoutes from "./routes/review-period.routes.js"
import reviewerRoutes from "./routes/reviewer.routes.js"
import { errorHandler, notFoundHandler } from "./middlewares/error-handler.js"

const app = express()
const allowedOrigins = new Set(env.FRONTEND_URLS)

app.use(
  cors({
    origin(origin, callback) {
      // Browser requests carry an Origin header; health checks and server-to-server calls often do not.
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

app.use("/api/auth", authRoutes)
app.use("/api/faculties", facultyRoutes)
app.use("/api/review-periods", reviewPeriodRoutes)
app.use("/api/reviewers", reviewerRoutes)

app.use(notFoundHandler)
app.use(errorHandler)

export default app
