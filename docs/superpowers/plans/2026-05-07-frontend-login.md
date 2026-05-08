# Frontend Login Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Next.js 14 login page for Sistem Review PKM dengan Supabase Auth, shadcn/ui, Poppins font, dan green/white design sesuai Figma node `1142:290`.

**Architecture:** Next.js App Router dengan route groups `(auth)` dan `(dashboard)`. Supabase Auth via `@supabase/ssr` untuk server-side sessions. Login form adalah client component yang memanggil server action. Middleware melindungi `/admin` dan `/reviewer` dengan mengecek `user_metadata.role`.

**Tech Stack:** Next.js 14, TypeScript, `@supabase/supabase-js`, `@supabase/ssr`, shadcn/ui, Tailwind CSS, Poppins (`next/font/google`)

**Spec:** `docs/superpowers/specs/2026-05-07-frontend-login-design.md`

---

## File Map

| File | Status | Tanggung jawab |
|---|---|---|
| `frontend/` | Create (scaffold) | Next.js 14 project root |
| `frontend/.env.local` | Create | Supabase URL + anon key |
| `frontend/public/logo-upnvj.png` | Create | Logo dari Figma asset |
| `frontend/public/icon-user.png` | Create | Icon user dari Figma |
| `frontend/public/icon-lock.png` | Create | Icon lock dari Figma |
| `frontend/tailwind.config.ts` | Modify | Tambah `pkm.*` color tokens |
| `frontend/app/globals.css` | Modify | CSS variables shadcn override (green) |
| `frontend/app/layout.tsx` | Modify | Poppins font via next/font |
| `frontend/app/page.tsx` | Modify | Redirect root → /login |
| `frontend/app/actions/auth.ts` | Create | Server action: login() |
| `frontend/app/(auth)/login/page.tsx` | Create | Login page (server component) |
| `frontend/app/(dashboard)/admin/page.tsx` | Create | Admin placeholder |
| `frontend/app/(dashboard)/reviewer/page.tsx` | Create | Reviewer placeholder |
| `frontend/components/layout/PageWrapper.tsx` | Create | Background gradient + centered layout |
| `frontend/components/auth/LoginForm.tsx` | Create | "use client" — form + role dropdown |
| `frontend/lib/supabase/client.ts` | Create | Browser Supabase client |
| `frontend/lib/supabase/server.ts` | Create | Server Supabase client |
| `frontend/lib/utils.ts` | Create (if missing) | cn() helper |
| `frontend/middleware.ts` | Create | Route guard berdasarkan role |
| `database/supabase/migrations/20260507000000_create_profiles.sql` | Create | Tabel profiles + RLS |

---

## Task 1: Scaffold Next.js project

**Files:**
- Create: `frontend/` (seluruh project via CLI)

- [ ] **Step 1: Scaffold dari repo root**

```bash
npx create-next-app@latest frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --no-src-dir \
  --import-alias "@/*" \
  --no-git
```
Jawab semua prompt dengan default.

- [ ] **Step 2: Install Supabase dependencies**

```bash
cd frontend
npm install @supabase/supabase-js @supabase/ssr
```

- [ ] **Step 3: Init shadcn/ui**

```bash
npx shadcn@latest init
```
Saat prompt:
- Style: **Default**
- Base color: **Green**
- CSS variables: **Yes**

- [ ] **Step 4: Add shadcn components**

```bash
npx shadcn@latest add button input label select alert card
```

- [ ] **Step 5: Buat `.env.local`**

Buat `frontend/.env.local`:
```
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```
> Ambil dari Supabase dashboard → Settings → API → Project URL & anon key.

- [ ] **Step 6: Verifikasi dev server**

```bash
npm run dev
```
Expected: server jalan di `http://localhost:3000`, halaman default Next.js muncul. Ctrl+C setelah terverifikasi.

- [ ] **Step 7: Commit**

```bash
cd .. # kembali ke repo root
git add frontend/
git commit -m "feat: scaffold Next.js 14 frontend with shadcn/ui and Supabase deps"
```

---

## Task 2: Download Figma assets

**Files:**
- Create: `frontend/public/logo-upnvj.png`
- Create: `frontend/public/icon-user.png`
- Create: `frontend/public/icon-lock.png`

