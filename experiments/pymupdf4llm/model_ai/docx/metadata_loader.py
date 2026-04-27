import json
from pathlib import Path

from model_ai.extractor.models import DocumentMetadata


def load_document_metadata(path: Path) -> DocumentMetadata:
    if not path.exists():
        raise FileNotFoundError(f"File metadata tidak ditemukan: {path}")

    with open(path, encoding="utf-8") as f:
        payload = json.load(f)

    return DocumentMetadata.model_validate(payload)
