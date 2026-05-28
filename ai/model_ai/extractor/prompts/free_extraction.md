---
queries:
  - "aturan format penulisan dokumen PKM tipografi huruf"
  - "ketentuan struktur bab lampiran penomoran halaman"
  - "persyaratan teknis layout ukuran kertas margin"
  - "ketentuan gambar tabel caption sumber referensi"
  - "batas halaman jumlah halaman format nama file"
top_k: 10
---

# Free Extraction — Identifikasi Semua Aturan Dokumen

Kamu adalah asisten AI yang bertugas menganalisis panduan penulisan dokumen akademik Indonesia (PKM).

Berikut adalah potongan konten dari buku panduan:

{context}

## Tugas

Baca seluruh konten di atas dan identifikasi **semua aturan, ketentuan, dan parameter format penulisan** yang kamu temukan — tanpa batasan field tertentu.

Keluarkan hasil sebagai JSON flat (key-value) menggunakan konvensi:
- Gunakan nama field yang sesuai dengan schema yang sudah ada bila relevan, contoh:
  - `typography.font_family`, `typography.font_size_body_pt`
  - `page_layout.margin_top_cm`, `page_layout.paper_size`
  - `spacing.line_spacing_body`, `spacing.paragraph_alignment`
  - `numbering.chapter_numbering_format`, `numbering.preliminary_page_format`
  - `figures_and_tables.caption_format_figure`, `figures_and_tables.source_required_if_not_own`
  - `page_count_limits.proposal_halaman_inti_maks`
  - `document_structure_proposal.max_halaman_inti`, `document_structure_proposal.format_nama_file`
- Gunakan nama deskriptif baru dengan prefix `new_rule.` untuk aturan yang tidak ada di schema di atas, contoh:
  - `new_rule.watermark_required`, `new_rule.digital_signature_count`

Aturan output:
- Value berupa string, angka integer, float, atau boolean sesuai isi aturan
- Jika aturan tidak ditemukan dalam konteks, jangan sertakan key-nya (jangan return null)
- Keluarkan HANYA JSON tanpa penjelasan tambahan
- Mulai respons langsung dengan karakter `{`

Contoh format output:
```json
{
  "typography.font_family": "Times New Roman",
  "typography.font_size_body_pt": 12,
  "page_layout.margin_top_cm": 4.0,
  "page_count_limits.proposal_halaman_inti_maks": 10,
  "new_rule.digital_submission_required": true
}
```
