import { createClient } from "@supabase/supabase-js"
import { NextResponse } from "next/server"

function getSupabase() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  )
}

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url)
  const skema = searchParams.get("skema")
  const tahun = searchParams.get("tahun")

  const supabase = getSupabase()

  let query = supabase
    .from("projects")
    .select("id, skema, tahun, result_url")
    .eq("status", "completed")
    .not("result_url", "is", null)
    .order("tahun", { ascending: false })
    .order("skema", { ascending: true })

  if (skema) query = query.eq("skema", skema)
  if (tahun) query = query.eq("tahun", tahun)

  const { data, error } = await query

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ data: data ?? [] })
}
