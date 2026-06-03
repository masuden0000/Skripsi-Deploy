"""Diagnosa mendalam font pada paragraf Daftar Pustaka."""
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

docx_path = Path(__file__).parent / "file_target.docx"
doc = Document(str(docx_path))

TARGET_PARAS = [115, 117, 123]

for idx in TARGET_PARAS:
    para = doc.paragraphs[idx]
    print(f"\n{'='*70}")
    print(f"Para #{idx} | Style: '{para.style.name}' | Text: '{para.text[:60]}'")
    print(f"{'='*70}")

    # 1. Font di level style chain
    style = para.style
    chain = []
    while style:
        chain.append(f"  Style '{style.name}': font.name={style.font.name!r}")
        style = style.base_style
    print("Style chain:")
    for c in chain:
        print(c)

    # 2. Font di level run
    print(f"\nRuns ({len(para.runs)}):")
    for i, run in enumerate(para.runs):
        print(f"  Run #{i}: text={run.text[:30]!r:35} | font.name={run.font.name!r} | font.size={run.font.size}")

    # 3. XML mentah paragraph (rPr)
    print("\nXML rPr per run:")
    for i, run in enumerate(para.runs[:5]):  # maks 5 run
        rpr = run._r.find(qn("w:rPr"))
        if rpr is not None:
            fonts_el = rpr.find(qn("w:rFonts"))
            if fonts_el is not None:
                attrs = dict(fonts_el.attrib)
                print(f"  Run #{i}: rFonts = {attrs}")
            else:
                print(f"  Run #{i}: tidak ada rFonts di rPr")
        else:
            print(f"  Run #{i}: tidak ada rPr")

    # 4. Cek theme font di document
    print()
