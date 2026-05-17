import { createClient } from "@supabase/supabase-js"
import { NextResponse } from "next/server"

type RouteContext = {
  params: Promise<{ id: string }>
}

function getSupabase() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL!
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  return createClient(url, key)
}

export async function GET(_req: Request, context: RouteContext) {
  const { id } = await context.params
  const supabase = getSupabase()

  const { data, error } = await supabase
    .from("document_metadata")
    .select("payload")
    .eq("project_id", id)
    .single()

  if (error) {
    const status = error.code === "PGRST116" ? 404 : 500
    return NextResponse.json({ error: error.message }, { status })
  }

  return NextResponse.json({ data: data.payload })
}

export async function PATCH(req: Request, context: RouteContext) {
  const { id } = await context.params
  const body = await req.json()
  const supabase = getSupabase()

  const { data, error } = await supabase
    .from("document_metadata")
    .update({ payload: body.payload })
    .eq("project_id", id)
    .select("payload")
    .single()

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ data: data.payload })
}

export async function DELETE(_req: Request, context: RouteContext) {
  const { id } = await context.params
  const supabase = getSupabase()

  const [metaResult, chunksResult] = await Promise.all([
    supabase.from("document_metadata").delete().eq("project_id", id),
    supabase.from("document_chunks").delete().eq("project_id", id),
  ])

  if (metaResult.error) {
    return NextResponse.json({ error: metaResult.error.message }, { status: 500 })
  }
  if (chunksResult.error) {
    return NextResponse.json({ error: chunksResult.error.message }, { status: 500 })
  }

  return NextResponse.json({ success: true })
}
