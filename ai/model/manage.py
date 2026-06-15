"""CLI entry point untuk menjalankan subperintah pipeline. Dipanggil oleh ai/backend/services/pipeline.py via subprocess. Posisi pipeline: entry point utama (setup → extract → generate-placeholders → docx → validate). Keyword: automated document generation"""
import argparse
import sys
from pathlib import Path


AI_DIR = Path(__file__).resolve().parent


def resolve_ai_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == AI_DIR.name:
        return AI_DIR.parent / path
    return AI_DIR / path


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


def run_setup(project_id: str, skip_ingest: bool = False) -> None:
    from model_ai.loader.pdf_extractor import extract_chunks
    from model_ai.loader.supabase_ingest import upsert_embeddings

    total_chunks, output_path = extract_chunks(project_id=project_id)
    print(f"[setup] Berhasil membuat {total_chunks} chunk: {output_path}")

    if skip_ingest:
        print("[setup] Ingest ke Supabase dilewati.")
        return

    total_rows = upsert_embeddings(project_id=project_id)
    print(f"[setup] Berhasil upsert {total_rows} chunk ke Supabase.")


def run_extract(project_id: str | None = None, skema: str = "PKM-KC") -> None:
    from model_ai.extractor.doc_extractor import run_extraction

    run_extraction(project_id=project_id, skema=skema)


