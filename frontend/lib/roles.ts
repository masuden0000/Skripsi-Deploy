/**
 * Fungsi: Pemetaan role user ke route dashboard yang sesuai
 * Digunakan oleh: Middleware autentikasi, redirect after login
 * Tujuan: Menentukan ke halaman mana user diarahkan setelah login
 */

export const ROLE_ROUTES: Record<string, string> = {