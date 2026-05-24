/**
 * Fungsi: Entry point server Express.
 * Digunakan oleh: process utama (node server.js)
 * Tujuan: Memulai server dan melakukan warmup koneksi Supabase.
 */

import app from "./app.js"
import { env } from "./config/env.js"
import { adminClient, createAuthClient } from "./config/supabase.js"

app.listen(env.PORT, async () => {
  console.log(`Backend server listening on http://127.0.0.1:${env.PORT}`)

  try {
    await adminClient.from("profiles").select("id").limit(1)
    console.log("Supabase PostgREST connection warmed up.")
  } catch (err) {
    console.warn("Supabase PostgREST warmup failed (non-fatal):", err.message)
  }

  try {
    const authClient = createAuthClient()
    await authClient.auth.getSession()
    console.log("Supabase auth connection warmed up.")
  } catch (err) {
    console.warn("Supabase auth warmup failed (non-fatal):", err.message)
  }
})