> **Catatan:** URL Figma asset expire dalam 7 hari. Jalankan segera.

- [ ] **Step 1: Download logo UPNVJ**

```bash
curl -L -o frontend/public/logo-upnvj.png \
  "https://www.figma.com/api/mcp/asset/486a98d8-23b0-4135-bbe9-02c475e76c6d"
```

- [ ] **Step 2: Download icon user**

```bash
curl -L -o frontend/public/icon-user.png \
  "https://www.figma.com/api/mcp/asset/1c3315e0-d51c-4215-ad8c-2cebaafe5db8"
```

- [ ] **Step 3: Download icon lock**

```bash
curl -L -o frontend/public/icon-lock.png \
  "https://www.figma.com/api/mcp/asset/db14a5e2-e82f-4ba2-b035-b9d2e2bfb54f"
```

- [ ] **Step 4: Verifikasi file tidak kosong**

```bash
ls -lh frontend/public/*.png
```
Expected: ketiga file ada dan size > 0 bytes.

- [ ] **Step 5: Commit**

```bash
git add frontend/public/
git commit -m "feat: add Figma assets — logo UPNVJ, icon user, icon lock"
```

---

## Task 3: Supabase migration — tabel profiles

**Files:**
- Create: `database/supabase/migrations/20260507000000_create_profiles.sql`

- [ ] **Step 1: Tulis migration**

Buat `database/supabase/migrations/20260507000000_create_profiles.sql`:
```sql
create type public.app_role as enum ('admin', 'reviewer');

create table public.profiles (
  id         uuid primary key references auth.users(id) on delete cascade,
  role       public.app_role not null,
  full_name  text,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "users read own profile"
  on public.profiles
  for select
  using (auth.uid() = id);
```

- [ ] **Step 2: Apply migration**

**Jika pakai Supabase lokal:**
```bash
npx supabase db push
```
Expected: `Applying migration 20260507000000_create_profiles.sql... done`

**Jika pakai Supabase remote saja:** buka Supabase dashboard → SQL Editor → paste isi file → Run.

- [ ] **Step 3: Buat user admin test**

Di Supabase dashboard → Authentication → Users → Add user:
- Email: `admin@test.com`, Password: `Test1234!`

Lalu di SQL Editor:
```sql
update auth.users
set raw_user_meta_data = jsonb_set(
  coalesce(raw_user_meta_data, '{}'),
  '{role}',
  '"admin"'
)
where email = 'admin@test.com';

insert into public.profiles (id, role, full_name)
select id, 'admin', 'Admin Test'
from auth.users
where email = 'admin@test.com';
```

- [ ] **Step 4: Buat user reviewer test**

Di Supabase dashboard → Authentication → Users → Add user:
- Email: `reviewer@test.com`, Password: `Test1234!`

Lalu di SQL Editor:
```sql
update auth.users
set raw_user_meta_data = jsonb_set(
  coalesce(raw_user_meta_data, '{}'),
  '{role}',
  '"reviewer"'
)
where email = 'reviewer@test.com';

insert into public.profiles (id, role, full_name)
select id, 'reviewer', 'Reviewer Test'
from auth.users
where email = 'reviewer@test.com';
```

- [ ] **Step 5: Commit**

```bash
git add database/supabase/migrations/20260507000000_create_profiles.sql
git commit -m "feat: add profiles table migration with app_role enum and RLS"
```

---

## Task 4: Konfigurasi Supabase clients

**Files:**
- Create: `frontend/lib/supabase/client.ts`
- Create: `frontend/lib/supabase/server.ts`
- Create: `frontend/lib/utils.ts` (jika belum ada dari shadcn init)

- [ ] **Step 1: Buat browser client**

Buat `frontend/lib/supabase/client.ts`:
```typescript
import { createBrowserClient } from "@supabase/ssr"

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}
```

- [ ] **Step 2: Buat server client**

Buat `frontend/lib/supabase/server.ts`:
```typescript
import { createServerClient } from "@supabase/ssr"
import { cookies } from "next/headers"

export async function createClient() {
  const cookieStore = await cookies()

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll()
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            )
          } catch {
            // Server Component — cookie writes ignored here, handled in middleware
          }
        },
      },
    }
  )
}
```

