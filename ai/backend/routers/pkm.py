"""Router untuk data referensi PKM: daftar skema."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services.database import get_supabase

router = APIRouter()


@router.get("/schemas")
async def list_pkm_schemas():
    """Kembalikan daftar semua skema PKM dari tabel pkm_schemas."""
    supabase = get_supabase()
    result = (
        supabase.table("pkm_schemas")
        .select("singkatan, nama, renderer_type")
        .order("singkatan")
        .execute()
    )
    return JSONResponse(content={"success": True, "data": result.data or []})
