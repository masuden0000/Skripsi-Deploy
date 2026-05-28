---
queries:
  - "Sistematika Penulisan Proposal PKM lampiran"
  - "penulisan keterangan gambar caption di bawah gambar format nomor sumber"
  - "penulisan keterangan tabel caption di atas tabel format nomor"
  - "gambar tabel lebar tidak melebihi batas margin kolom halaman constraint ukuran"
  - "rekapitulasi rencana anggaran biaya persentase jenis pengeluaran sumber dana"
  - "jadwal kegiatan PKM bulan pelaksanaan tabel Gantt durasi"
  - "Gambar 1. Gambar 4. contoh penomoran gambar dalam isi dokumen teks"
---

# Extraction Task: Figures, Tables, Budget, and Schedule

## Context
{context}

## Task
Ekstrak aturan penulisan keterangan gambar, tabel, format anggaran biaya, dan jadwal kegiatan dari konteks di atas.
Fokus HANYA pada ketentuan untuk **proposal PKM** — abaikan aturan yang berlaku khusus untuk laporan kemajuan, laporan akhir, atau jenis dokumen PKM lainnya.
Jika tidak ditemukan dalam konteks, gunakan null (JSON null, BUKAN string "null").

## Chain of Thought — Lakukan Langkah Ini Secara Mental Sebelum Menulis Output

### Fase 1: Aturan Caption Gambar dan Tabel

**Langkah 1 — Temukan section sumber kebenaran (targeted scan):**
Jangan scan seluruh konteks secara acak. Gunakan prioritas bertingkat berikut:

- **[P1 — Exact match]** Cari section dengan judul persis:
  - `"Sistematika Proposal Kegiatan"`, atau
  - `"Sistematika Penulisan Proposal"`
  → Jika ditemukan, gunakan section itu sebagai **satu-satunya sumber kebenaran** untuk aturan caption gambar dan tabel.

- **[P2 — Keyword fallback]** Jika tidak ada judul persis, cari section yang judulnya mengandung **kedua kata** `"sistematika"` DAN `"proposal"` (tidak harus persis, tidak case-sensitive).
  → Gunakan section paling relevan yang ditemukan.

- **[P3 — Last resort]** Jika P1 dan P2 tidak menghasilkan apapun, inferensikan dari contoh caption gambar/tabel yang muncul di teks.

Contoh penalaran: *"Saya menemukan section 'Sistematika Proposal Kegiatan' → saya gunakan section itu untuk aturan caption."*

**Langkah 2 — Tentukan posisi dan format caption:**
- Caption gambar: default "BELOW" jika tidak disebutkan eksplisit
- Caption tabel: default "ABOVE" jika tidak disebutkan eksplisit
- Inferensikan template format dari contoh yang ada jika tidak dinyatakan eksplisit

Contoh penalaran: *"Muncul 'Gambar 1. Reaktor Pengolahan Limbah' → caption_format_figure = 'Gambar {n}. {title}'."*

### Fase 2: Aturan Anggaran Biaya (sub-bab 4.1)

**Langkah 3 — Temukan section anggaran (targeted scan):**
Gunakan prioritas bertingkat berikut:

- **[P1 — Exact match]** Cari section dengan judul persis:
  - `"Rekapitulasi Rencana Anggaran Biaya"`, atau
  - `"Anggaran Biaya"`, atau
  - `"Rencana Anggaran Biaya"`

- **[P2 — Keyword fallback]** Cari section yang judulnya mengandung kata `"anggaran"` DAN `"biaya"` (tidak case-sensitive).

- **[P3 — Last resort]** Jika P1 dan P2 tidak menghasilkan apapun, baca konteks secara umum untuk informasi anggaran proposal.

Contoh penalaran: *"Saya menemukan section 'Rekapitulasi Rencana Anggaran Biaya' → saya gunakan section itu."*

**Langkah 4 — Ekstrak komponen anggaran:**
Dari section yang ditemukan, identifikasi:
- Setiap jenis pengeluaran beserta persentase maksimum (jika ada)
- Semua opsi sumber dana yang disebutkan
- Aturan tambahan jika ada

