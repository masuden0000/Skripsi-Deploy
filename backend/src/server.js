import app from "./app.js"
import { env } from "./config/env.js"

app.listen(env.PORT, () => {
  console.log(`Backend server listening on http://127.0.0.1:${env.PORT}`)
})