def run_docx(project_id: str, skema: str = "PKM-KC", local_output: str | None = None) -> str | None:
    from model_ai.docx.generator import generate_proposal_docx_bytes

    doc_bytes, file_name = generate_proposal_docx_bytes(
        project_id=project_id,
        skema=skema,
    )

    if local_output:
        out_path = resolve_ai_path(local_output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(doc_bytes)
        print(f"[docx] Disimpan lokal: {out_path}")
        return str(out_path)

    from model_ai.storage import upload_docx_to_storage
    result_url = upload_docx_to_storage(doc_bytes, file_name, project_id)
    print(f"[docx] Berhasil upload dokumen: {result_url}")
    print(f"[docx] RESULT_URL={result_url}")
    return result_url


def run_generate_placeholders(project_id: str, skema: str = "PKM-KC") -> None:
    """Generate instructional placeholder via LLM dan simpan ke DB."""
    from model_ai.docx.chunk_loader import load_chunk_sources
    from model_ai.docx.instructional_placeholder_builder import build_instructional_placeholder_map
    from model_ai.metadata_repository import load_document_metadata, save_generated_placeholders
    from model_ai.shared import is_type_b

    print(f"[generate-placeholders] Memuat metadata dan chunks untuk project: {project_id} (skema: {skema})", flush=True)
    metadata = load_document_metadata(project_id)
    chunks = load_chunk_sources(project_id)

    doc_structure = metadata.document_structure_artikel if is_type_b(skema) else metadata.document_structure_proposal
    total = len(doc_structure.sections) if doc_structure else 0
    print(f"[generate-placeholders] {total} section ditemukan. Memulai generate placeholder...", flush=True)

    generated = build_instructional_placeholder_map(
        metadata=metadata,
        chunks=chunks,
        use_llm=True,
    )

    print(f"[generate-placeholders] {len(generated)} placeholder selesai. Menyimpan ke DB...", flush=True)
    save_generated_placeholders(project_id, generated, skema=skema)
    print("[generate-placeholders] Selesai. Placeholder tersimpan ke DB.", flush=True)


def run_export_payload(project_id: str, output: str | None = None) -> None:
    import json
    from model_ai.metadata_repository import load_document_metadata_payload

    payload = load_document_metadata_payload(project_id)

    out_path = resolve_ai_path(output) if output else AI_DIR / "data" / f"payload_{project_id}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"[export-payload] Payload disimpan ke: {out_path}")


def run_validate(project_id: str | None = None, output_json: str | None = None) -> None:
    import json
    from model_ai.validation.validator import validate_and_print

    if project_id:
        docx_path = AI_DIR / "data" / project_id / "file_target.docx"
        default_output_json = AI_DIR / "data" / project_id / "output.json"
    else:
        docx_path = AI_DIR / "data" / "file_target.docx"
        default_output_json = AI_DIR / "data" / "output.json"

    if not docx_path.exists():
        raise SystemExit(f"File tidak ditemukan: {docx_path}")

    json_path = AI_DIR / output_json if output_json else default_output_json

    if not json_path.exists():
        raise SystemExit(f"File output.json tidak ditemukan: {json_path}")

    with open(json_path, encoding="utf-8") as f:
        payload = json.load(f)

    print(f"[validate] Loaded metadata dari: {json_path}")

    result = validate_and_print(str(docx_path), payload)

    import json as _json
    out_json_path = docx_path.parent / "validation_result.json"
    with open(out_json_path, "w", encoding="utf-8") as f:
        _json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
    print(f"[validate] Hasil disimpan ke: {out_json_path}")

    if result.status != "pass":
        raise SystemExit(1)


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
        required=True,
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
    extract_parser.add_argument(
        "--skema",
        default="PKM-KC",
        help="Skema PKM project (contoh: PKM-KC, PKM-RE, PKM-AI). Default: PKM-KC.",
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
    docx_parser.add_argument(
        "--skema",
        default="PKM-KC",
        help="Skema PKM project (contoh: PKM-KC, PKM-RE, PKM-AI). Default: PKM-KC.",
    )
    docx_parser.add_argument(
        "--local",
        action="store_true",
        help="Simpan DOCX ke lokal saja, skip upload ke Supabase storage.",
    )

    export_payload_parser = subparsers.add_parser(
        "export-payload",
        help="Export document_metadata.payload dari Supabase ke file JSON lokal.",
    )
    export_payload_parser.add_argument(
        "--project-id",
        required=True,
        help="Project ID sebagai selector document_metadata.",
    )
    export_payload_parser.add_argument(
        "--output",
        help="Path output JSON (default: data/payload_<project-id>.json).",
    )

    gen_ph_parser = subparsers.add_parser(
        "generate-placeholders",
        help="Generate instructional placeholder via LLM dan simpan ke DB.",
    )
    gen_ph_parser.add_argument(
        "--project-id",
        required=True,
        help="Project ID.",
    )
    gen_ph_parser.add_argument(
        "--skema",
        default="PKM-KC",
        help="Skema PKM project (contoh: PKM-KC, PKM-AI). Default: PKM-KC.",
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validasi format dokumen DOCX terhadap rules dari output.json lokal.",
    )
    validate_parser.add_argument(
        "--project-id",
        help="Project ID untuk isolate per-project (default: data/file_target.docx + data/output.json).",
    )
    validate_parser.add_argument(
        "--output-json",
        help="Path output.json sebagai ground truth (default: data/output.json atau data/{project-id}/output.json).",
    )

    args = parser.parse_args()

    if args.command == "setup":
        run_setup(project_id=args.project_id, skip_ingest=args.skip_ingest)
        return

    if args.command == "extract":
        run_extract(project_id=args.project_id, skema=args.skema)
        return

    if args.command == "docx":
        if args.doc_type != "proposal":
            raise SystemExit("Tipe dokumen belum didukung.")
        if not args.project_id:
            raise SystemExit("--project-id wajib untuk perintah docx.")
        run_docx(
            project_id=args.project_id,
            skema=args.skema,
            local_output=args.output if args.local else None,
        )
        return

    if args.command == "generate-placeholders":
        run_generate_placeholders(project_id=args.project_id, skema=args.skema)
        return

    if args.command == "export-payload":
        run_export_payload(
            project_id=args.project_id,
            output=getattr(args, "output", None),
        )
        return

    if args.command == "validate":
        run_validate(
            project_id=getattr(args, "project_id", None),
            output_json=getattr(args, "output_json", None),
        )
        return


if __name__ == "__main__":
    main()
