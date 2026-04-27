import argparse
import sys
from pathlib import Path


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


def run_extract() -> None:
    from model_ai.extractor.doc_extractor import run_extraction

    run_extraction()


def run_schema_diff_cmd() -> None:
    from model_ai.extractor.schema_differ import run_schema_diff

    run_schema_diff()


def run_docx(
    doc_type: str,
    input_path: str,
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
        metadata_path=Path(input_path),
        chunks_path=Path(chunks_path),
        output_path=Path(output_path),
        use_llm_normalization=use_llm_normalization,
    )
    print(f"[docx] Berhasil membuat dokumen: {generated_path}")


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
        "ui",
        help="Jalankan web chat UI yang terhubung ke model_ai.rag.rag_service.",
    )

    subparsers.add_parser(
        "extract",
        help="Ekstrak metadata terstruktur dari chunks Supabase dan simpan ke output.json.",
    )

    subparsers.add_parser(
        "schema-diff",
        help=(
            "Jalankan free extraction via LLM lalu bandingkan terhadap output.json. "
            "Simpan laporan diff ke data/schema_diff_<timestamp>.json dan .md."
        ),
    )

    docx_parser = subparsers.add_parser(
        "docx",
        help="Generate dokumen DOCX berdasarkan output metadata extractor.",
    )
    docx_parser.add_argument(
        "--type",
        dest="doc_type",
        required=True,
        choices=["proposal"],
        help="Tipe dokumen yang akan digenerate.",
    )
    docx_parser.add_argument(
        "--input",
        default="data/output.json",
        help="Path input metadata JSON (default: data/output.json).",
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
        help="Nonaktifkan LLM translator untuk normalisasi nilai deskriptif.",
    )

    args = parser.parse_args()

    if args.command == "setup":
        run_setup(skip_ingest=args.skip_ingest)
        return

    if args.command == "ui":
        from model_ai.ui.chat_server import main as run_chat_server

        run_chat_server()

    if args.command == "extract":
        run_extract()
        return

    if args.command == "schema-diff":
        run_schema_diff_cmd()
        return

    if args.command == "docx":
        run_docx(
            doc_type=args.doc_type,
            input_path=args.input,
            chunks_path=args.chunks,
            output_path=args.output,
            use_llm_normalization=not args.no_llm_normalization,
        )
        return


if __name__ == "__main__":
    main()