- [ ] **Step 3: Pastikan utils.ts ada**

Cek apakah `frontend/lib/utils.ts` sudah dibuat oleh shadcn init:
```bash
cat frontend/lib/utils.ts
```
Jika tidak ada, buat:
```typescript
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/
git commit -m "feat: add Supabase browser and server clients"
```

---

## Task 5: Setup design system (Tailwind tokens + Poppins + globals.css)

**Files:**
- Modify: `frontend/tailwind.config.ts`
- Modify: `frontend/app/globals.css`
- Modify: `frontend/app/layout.tsx`

- [ ] **Step 1: Tambah PKM colors ke Tailwind**

Buka `frontend/tailwind.config.ts`. Ganti seluruh isinya dengan:
```typescript
import type { Config } from "tailwindcss"

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        pkm: {
          50:   "#ecfdf5",
          100:  "#d0fae5",
          400:  "#a4f4cf",
          600:  "#009966",
          700:  "#007a55",
          900:  "#004f3b",
          muted: "rgba(0,153,102,0.8)",
        },
        border:     "hsl(var(--border))",
        input:      "hsl(var(--input))",
        ring:       "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT:    "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT:    "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT:    "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT:    "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT:    "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        card: {
          DEFAULT:    "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
export default config
```

- [ ] **Step 2: Update globals.css dengan PKM green theme**

Ganti `frontend/app/globals.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background:            0 0% 100%;
    --foreground:            160 100% 15%;
    --card:                  0 0% 100%;
    --card-foreground:       160 100% 15%;
    --popover:               0 0% 100%;
    --popover-foreground:    160 100% 15%;
    --primary:               160 100% 30%;
    --primary-foreground:    0 0% 100%;
    --secondary:             150 80% 95%;
    --secondary-foreground:  160 100% 15%;
    --muted:                 150 60% 96%;
    --muted-foreground:      160 40% 45%;
    --accent:                150 80% 95%;
    --accent-foreground:     160 100% 15%;
    --destructive:           0 84% 60%;
    --destructive-foreground:0 0% 98%;
    --border:                150 60% 88%;
    --input:                 150 60% 88%;
    --ring:                  160 100% 30%;
    --radius:                0.5rem;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

- [ ] **Step 3: Pasang Poppins di root layout**

Ganti `frontend/app/layout.tsx`:
```typescript
import type { Metadata } from "next"
import { Poppins } from "next/font/google"
import "./globals.css"

const poppins = Poppins({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-poppins",
})

