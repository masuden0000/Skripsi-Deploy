"""
Fungsi: Entry point CLI untuk menjalankan workflow setup, extract, schema-diff, dan docx.

Digunakan oleh: Dijalankan langsung oleh pengguna via command line.

Tujuan: Menyediakan satu pintu eksekusi agar pipeline bisa dijalankan konsisten dari command line.
"""
import argparse
import sys
from pathlib import Path


AI_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Digunakan oleh: run_docx dan run_docx_style_map.
# Menormalkan path relatif CLI agar selalu mengarah ke folder ai/.
# ---------------------------------------------------------------------------
def resolve_ai_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == AI_DIR.name:
        return AI_DIR.parent / path
    return AI_DIR / path


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `ensure_supported_python` sebagai bagian alur `manage`.
# ---------------------------------------------------------------------------
def ensure_supported_python() -> None:
    version = sys.version_info
    if version < (3, 11):
        raise SystemExit(
            "Project pymupdf4llm membutuhkan Python 3.11 atau 3.12. "
            f"Versi aktif saat ini: {version.major}.{version.minor}.{version.micro}."
        )

    if version >= (3, 14):
        raise SystemExit(
            "Python 3.14+ belum diuji untuk project pymupdf4llm. "
            f"Versi aktif saat ini: {version.major}.{version.minor}.{version.micro}. "
            "Gunakan Python 3.11, 3.12, atau 3.13."
        )


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `run_setup` sebagai bagian alur `manage`.
# ---------------------------------------------------------------------------
def run_setup(skip_ingest: bool = False) -> None:
    from model_ai.loader.pdf_extractor import extract_chunks
    from model_ai.loader.supabase_ingest import upsert_embeddings

    total_chunks, output_path = extract_chunks()
    print(f"[setup] Berhasil membuat {total_chunks} chunk: {output_path}")

    if skip_ingest:
        print("[setup] Ingest ke Supabase dilewati.")
        return

    total_rows = upsert_embeddings()
    print(f"[setup] Berhasil upsert {total_rows} chunk ke Supabase.")


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `run_extract` sebagai bagian alur `manage`.
# ---------------------------------------------------------------------------
def run_extract() -> None:
    from model_ai.extractor.doc_extractor import run_extraction

    run_extraction()


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `run_docx` sebagai bagian alur `manage`.
# ---------------------------------------------------------------------------
def run_docx(
    doc_type: str,
    source_doc: str,
    chunks_path: str,
    output_path: str,
    use_llm_normalization: bool,
) -> None:
    if doc_type != "proposal":
        raise SystemExit(
            f"Tipe dokumen '{doc_type}' belum didukung. Gunakan '--type proposal'."
        )

    from model_ai.docx.generator import generate_proposal_docx

    generated_path = generate_proposal_docx(
        source_doc=source_doc,
        chunks_path=resolve_ai_path(chunks_path),
        output_path=resolve_ai_path(output_path),
        use_llm_normalization=use_llm_normalization,
    )
    print(f"[docx] Berhasil membuat dokumen: {generated_path}")


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `run_docx_style_map` sebagai bagian alur `manage`.
# ---------------------------------------------------------------------------
def run_docx_style_map(
    source_doc: str,
    dictionary_path: str,
    with_embeddings: bool,
    use_llm_mapper: bool,
) -> None:
    from model_ai.docx.style_mapping_pipeline import run_docx_style_mapping_pipeline
    from model_ai.metadata_repository import load_document_metadata_payload

    run_docx_style_mapping_pipeline(
        dictionary_path=resolve_ai_path(dictionary_path),
        extracted_payload=load_document_metadata_payload(source_doc),
        with_embeddings=with_embeddings,
        use_llm_mapper=use_llm_mapper,
    )


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `run_schema_diff_cmd` sebagai bagian alur `manage`.
# ---------------------------------------------------------------------------
def run_schema_diff_cmd(source_doc: str) -> None:
    from model_ai.extractor.schema_differ import run_schema_diff

    run_schema_diff(source_doc)


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/loader/pdf_extractor.py; model_ai/loader/supabase_ingest.py
# Menjalankan fungsi `main` sebagai bagian alur `manage`.
# ---------------------------------------------------------------------------
def main() -> None:
    ensure_supported_python()

    parser = argparse.ArgumentParser(
        description="Command runner untuk pipeline PyMuPDF4LLM + RAG."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup_parser = subparsers.add_parser(
        "setup",
        help="Jalankan extractor/chunking lalu ingest ke Supabase.",
    )
    setup_parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Hanya buat output_chunks.json tanpa mengirim embedding ke Supabase.",
    )

    subparsers.add_parser(
        "extract",
        help="Ekstrak metadata terstruktur dari chunks Supabase dan simpan ke document_metadata.",
    )

    schema_diff_parser = subparsers.add_parser(
        "schema-diff",
        help=(
            "Jalankan free extraction via LLM lalu bandingkan terhadap baseline document_metadata. "
            "Simpan laporan diff ke data/schema_diff_<timestamp>.json dan .md."
        ),
    )
    schema_diff_parser.add_argument(
        "--source-doc",
        required=True,
        help="Nama file PDF sumber yang dipakai sebagai selector document_metadata.",
    )

    docx_parser = subparsers.add_parser(
        "docx",
        help="Generate dokumen DOCX berdasarkan metadata document_metadata di Supabase.",
    )
    docx_parser.add_argument(
        "--type",
        dest="doc_type",
        required=True,
        choices=["proposal"],
        help="Tipe dokumen yang akan digenerate.",
    )
    docx_parser.add_argument(
        "--source-doc",
        required=True,
        help="Nama file PDF sumber yang dipakai sebagai selector document_metadata.",
    )
    docx_parser.add_argument(
        "--chunks",
        default="data/output_chunks.json",
        help="Path input chunk JSON (default: data/output_chunks.json).",
    )
    docx_parser.add_argument(
        "--output",
        default="data/proposal_template.docx",
        help="Path output DOCX (default: data/proposal_template.docx).",
    )
    docx_parser.add_argument(
        "--no-llm-normalization",
        action="store_true",
        help="Nonaktifkan mapper LLM+embedding dan pakai translasi style deterministik.",
    )

    map_parser = subparsers.add_parser(
        "docx-style-map",
        help=(
            "Bangun catalog python-docx + chunk index, lalu lakukan retrieval, "
            "candidate mapping, validasi, dan apply-plan audit."
        ),
    )
    map_parser.add_argument(
        "--dictionary",
        default="data/python_docx_full_dictionary.yaml",
        help="Path dictionary python-docx YAML.",
    )
    map_parser.add_argument(
        "--source-doc",
        required=True,
        help="Nama file PDF sumber yang dipakai sebagai selector document_metadata.",
    )
    map_parser.add_argument(
        "--no-embeddings",
        action="store_true",
        help="Gunakan retrieval lexical saja (tanpa embedding index).",
    )
    map_parser.add_argument(
        "--no-llm-mapper",
        action="store_true",
        help="Gunakan mapper rule-based sederhana tanpa LLM.",
    )

    args = parser.parse_args()

    if args.command == "setup":
        run_setup(skip_ingest=args.skip_ingest)
        return

    if args.command == "extract":
        run_extract()
        return

    if args.command == "schema-diff":
        run_schema_diff_cmd(source_doc=args.source_doc)
        return

    if args.command == "docx":
        run_docx(
            doc_type=args.doc_type,
            source_doc=args.source_doc,
            chunks_path=args.chunks,
            output_path=args.output,
            use_llm_normalization=not args.no_llm_normalization,
        )
        return

    if args.command == "docx-style-map":
        run_docx_style_map(
            source_doc=args.source_doc,
            dictionary_path=args.dictionary,
            with_embeddings=not args.no_embeddings,
            use_llm_mapper=not args.no_llm_mapper,
        )
        return


if __name__ == "__main__":
    main()
