#
#    Copyright 2017 Vitalii Kulanov
#

__all__ = ['DocumentWrapper']

from docx.oxml.ns import qn


class DocumentWrapper(object):
    """Wrapper class for retrieving docx document attributes."""

    def __init__(self, document):
        self._document = document
        self._author = document.core_properties.author
        self._created = document.core_properties.created
        self._modified = document.core_properties.modified
        self._last_modified_by = document.core_properties.last_modified_by
        self._doc_defaults = self._read_doc_defaults()

    def _read_doc_defaults(self):
        """
        Baca docDefaults dari styles.xml di dalam .docx.

        docDefaults adalah lapisan terbawah formatting — berlaku ke seluruh
        dokumen jika paragraf dan style tidak mendefinisikan nilainya sendiri.
        Disimpan di: word/styles.xml → <w:docDefaults> → <w:pPrDefault> (paragraf)
        dan <w:rPrDefault> (run/font).

        Contoh XML:
          <w:pPrDefault>
            <w:pPr>
              <w:spacing w:line="276" w:lineRule="auto"/>
            </w:pPr>
          </w:pPrDefault>
          <w:rPrDefault>
            <w:rPr>
              <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
              <w:sz w:val="24"/>  <!-- 24 half-points = 12pt -->
            </w:rPr>
          </w:rPrDefault>

        w:line="276" dengan lineRule="auto" → 276 ÷ 240 = 1.15x (MULTIPLE)
        w:sz w:val="24" → 24 ÷ 2 = 12pt
        """
        defaults = {}
        try:
            styles_el = self._document.styles.element
            spacing = styles_el.find(
                f'.//{qn("w:pPrDefault")}/{qn("w:pPr")}/{qn("w:spacing")}'
            )
            if spacing is not None:
                line      = spacing.get(qn('w:line'))
                line_rule = spacing.get(qn('w:lineRule'))
                if line and line_rule == 'auto':
                    defaults['line_spacing'] = int(line) / 240
            rPr = styles_el.find(f'.//{qn("w:rPrDefault")}/{qn("w:rPr")}')
            if rPr is not None:
                rFonts = rPr.find(qn('w:rFonts'))
                if rFonts is not None:
                    name = (rFonts.get(qn('w:ascii')) or
                            rFonts.get(qn('w:hAnsi')))
                    if name:
                        defaults['font_name'] = name
                sz = rPr.find(qn('w:sz'))
                if sz is not None:
                    val = sz.get(qn('w:val'))
                    if val:
                        defaults['font_size_pt'] = int(val) / 2
        except Exception:
            pass
        return defaults

    @property
    def author(self):
        return self._author

    @property
    def created(self):
        return self._created

    @property
    def modified(self):
        return self._modified

    @property
    def last_modified_by(self):
        return self._last_modified_by

    def iter_paragraphs(self, styles=None):
        """Get paragraphs of a document, termasuk paragraf di dalam w:sdt.

        python-docx standar (doc.paragraphs) hanya mengembalikan w:p yang langsung
        ada di w:body. Elemen w:sdt (Structured Document Tag) seperti Table of
        Contents yang dibuat otomatis Word menyimpan paragraf di dalam dirinya —
        dan tidak ikut dalam doc.paragraphs.

        Method ini menelusuri langsung elemen-elemen w:body, lalu untuk setiap
        w:sdt juga menelusuri semua w:p di dalamnya secara rekursif.
        """
        from docx.text.paragraph import Paragraph

        body = self._document.element.body

        for child in body:
            if child.tag == qn("w:p"):
                para = Paragraph(child, self._document)
                if not styles or para.style.name in styles:
                    yield para
            elif child.tag == qn("w:sdt"):
                for p_el in child.iter(qn("w:p")):
                    para = Paragraph(p_el, self._document)
                    if not styles or para.style.name in styles:
                        yield para

    def iter_sections(self):
        """Iterate over sections in docx document."""
        for section in self._document.sections:
            yield section

    _IGNORE_FONT_ATTRS = frozenset({'italic', 'cs_italic', 'cs_bold'})

    def _get_normal_style_font_attr(self, attr):
        """Baca nilai font dari style 'Normal' sebagai final fallback."""
        try:
            normal = self._document.styles['Normal']
            value = getattr(normal.font, attr, None)
            if value is not None:
                return value
            return self._find_paragraph_attribute(normal, 'font', attr)
        except (KeyError, AttributeError):
            return None

    def get_font_attributes(self, paragraph, unit='pt'):
        """Get font attributes for specified paragraph.

        Fallback chain untuk size dan name (setara dengan get_paragraph_attributes):
          1. Run font (eksplisit di run XML)
          2. Style chain (base_style → ancestor)
          3. docDefaults (rPrDefault di styles.xml)
          4. Style Normal sebagai final fallback
        """
        runs = []
        for run in paragraph.runs:
            size = (run.font.size or
                    self._find_paragraph_attribute(paragraph.style, 'font', 'size') or
                    self._doc_defaults.get('font_size_pt') or
                    self._get_normal_style_font_attr('size'))
            family = (run.font.name or
                      self._find_paragraph_attribute(paragraph.style, 'font', 'name') or
                      self._doc_defaults.get('font_name') or
                      self._get_normal_style_font_attr('name'))
            fetched_attributes = [self._convert_unit(size, unit), family]
            for attr, member in type(paragraph.style.font).__dict__.items():
                if isinstance(member, property) and attr not in self._IGNORE_FONT_ATTRS:
                    val = (run.font.__getattribute__(attr) or
                           paragraph.style.font.__getattribute__(attr))
                    if val is True:
                        fetched_attributes.append(attr)
            runs.append(fetched_attributes)
        return runs

    def get_section_attributes(self, section, unit='cm'):
        """Get attributes for specified section."""
        fetched_attributes = {
            attr: self._convert_unit(section.__getattribute__(attr), unit)
            for attr, p in type(section).__dict__.items()
            if isinstance(p, property)
        }
        return fetched_attributes

    def get_paragraph_attributes(self, paragraph, unit='cm'):
        """Get attributes for specified paragraph.

        Urutan pencarian nilai:
          1. Paragraf itu sendiri (override manual)
          2. Style chain paragraf (base_style → dst)
          3. docDefaults (default seluruh dokumen, tersimpan di styles.xml)
          4. Style 'Normal' sebagai final fallback — Word menggunakannya sebagai
             default universal ketika tidak ada lapisan lain yang mendefinisikan nilai.
             Ini mencegah false-positive "inherited" warning pada style kustom
             (mis. 'Lampiran') yang mewarisi JUSTIFY dari Normal secara implisit.
        """
        _except_attributes = ('tab_stops', 'first_line_indent')

        fetched_attributes = {}
        for attr, member in type(paragraph.paragraph_format).__dict__.items():
            if isinstance(member, property) and attr not in _except_attributes:
                value = (
                    paragraph.paragraph_format.__getattribute__(attr) or
                    self._find_paragraph_attribute(
                        paragraph.style, 'paragraph_format', attr) or
                    self._doc_defaults.get(attr) or
                    self._get_normal_style_attr(attr)
                )
                fetched_attributes[attr] = self._convert_unit(value, unit)
        return fetched_attributes

    def _get_normal_style_attr(self, attr):
        """Baca nilai atribut paragraf dari style 'Normal' sebagai final fallback."""
        try:
            normal = self._document.styles['Normal']
            value = normal.paragraph_format.__getattribute__(attr)
            if value is not None:
                return value
            return self._find_paragraph_attribute(normal, 'paragraph_format', attr)
        except (KeyError, AttributeError):
            return None

    def _find_paragraph_attribute(self, p_style, p_element, attr):
        value = p_style.__getattribute__(p_element).__getattribute__(attr)
        if value is None and p_style.base_style is not None:
            return self._find_paragraph_attribute(p_style.base_style,
                                                  p_element, attr)
        return value

    @staticmethod
    def _convert_unit(value, unit):
        try:
            value = value.__getattribute__(unit)
        except AttributeError:
            pass
        return value
