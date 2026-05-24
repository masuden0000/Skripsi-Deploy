/**
 * Fungsi: Klien API terpusat dengan validasi Zod dan error handling
 * Digunakan oleh: Semua modul API di frontend/lib/api/*
 * Tujuan: Fetch wrapper yang menangani autentikasi, parsing, dan error secara konsisten
 */

import { ZodSchema, ZodError } from "zod"