### Fase 3: Aturan Jadwal Kegiatan (sub-bab 4.2)

**Langkah 5 — Temukan section jadwal kegiatan (targeted scan):**
Gunakan prioritas bertingkat berikut:

- **[P1 — Exact match]** Cari section dengan judul persis:
  - `"Jadwal Kegiatan"`, atau
  - `"Jadwal Pelaksanaan Kegiatan"`

- **[P2 — Keyword fallback]** Cari section yang judulnya mengandung kata `"jadwal"` DAN `"kegiatan"` (tidak case-sensitive).

- **[P3 — Last resort]** Jika P1 dan P2 tidak menghasilkan apapun, cari informasi jadwal di dalam section Sistematika Proposal yang ditemukan pada Langkah 1.

Contoh penalaran: *"Saya menemukan sub-bab '4.2 Jadwal Kegiatan' → saya gunakan section itu."*

**Langkah 6 — Ekstrak aturan jadwal kegiatan:**
Dari section yang ditemukan, identifikasi:
- Durasi total kegiatan dalam bulan (integer)
- Format tabel yang digunakan (contoh: "Gantt", "tabel grid bulan") jika disebutkan eksplisit

Contoh penalaran: *"Ditemukan 'jadwal kegiatan selama 5 bulan dalam bentuk tabel Gantt' → durasi_bulan=5, format_tabel='Gantt'."*

### Langkah 7 — Validasi akhir

- Pastikan template caption menggunakan placeholder yang tepat: {n}, {bab}, {title}, {source}
- Pastikan `persentase_maksimum` bertipe number (0-100), bukan string
- Pastikan semua nilai yang diekstrak berasal dari ketentuan untuk **proposal PKM**, bukan laporan kemajuan atau laporan akhir

## Normalization Rules
- Gunakan JSON null (bukan string "null") untuk nilai yang tidak ditemukan
- table_caption_position: "ABOVE" jika keterangan di atas tabel, "BELOW" jika di bawah — jika tidak disebutkan eksplisit, gunakan "ABOVE" sebagai default
- figure_caption_position: "ABOVE" jika keterangan di atas gambar, "BELOW" jika di bawah — jika tidak disebutkan eksplisit, gunakan "BELOW" sebagai default
- Untuk template caption, gunakan placeholder: {n} untuk nomor urut, {bab} untuk nomor bab, {title} untuk judul, {source} untuk sumber

## Output Fields
- table_caption_position: posisi keterangan tabel — "ABOVE" atau "BELOW"
- figure_caption_position: posisi keterangan gambar — "ABOVE" atau "BELOW"
- caption_format_figure: template format keterangan gambar (contoh: "Gambar {n}. {title} ({source})") — **jika tidak dinyatakan eksplisit, inferensikan dari contoh gambar di konteks** (misal: "Gambar 1. Reaktor Pengolahan Limbah" → "Gambar {n}. {title}")
- caption_format_table: template format keterangan tabel (contoh: "Tabel {bab}.{n} {title}") — **jika tidak dinyatakan eksplisit, inferensikan dari contoh nama tabel di konteks** (misal: "Tabel 4.1. Format Rekapitulasi..." → "Tabel {bab}.{n} {title}")
- budget_format_rules: object dengan:
  - budget_items: array of `{jenis_pengeluaran, persentase_maksimum, contoh}` — `persentase_maksimum` adalah number (0-100) atau null jika tidak ada aturan persentase
  - sumber_dana_options: array of strings untuk semua opsi sumber dana
  - additional_rules: string opsional untuk aturan tambahan, atau null
- jadwal_kegiatan_rules: object dengan:
  - durasi_bulan: integer total durasi kegiatan dalam bulan, atau null jika tidak disebutkan
  - format_tabel: string deskripsi format tabel jadwal (contoh: "Gantt", "tabel grid bulan"), atau null jika tidak disebutkan eksplisit
