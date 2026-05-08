# Database

Folder ini menyimpan referensi schema Supabase untuk project.

## Workflow yang dipakai

- Source migration utama ada di `database/supabase/migrations/`.
- File `database/supabase_setup.sql` dan `database/supabase_metadata.sql` tetap disimpan sebagai referensi schema yang mudah dibaca.
- Untuk apply schema ke Supabase cloud, gunakan Supabase CLI atau VSCode Supabase extension, bukan copy-paste ke SQL Editor.
- Workflow migration standar tidak membutuhkan file `.env` khusus di folder `database/`; konfigurasi utamanya ada di `database/supabase/`.

## Command utama

```powershell
Set-Location -LiteralPath .\database\supabase
npx supabase login
npx supabase link --project-ref <PROJECT_REF>
npx supabase db push --dry-run
npx supabase db push
```

`database/supabase/config.toml` sudah dibuat dengan `npx supabase init`, jadi tidak perlu init ulang.

Jika ingin install CLI global, gunakan installer resmi/standalone atau package manager yang tersedia di mesinmu. Di mesin ini `winget install Supabase.CLI` belum menemukan package.

Jika ingin pakai `npx`, Node.js 20+ dibutuhkan:

```powershell
npx supabase --help
```

## Catatan VSCode Extension

Setelah login/link berhasil, VSCode Supabase extension bisa membaca project lokal ini dari folder `database/supabase/` dan migration di `database/supabase/migrations/`.
