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
def run_setup(project_id: str | None = None, skip_ingest: bool = False) -> None:
    from model_ai.loader.pdf_extractor import extract_chunks
    from model_ai.loader.supabase_ingest import upsert_embeddings

    total_chunks, output_path = extract_chunks(project_id=project_id)
    print(f"[setup] Berhasil membuat {total_chunks} chunk: {output_path}")

    if skip_ingest:
        print("[setup] Ingest ke Supabase dilewati.")
        return

    total_rows = upsert_embeddings(project_id=project_id)
    print(f"[setup] Berhasil upsert {total_rows} chunk ke Supabase.")


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `run_extract` sebagai bagian alur `manage`.
# ---------------------------------------------------------------------------
def run_extract(project_id: str | None = None) -> None:
    from model_ai.extractor.doc_extractor import run_extraction

    run_extraction(project_id)


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `run_docx` sebagai bagian alur `manage`.
# ---------------------------------------------------------------------------
def run_docx(
    doc_type: str,
    project_id: str | None,
    output_json: str,
    chunks_path: str,
    output_path: str,
) -> str | None:
    if doc_type != "proposal":
        raise SystemExit(
            f"Tipe dokumen '{doc_type}' belum didukung. Gunakan '--type proposal'."
        )

    from model_ai.docx.generator import generate_proposal_docx

    # Build project-specific paths if project_id is provided
    output_json_path = resolve_ai_path(output_json)
    chunks_path_resolved = resolve_ai_path(chunks_path)
    output_path_resolved = resolve_ai_path(output_path)

    if project_id:
        output_json_path = AI_DIR / "data" / project_id / "output.json"
        chunks_path_resolved = AI_DIR / "data" / project_id / "output_chunks.json"
        output_path_resolved = AI_DIR / "data" / project_id / "proposal_output.docx"

    generated_path = generate_proposal_docx(
        output_json_path=output_json_path,
        chunks_path=chunks_path_resolved,
        output_path=output_path_resolved,
    )
    print(f"[docx] Berhasil membuat dokumen: {generated_path}")
    return str(generated_path)


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
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `run_validate` sebagai bagian alur `manage`.
# ---------------------------------------------------------------------------
def run_validate(project_id: str | None = None, source_doc: str | None = None) -> None:
    from model_ai.metadata_repository import load_document_metadata_payload
    from model_ai.validation.validator import validate_and_print

    # Resolve paths
    if project_id:
        docx_path = AI_DIR / "data" / project_id / "file_target.docx"
    else:
        docx_path = AI_DIR / "data" / "file_target.docx"

    if not docx_path.exists():
        raise SystemExit(f"File tidak ditemukan: {docx_path}")

    # Load metadata from Supabase
    if source_doc is None:
        # Default: gunakan nama file DOCX sebagai source_doc
        source_doc = docx_path.name

    payload = load_document_metadata_payload(source_doc)
    print(f"[validate] Loaded metadata untuk source_doc: {source_doc}")

    # Run validation
    result = validate_and_print(str(docx_path), payload)

    if result.status != "pass":
        raise SystemExit(1)


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
        "--project-id",
        help="Project ID untuk isolate output per-project.",
    )
    setup_parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Hanya buat output_chunks.json tanpa mengirim embedding ke Supabase.",
    )

    extract_parser = subparsers.add_parser(
        "extract",
        help="Ekstrak metadata terstruktur dari chunks Supabase dan simpan ke document_metadata.",
    )
    extract_parser.add_argument(
        "--project-id",
        help="Project ID untuk isolate extraction per-project.",
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
        help="Generate dokumen DOCX berdasarkan output.json hasil ekstraksi.",
    )
    docx_parser.add_argument(
        "--type",
        dest="doc_type",
        required=True,
        choices=["proposal"],
        help="Tipe dokumen yang akan digenerate.",
    )
    docx_parser.add_argument(
        "--project-id",
        help="Project ID untuk isolate output per-project (default: gunakan path default).",
    )
    docx_parser.add_argument(
        "--output-json",
        default="data/output.json",
        help="Path file output.json hasil ekstraksi (default: data/output.json).",
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

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validasi format dokumen DOCX terhadap rules di document_metadata.",
    )
    validate_parser.add_argument(
        "--project-id",
        help="Project ID untuk isolate output per-project (default: data/file_target.docx).",
    )
    validate_parser.add_argument(
        "--source-doc",
        help="Nama file PDF sumber sebagai selector document_metadata (default: nama file DOCX).",
    )

    args = parser.parse_args()

    if args.command == "setup":
        run_setup(project_id=getattr(args, "project_id", None), skip_ingest=args.skip_ingest)
        return

    if args.command == "extract":
        run_extract(project_id=args.project_id)
        return

    if args.command == "schema-diff":
        run_schema_diff_cmd(source_doc=args.source_doc)
        return

    if args.command == "docx":
        run_docx(
            doc_type=args.doc_type,
            project_id=args.project_id,
            output_json=args.output_json,
            chunks_path=args.chunks,
            output_path=args.output,
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

    if args.command == "validate":
        run_validate(
            project_id=getattr(args, "project_id", None),
            source_doc=getattr(args, "source_doc", None),
        )
        return


if __name__ == "__main__":
    main()
