"""Router untuk data referensi PKM: daftar skema."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services.database import get_supabase

router = APIRouter()


@router.get("/schemas")
async def list_pkm_schemas():
    """Kembalikan daftar semua skema PKM dari tabel pkm_schemas."""
    try:
        supabase = get_supabase()
        result = (
            supabase.table("pkm_schemas")
            .select("singkatan, nama")
            .order("singkatan")
            .execute()
        )
        return JSONResponse(content={"success": True, "data": result.data or []})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Gagal mengambil daftar skema PKM: {str(e)}"},
        )