export const metadata: Metadata = {
  title: "Sistem Review PKM — UPNVJ",
  description: "Portal manajemen review Program Kreativitas Mahasiswa",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="id">
      <body
        className={`${poppins.variable} font-[family-name:var(--font-poppins)] antialiased`}
      >
        {children}
      </body>
    </html>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/app/globals.css frontend/app/layout.tsx frontend/tailwind.config.ts
git commit -m "feat: setup PKM green design system with Poppins and shadcn CSS variable overrides"
```

---

## Task 6: Buat PageWrapper component

**Files:**
- Create: `frontend/components/layout/PageWrapper.tsx`

- [ ] **Step 1: Buat direktori dan file**

```bash
mkdir -p frontend/components/layout
```

Buat `frontend/components/layout/PageWrapper.tsx`:
```typescript
export default function PageWrapper({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div
      className="relative min-h-screen w-full flex items-center justify-center overflow-hidden"
      style={{
        background:
          "linear-gradient(154.57deg, #ecfdf5 0%, #ffffff 50%, rgba(236,253,245,0.3) 100%)",
      }}
    >
      {/* Blurred green orb kanan atas — sesuai Figma node 1142:293 */}
      <div
        className="pointer-events-none absolute right-0 top-[-160px] size-80 rounded-full blur-[64px]"
        style={{ background: "rgba(164,244,207,0.5)" }}
      />
      {/* Blurred green orb kiri bawah — sesuai Figma node 1142:294 */}
      <div
        className="pointer-events-none absolute bottom-[-160px] left-0 size-80 rounded-full blur-[64px]"
        style={{ background: "rgba(185,248,207,0.5)" }}
      />
      {/* Blurred green orb tengah — sesuai Figma node 1142:295 */}
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 size-96 -translate-x-1/2 -translate-y-1/2 rounded-full blur-[64px]"
        style={{ background: "rgba(208,250,229,0.3)" }}
      />

      {/* Slot konten */}
      <div className="relative z-10 w-full max-w-[448px] px-4 py-10">
        {children}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/layout/PageWrapper.tsx
git commit -m "feat: add PageWrapper with Figma-matched green gradient background and orbs"
```

---

## Task 7: Buat LoginForm component

**Files:**
- Create: `frontend/components/auth/LoginForm.tsx`

- [ ] **Step 1: Buat direktori**

```bash
mkdir -p frontend/components/auth
```

- [ ] **Step 2: Buat LoginForm.tsx**

Buat `frontend/components/auth/LoginForm.tsx`:
```typescript
"use client"

import { useState, useTransition } from "react"
import Image from "next/image"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { login } from "@/app/actions/auth"

export default function LoginForm() {
  const [role, setRole] = useState<string>("")
  const [error, setError] = useState<string>("")
  const [isPending, startTransition] = useTransition()

  const canSubmit = Boolean(role) && !isPending

  function handleSubmit(formData: FormData) {
    setError("")
    formData.set("role", role)
    startTransition(async () => {
      const result = await login(formData)
      if (result?.error) {
        setError(result.error)
      }
    })
  }

  return (
    <div
      className="w-full overflow-hidden rounded-xl border border-pkm-100 bg-white/95"
      style={{ boxShadow: "0px 25px 50px 0px rgba(0,0,0,0.25)" }}
    >
      {/* Header: logo + judul */}
      <div className="flex flex-col items-center px-6 pb-0 pt-10">
        {/* Lingkaran logo */}
        <div className="relative mb-5">
          <div
            className="absolute inset-0 rounded-full blur-[24px]"
            style={{
              background:
                "linear-gradient(135deg, rgba(0,212,146,0.3) 0%, rgba(5,223,114,0.3) 100%)",
            }}
          />
          <div className="relative flex size-28 items-end justify-center rounded-full bg-white px-4 pt-4 shadow-[0px_10px_15px_0px_rgba(0,0,0,0.1),0px_4px_6px_0px_rgba(0,0,0,0.1)]">
            <Image
              src="/logo-upnvj.png"
              alt="Logo UPNVJ"
              width={80}
              height={80}
              className="mb-2 object-contain"
              priority
            />
          </div>
        </div>

        {/* Judul sistem */}
        <h1 className="text-center text-base font-semibold text-pkm-900">
          Sistem Review PKM
        </h1>
        <p className="mt-1 text-center text-[13px]" style={{ color: "rgba(0,153,102,0.8)" }}>
          Universitas Pembangunan Nasional Veteran Jakarta
        </p>
      </div>

      {/* Form */}
      <form action={handleSubmit} className="flex flex-col gap-5 px-6 py-8">
        {/* Role dropdown */}
        <div className="flex flex-col gap-2">
          <Label className="text-sm font-medium text-pkm-900">
            Masuk sebagai
          </Label>
          <Select value={role} onValueChange={setRole}>
            <SelectTrigger className="h-11 rounded-lg border-pkm-400 bg-white text-sm focus:ring-pkm-600">
              <SelectValue placeholder="Pilih role..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="admin">Admin</SelectItem>
              <SelectItem value="reviewer">Reviewer</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Username (email) */}
        <div className="flex flex-col gap-2">
          <Label htmlFor="email" className="text-sm font-medium text-pkm-900">
            Username
          </Label>
          <div className="relative">
            <Image
              src="/icon-user.png"
              alt=""
              width={20}
              height={20}
              aria-hidden
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2"
            />
            <Input
              id="email"
              name="email"
              type="email"
              placeholder="Masukkan username"
              required
              className="h-11 rounded-lg border-pkm-400 pl-10 text-sm placeholder:text-gray-400 focus-visible:ring-pkm-600"
            />
          </div>
        </div>

        {/* Password */}
        <div className="flex flex-col gap-2">
          <Label htmlFor="password" className="text-sm font-medium text-pkm-900">
            Password
          </Label>
          <div className="relative">
            <Image
              src="/icon-lock.png"
              alt=""
              width={20}
              height={20}
              aria-hidden
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2"
            />
            <Input
              id="password"
              name="password"
              type="password"
              placeholder="Masukkan password"
              required
              className="h-11 rounded-lg border-pkm-400 pl-10 text-sm placeholder:text-gray-400 focus-visible:ring-pkm-600"
            />
          </div>
        </div>

        {/* Error alert */}
        {error && (
          <Alert variant="destructive" className="py-2">
            <AlertDescription className="text-sm">{error}</AlertDescription>
          </Alert>
        )}

        {/* Submit button */}
        <Button
          type="submit"
          disabled={!canSubmit}
          className="h-11 w-full rounded-lg text-sm font-medium text-white disabled:opacity-50"
          style={
            canSubmit
              ? {
                  background: "linear-gradient(90deg, #009966 0%, #00bc7d 100%)",
                  boxShadow: "0px 10px 7.5px rgba(164,244,207,0.6), 0px 4px 3px rgba(164,244,207,0.4)",
                }
              : { background: "#a4f4cf" }
          }
        >
          {isPending ? "Memproses..." : "Masuk ke Dashboard"}
        </Button>
      </form>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/auth/LoginForm.tsx
git commit -m "feat: add LoginForm with role dropdown, Figma-matched green styling, error handling"
```

---

## Task 8: Buat server action login

**Files:**
- Create: `frontend/app/actions/auth.ts`

- [ ] **Step 1: Buat direktori**

```bash
mkdir -p frontend/app/actions
```

- [ ] **Step 2: Buat auth.ts**

Buat `frontend/app/actions/auth.ts`:
```typescript
"use server"

import { createClient } from "@/lib/supabase/server"
import { redirect } from "next/navigation"

type LoginResult = { error: string } | undefined

export async function login(formData: FormData): Promise<LoginResult> {
  const email    = formData.get("email")    as string
  const password = formData.get("password") as string
  const role     = formData.get("role")     as string

  if (!email || !password || !role) {
    return { error: "Semua field wajib diisi." }
  }

  const supabase = await createClient()

  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  })

  if (error) {
    return { error: "Email atau password salah. Periksa kembali." }
  }

  const userRole = data.user.user_metadata?.role as string | undefined

  if (!userRole) {
    return { error: "Akun ini belum memiliki role yang ditetapkan." }
  }

  if (userRole !== role) {
    return {
      error: `Akun ini tidak memiliki akses sebagai ${
        role === "admin" ? "Admin" : "Reviewer"
      }.`,
    }
  }

  redirect(role === "admin" ? "/admin" : "/reviewer")
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/app/actions/auth.ts
git commit -m "feat: add login server action with Supabase Auth and server-side role check"
```

---

## Task 9: Buat middleware route guard

**Files:**
- Create: `frontend/middleware.ts`

- [ ] **Step 1: Buat middleware.ts**

Buat `frontend/middleware.ts`:
```typescript
import { createServerClient } from "@supabase/ssr"
import { NextResponse, type NextRequest } from "next/server"

export async function middleware(request: NextRequest) {
  const response = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          )
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  const {
    data: { user },
  } = await supabase.auth.getUser()

  const { pathname } = request.nextUrl

  // User sudah login dan buka /login → redirect ke dashboard sesuai role
  if (pathname === "/login" && user) {
    const role = user.user_metadata?.role as string | undefined
    const dest = role === "admin" ? "/admin" : "/reviewer"
    return NextResponse.redirect(new URL(dest, request.url))
  }

  // /admin hanya untuk role admin
  if (pathname.startsWith("/admin")) {
    if (!user) {
      return NextResponse.redirect(new URL("/login", request.url))
    }
    if (user.user_metadata?.role !== "admin") {
      return NextResponse.redirect(new URL("/login", request.url))
    }
  }

  // /reviewer hanya untuk role reviewer
  if (pathname.startsWith("/reviewer")) {
    if (!user) {
      return NextResponse.redirect(new URL("/login", request.url))
    }
    if (user.user_metadata?.role !== "reviewer") {
      return NextResponse.redirect(new URL("/login", request.url))
    }
  }

  return response
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/middleware.ts
git commit -m "feat: add middleware route guard — protect /admin and /reviewer by role"
```

---

## Task 10: Buat halaman-halaman route

**Files:**
- Create: `frontend/app/(auth)/login/page.tsx`
- Create: `frontend/app/(dashboard)/admin/page.tsx`
- Create: `frontend/app/(dashboard)/reviewer/page.tsx`
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: Buat login page**

```bash
mkdir -p frontend/app/\(auth\)/login
```

Buat `frontend/app/(auth)/login/page.tsx`:
```typescript
import PageWrapper from "@/components/layout/PageWrapper"
import LoginForm from "@/components/auth/LoginForm"

export default function LoginPage() {
  return (
    <PageWrapper>
      <LoginForm />
    </PageWrapper>
  )
}
```

- [ ] **Step 2: Buat admin dashboard placeholder**

```bash
mkdir -p frontend/app/\(dashboard\)/admin
```

Buat `frontend/app/(dashboard)/admin/page.tsx`:
```typescript
export default function AdminDashboard() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-pkm-50">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-pkm-900">Dashboard Admin</h1>
        <p className="mt-2 text-sm" style={{ color: "rgba(0,153,102,0.8)" }}>
          Selamat datang, Admin.
        </p>
      </div>
    </main>
  )
}
```

- [ ] **Step 3: Buat reviewer dashboard placeholder**

```bash
mkdir -p frontend/app/\(dashboard\)/reviewer
```

Buat `frontend/app/(dashboard)/reviewer/page.tsx`:
```typescript
export default function ReviewerDashboard() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-pkm-50">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-pkm-900">Dashboard Reviewer</h1>
        <p className="mt-2 text-sm" style={{ color: "rgba(0,153,102,0.8)" }}>
          Selamat datang, Reviewer.
        </p>
      </div>
    </main>
  )
}
```

- [ ] **Step 4: Redirect root ke /login**

Ganti isi `frontend/app/page.tsx`:
```typescript
import { redirect } from "next/navigation"

