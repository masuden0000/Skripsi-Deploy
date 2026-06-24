from supabase import Client

from ._supabase import supabase_client


def get_supabase() -> Client:
    return supabase_client
