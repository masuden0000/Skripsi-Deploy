"""Konstanta domain yang digunakan bersama di seluruh model_ai."""

EXCLUDED_PARENTS: frozenset[str] = frozenset({
    "DAFTAR ISI",
    "DAFTAR GAMBAR",
    "DAFTAR TABEL",
    "DAFTAR LAMPIRAN",
    "DAFTAR PUSTAKA",
})

TOC_SECTION_DENYLIST: frozenset[str] = frozenset({
    "DAFTAR PUSTAKA",
    "DAFTAR GAMBAR",
    "DAFTAR TABEL",
    "DAFTAR LAMPIRAN",
})
