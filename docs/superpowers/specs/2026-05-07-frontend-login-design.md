# Frontend Login Page — Design Spec
**Date:** 2026-05-07
**Scope:** Login page only (Admin & Reviewer Dashboard deferred to next spec)
**Stack:** Next.js 14 App Router, Supabase Auth (`@supabase/ssr`), shadcn/ui, TypeScript

---

## 1. Architecture

### Framework & Auth
- **Next.js 14** with App Router (`app/` directory)
- **Supabase Auth** via `@supabase/ssr` for server-side session management
- **Middleware** (`middleware.ts`) reads session cookie, checks `user_metadata.role`, redirects unauthenticated users and wrong-role access
- **Server Actions** handle login form submission (no client-side API call leakage)

### Route Structure
```
frontend/
├── app/
│   ├── (auth)/
│   │   └── login/
│   │       └── page.tsx          # login page (server component wrapper)
│   ├── (dashboard)/
│   │   ├── admin/
│   │   │   └── page.tsx          # admin dashboard placeholder
│   │   └── reviewer/
│   │       └── page.tsx          # reviewer dashboard placeholder
│   ├── layout.tsx                # root layout (Poppins font, globals.css)
│   └── globals.css               # CSS variables + shadcn/ui base styles
├── components/
│   ├── ui/                       # shadcn/ui generated components
│   ├── auth/
│   │   └── LoginForm.tsx         # "use client" — form state, role dropdown, submit
│   └── layout/
│       └── PageWrapper.tsx       # centered container, background gradient
├── lib/
│   ├── supabase/
│   │   ├── client.ts             # createBrowserClient()
│   │   └── server.ts             # createServerClient() for Server Components
│   └── utils.ts                  # cn() helper (clsx + tailwind-merge)
├── middleware.ts                  # route guard
├── .env.local                     # NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY
└── package.json
```

---

## 2. Database

### Supabase Migration (new file: `database/supabase/migrations/20260507000000_create_profiles.sql`)
```sql
create type public.app_role as enum ('admin', 'reviewer');

create table public.profiles (
  id        uuid primary key references auth.users(id) on delete cascade,
  role      public.app_role not null,
  full_name text,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

-- users can read their own profile
create policy "users read own profile"
  on public.profiles for select
  using (auth.uid() = id);
```

### Role Storage Strategy
- Role stored in **both** `public.profiles.role` (for DB queries) and `auth.users.user_metadata.role` (for fast middleware reads without extra DB round-trip)
- `user_metadata.role` is set once at user creation by admin (not self-selectable at login time)
- The role **dropdown at login** is for routing intent only — the actual role is verified server-side against `user_metadata.role` after successful auth

---

## 3. Login Page UI

### Visual Design (based on Figma node `1142:290`)
| Token | Value | Usage |
|---|---|---|
| `--pkm-green-50` | `#ecfdf5` | page background, badge bg |
| `--pkm-green-100` | `#d0fae5` | card border, badge border |
| `--pkm-green-400` | `#a4f4cf` | input border, button shadow |
| `--pkm-green-600` | `#009966` | button gradient start, icon color |
| `--pkm-green-700` | `#007a55` | badge text |
| `--pkm-green-900` | `#004f3b` | heading, label text |
| `--pkm-green-muted` | `rgba(0,153,102,0.8)` | subtitle text |

- **Font:** Poppins (Google Fonts — Regular 400, Medium 500)
- **Background:** radial blurred green orbs on `#ecfdf5` → white gradient
- **Card:** `bg-white/95`, border `#d0fae5`, `shadow-2xl`, `rounded-xl`

### Layout
```
[Full viewport, centered]
  ↳ PageWrapper (gradient background + orbs)
      ↳ Card (white, 448px wide)
          ↳ Logo UPNVJ (circular, shadow)
          ↳ "Sistem Review PKM" heading
          ↳ "Universitas Pembangunan Nasional Veteran Jakarta" subtitle
          ↳ LoginForm
              ↳ Select (Role: Admin | Reviewer)
              ↳ Input (Username / email)
              ↳ Input (Password, type=password)
              ↳ Alert (error state, hidden by default)
              ↳ Button "Masuk ke Dashboard"
```

### Components
| Component | File | Type | Responsibility |
|---|---|---|---|
| `LoginForm` | `components/auth/LoginForm.tsx` | `"use client"` | form state, role dropdown, submit handler, error display |
| `PageWrapper` | `components/layout/PageWrapper.tsx` | Server | background gradient + centered layout |
| shadcn `Select` | `components/ui/select.tsx` | UI primitive | role selection dropdown |
| shadcn `Input` | `components/ui/input.tsx` | UI primitive | username & password fields |
| shadcn `Button` | `components/ui/button.tsx` | UI primitive | submit button |
| shadcn `Label` | `components/ui/label.tsx` | UI primitive | field labels |
| shadcn `Alert` | `components/ui/alert.tsx` | UI primitive | error feedback |

---

## 4. Auth Flow

```
User opens /login
  → fills Role dropdown (Admin | Reviewer)
  → fills Username (email) + Password
  → clicks "Masuk ke Dashboard"
      → LoginForm calls Server Action: login(formData)
          → supabase.auth.signInWithPassword({ email, password })
          → if error: return { error: "Email atau password salah" }
          → if success: read user.user_metadata.role
              → if role !== selected dropdown role: return { error: "Role tidak sesuai" }
              → if role === 'admin': redirect('/admin')
              → if role === 'reviewer': redirect('/reviewer')

Middleware on every request to /admin/* and /reviewer/*:
  → getUser() from session cookie
  → if no session: redirect('/login')
  → if session but wrong role: redirect('/login')
```

---

## 5. Middleware Route Guard

```typescript
// Protects:
// /admin/* → requires role === 'admin'
// /reviewer/* → requires role === 'reviewer'
// /login → redirects to dashboard if already logged in
```

---

## 6. Error States

| Trigger | Message |
|---|---|
| Email/password wrong | "Email atau password salah. Periksa kembali." |
| Role mismatch | "Akun ini tidak memiliki akses sebagai [role]." |
| Network error | "Terjadi kesalahan. Coba lagi." |
| Empty fields | Disabled button (no submit) |

---

## 7. Out of Scope (this spec)

- Admin dashboard features (Manajemen Periode, Pengelolaan Pengguna, Document Generation)
- Reviewer dashboard features
- User registration UI (admin creates accounts via Supabase dashboard)
- Forgot password flow
- Dark mode

---

## 8. Dependencies to Install

```
next@14, react, react-dom
@supabase/supabase-js, @supabase/ssr
shadcn/ui (via CLI: npx shadcn@latest init)
shadcn components: button, input, label, select, alert, card
next/font (Poppins — built into Next.js)
clsx, tailwind-merge (via shadcn init)
```
