"""Fungsi utilitas untuk mengambil instansi Supabase client yang terhubung ke database. Keyword: backend API."""
from supabase import Client

from ._supabase import supabase_client


def get_supabase() -> Client:
    return supabase_client
