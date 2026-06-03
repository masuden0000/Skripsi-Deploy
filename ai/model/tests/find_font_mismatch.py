"""Cari paragraf Normal bergaya Arial/11pt di file_target.docx."""
import sys
from pathlib import Path
from docx import Document

docx_path = Path(__file__).parent / "file_target.docx"
doc = Document(str(docx_path))

results = []
for i, para in enumerate(doc.paragraphs):
    if para.style.name != "Normal":
        continue
    text = para.text.strip()
    if not text:
        continue
    for run in para.runs:
        if not run.text.strip():
            continue
        name = run.font.name
        size = run.font.size
        size_pt = round(size.pt, 1) if size else None
        if name == "Arial" or size_pt == 11.0:
            results.append({
                "para_idx": i,
                "text_preview": text[:100],
                "font": name,
                "size_pt": size_pt,
            })
            break

print(f"Ditemukan {len(results)} paragraf Normal dengan Arial/11pt:\n")
for r in results:
    print(f'  Para #{r["para_idx"]:>4}: font={str(r["font"]):>12} | {r["size_pt"]}pt | "{r["text_preview"]}"')
