from pathlib import Path

if __package__:
    from ..loader.pdf_extractor import get_page_chunks
else:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from model_ai.loader.pdf_extractor import get_page_chunks


def main() -> None:
    page_chunks = get_page_chunks()
    print(page_chunks)


if __name__ == "__main__":
    main()
