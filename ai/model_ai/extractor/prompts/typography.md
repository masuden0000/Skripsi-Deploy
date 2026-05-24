---
queries:
  - "Format Penulisan Proposal tipe huruf Times New Roman ukuran 12"
  - "Sistematika Penulisan Proposal PKM tipe huruf"
  - "tipe huruf Times New Roman ukuran 12 nomor halaman"
  - "font huruf ukuran tipografi heading body Times New Roman ukuran 12"
  - "huruf kapital judul BAB ALL CAPS cetak tebal bold heading capitalization penulisan"
---

# Extraction Task: Typography

## Context
{context}

## Task
Ekstrak informasi tipografi dokumen dari konteks di atas.
Fokus HANYA pada ketentuan untuk **proposal PKM** — abaikan aturan yang berlaku khusus untuk laporan kemajuan, laporan akhir, atau jenis dokumen PKM lainnya.
Jika informasi tidak ditemukan dalam konteks, gunakan null (JSON null, BUKAN string "null").
Jangan gunakan pengetahuan umum — hanya berdasarkan konteks yang diberikan.

## Chain of Thought — Lakukan Langkah Ini Secara Mental Sebelum Menulis Output

**Langkah 1 — Temukan section sumber kebenaran (targeted scan):**
Jangan scan seluruh konteks secara acak. Gunakan prioritas bertingkat berikut:

- **[P1 — Exact match]** Cari section dengan judul persis:
  - `"Sistematika Proposal Kegiatan"`, atau
  - `"Sistematika Penulisan Proposal"`
  → Jika ditemukan, gunakan section itu sebagai **satu-satunya sumber kebenaran** untuk aturan tipografi.

- **[P2 — Keyword fallback]** Jika tidak ada judul persis, cari section yang judulnya mengandung **kedua kata** `"sistematika"` DAN `"proposal"` (tidak harus persis, tidak case-sensitive).
  → Gunakan section paling relevan yang ditemukan.

- **[P3 — Last resort]** Jika P1 dan P2 tidak menghasilkan apapun, baru baca konteks secara umum.

Contoh penalaran: *"Saya menemukan section 'Sistematika Penulisan Proposal' → saya gunakan section itu."*

**Langkah 2 — Ekstrak field tipografi dari section yang ditemukan:**
Catat secara berurutan:
- Nama font dan ukuran body (pt)
- Ukuran font heading — jika tidak disebutkan terpisah dari body, gunakan ukuran body sebagai fallback
- Apakah judul BAB dicetak tebal (bold)?
- Apakah judul BAB ditulis ALL CAPS?

Contoh penalaran: *"Font: Times New Roman 12pt. Heading tidak disebutkan → pakai 12pt juga. Judul BAB muncul sebagai '**BAB 1 PENDAHULUAN**' → heading_bold=true, heading_all_caps=true."*

**Langkah 3 — Validasi fokus proposal:**
Pastikan nilai yang diekstrak berasal dari ketentuan untuk **proposal PKM**. Jika konteks memuat aturan berbeda antara proposal dan laporan, ambil hanya aturan proposal. Jika aturan berlaku untuk semua jenis dokumen PKM, masukkan ke output.

**Langkah 4 — Validasi tipe data:**
- `font_size_heading_pt` tidak boleh null jika `font_size_body_pt` sudah diketahui (terapkan fallback ke nilai body)
- `heading_bold` dan `heading_all_caps` harus bertipe bool, bukan string

## Normalization Rules
- Gunakan JSON null (bukan string "null") untuk nilai yang tidak ditemukan
- font_size_heading_pt: keluarkan sebagai integer pt (contoh: 12)
  - **Fallback**: Jika dokumen tidak menyebut ukuran font heading secara eksplisit dan berbeda dari body, gunakan nilai yang sama dengan `font_size_body_pt` (bukan null). Null hanya digunakan jika ukuran font body JUGA tidak diketahui.
- heading_bold: true jika heading/judul BAB dicetak tebal (bold), false jika tidak
  - Jika konteks menampilkan judul BAB/DAFTAR/RINGKASAN dengan markdown tebal `**...**`, anggap itu bukti bahwa heading dicetak tebal (heading_bold=true) meskipun kata "bold" tidak ditulis eksplisit.
- heading_all_caps: true jika judul BAB ditulis ALL CAPS, false jika tidak (Title Case, Sentence Case, dsb.)

## Output Fields
- font_family: nama font utama dokumen (contoh: "Times New Roman")
- font_size_body_pt: ukuran font body dalam satuan pt sebagai integer (contoh: 12)
- font_size_heading_pt: ukuran font heading dalam satuan pt sebagai integer
- heading_bold: apakah judul BAB dicetak tebal/bold (bool — true/false, bukan string)
- heading_all_caps: apakah judul BAB ditulis ALL CAPS (bool — true/false, bukan string)