export default function Home() {
  redirect("/login")
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/app/
git commit -m "feat: add login page, admin/reviewer dashboard placeholders, root redirect to /login"
```

---

## Task 11: Smoke test end-to-end

- [ ] **Step 1: Start dev server**

```bash
cd frontend
npm run dev
```

- [ ] **Step 2: Test root redirect**

Buka `http://localhost:3000` di browser.
Expected: redirect ke `http://localhost:3000/login`.

- [ ] **Step 3: Test render halaman login**

Di `/login`, verifikasi:
- Logo UPNVJ tampil (bukan broken image)
- Heading "Sistem Review PKM" terlihat
- Dropdown role menampilkan "Pilih role..."
- Tombol "Masuk ke Dashboard" disabled (abu-abu / gradient pucat)

- [ ] **Step 4: Test dropdown mengaktifkan tombol**

Pilih "Admin" dari dropdown.
Expected: tombol berubah menjadi gradient hijau dan bisa diklik.

- [ ] **Step 5: Test credentials salah**

Isi: Role=Admin, email=salah@test.com, password=salah → klik Masuk.
Expected: muncul Alert merah: `"Email atau password salah. Periksa kembali."`

- [ ] **Step 6: Test role mismatch**

Isi: Role=Reviewer, email=admin@test.com, password=Test1234! → klik Masuk.
Expected: Alert: `"Akun ini tidak memiliki akses sebagai Reviewer."`

- [ ] **Step 7: Test login admin berhasil**

Isi: Role=Admin, email=admin@test.com, password=Test1234! → klik Masuk.
Expected: redirect ke `/admin`, muncul "Dashboard Admin".

- [ ] **Step 8: Test login reviewer berhasil**

Isi: Role=Reviewer, email=reviewer@test.com, password=Test1234! → klik Masuk.
Expected: redirect ke `/reviewer`, muncul "Dashboard Reviewer".

- [ ] **Step 9: Test middleware protection**

Logout (hapus cookies / buka incognito), lalu akses `http://localhost:3000/admin` langsung.
Expected: redirect ke `/login`.

- [ ] **Step 10: Test already-logged-in redirect**

Login sebagai admin, kemudian akses `http://localhost:3000/login`.
Expected: middleware redirect langsung ke `/admin`.

- [ ] **Step 11: Commit final**

```bash
cd ..
git add -A
git commit -m "chore: complete login page smoke test — all flows verified"
```
