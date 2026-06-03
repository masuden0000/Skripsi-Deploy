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
        Disimpan di: word/styles.xml → <w:docDefaults> → <w:pPrDefault>

        Contoh XML:
          <w:pPrDefault>
            <w:pPr>
              <w:spacing w:line="276" w:lineRule="auto"/>
            </w:pPr>
          </w:pPrDefault>

        w:line="276" dengan lineRule="auto" → 276 ÷ 240 = 1.15x (MULTIPLE)
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
                    # "auto" = MULTIPLE — nilai dalam 240ths of a line
                    defaults['line_spacing'] = int(line) / 240
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
        """Get paragraphs of specific styles of a document."""
        for paragraph in self._document.paragraphs:
            if styles:
                if paragraph.style.name in styles:
                    yield paragraph
            else:
                yield paragraph

    def iter_sections(self):
        """Iterate over sections in docx document."""
        for section in self._document.sections:
            yield section

    # Atribut font yang diabaikan saat perbandingan — tidak relevan untuk validasi format PKM.
    # cs_bold/cs_italic: artefak Word untuk Complex Script, selalu mengikuti bold/italic biasa.
    _IGNORE_FONT_ATTRS = frozenset({'italic', 'cs_italic', 'cs_bold'})

    def get_font_attributes(self, paragraph, unit='pt'):
        """Get font attributes for specified paragraph."""
        runs = []
        for run in paragraph.runs:
            size = (run.font.size or
                    self._find_paragraph_attribute(paragraph.style,
                                                   'font', 'size'))
            family = (run.font.name or
                      self._find_paragraph_attribute(paragraph.style,
                                                     'font', 'name'))
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
          2. Style chain (Normal → base style → dst)
          3. docDefaults (default seluruh dokumen, tersimpan di styles.xml)
        """
        _except_attributes = ('tab_stops',)

        fetched_attributes = {}
        for attr, member in type(paragraph.paragraph_format).__dict__.items():
            if isinstance(member, property) and attr not in _except_attributes:
                value = (
                    paragraph.paragraph_format.__getattribute__(attr) or
                    self._find_paragraph_attribute(
                        paragraph.style, 'paragraph_format', attr) or
                    self._doc_defaults.get(attr)   # ← baca docDefaults
                )
                fetched_attributes[attr] = self._convert_unit(value, unit)
        return fetched_attributes

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
