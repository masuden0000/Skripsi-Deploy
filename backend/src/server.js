import app from "./app.js"
import { env } from "./config/env.js"
import { adminClient, createAuthClient } from "./config/supabase.js"

app.listen(env.PORT, async () => {
  console.log(`Backend server listening on http://127.0.0.1:${env.PORT}`)

  // Warm up PostgREST connection (database queries)
  try {
    await adminClient.from("profiles").select("id").limit(1)
    console.log("Supabase PostgREST connection warmed up.")
  } catch (err) {
    console.warn("Supabase PostgREST warmup failed (non-fatal):", err.message)
  }

  // Warm up auth API connection — login menggunakan endpoint /auth/v1/ yang berbeda
  // dari PostgREST, sehingga perlu warmup terpisah agar tidak ECONNRESET pada login pertama
  try {
    const authClient = createAuthClient()
    await authClient.auth.getSession()
    console.log("Supabase auth connection warmed up.")
  } catch (err) {
    console.warn("Supabase auth warmup failed (non-fatal):", err.message)
  }
})
