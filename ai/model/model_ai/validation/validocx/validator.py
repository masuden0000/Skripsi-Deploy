#
#    Copyright 2017 Vitalii Kulanov
#

__all__ = ['Validator', 'validate']

import jsonschema
import logging
import math
import re

from docx import Document

from .wrapper import DocumentWrapper
from .schema import RequirementsSchema

logger = logging.getLogger(__name__)


class Validator(object):
    """Class for validating docx document."""

    schema = RequirementsSchema()

    def __init__(self, document):
        """
        :param document: docx.Document
        """
        self._docx = DocumentWrapper(document)

    def validate_sections(self, section_requirements):
        """Validate sections of a document.

        Jika dokumen memiliki lebih banyak section daripada yang didefinisikan
        di requirements, requirements terakhir diterapkan ke semua section sisa.
        """
        fallback = section_requirements[-1]

        for i, section in enumerate(self._docx.iter_sections()):
            req = section_requirements[i] if i < len(section_requirements) else fallback
            unit = req['unit']
            fetched_attr = self._docx.get_section_attributes(section, unit=unit)

            for attr, v in req['attributes'].items():
                if not math.isclose(fetched_attr[attr], v, rel_tol=1e-02):
                    msg = ("'Section {0}': attribute '{1}' with value {2} "
                           "does not match required value "
                           "{3}".format(i, attr, fetched_attr[attr], v))
                    logger.error(msg)
                else:
                    pass

    def validate_styles(self, style_requirements):
        """Validate styles of a document, i.e. font and paragraph.

        Jika style paragraf tidak terdaftar di requirements, fallback ke
        requirements 'Normal' (jika tersedia). Ini memastikan semua paragraf
        isi — termasuk yang menggunakan custom style seperti 'DaftarParagraf'
        atau 'TabelGambar' — tetap divalidasi dengan aturan format dasar.
        Hanya jika 'Normal' pun tidak terdaftar, baru dicatat sebagai warning.
        """
        _FALLBACK_STYLE = "Normal"

        for para_idx, paragraph in enumerate(self._docx.iter_paragraphs()):
            style_name = paragraph.style.name

            if style_name in style_requirements:
                req = style_requirements[style_name]
            elif _FALLBACK_STYLE in style_requirements:
                logger.info(
                    "Style '{0}' [para#{1}] tidak terdaftar, "
                    "divalidasi sebagai '{2}'.".format(
                        style_name, para_idx, _FALLBACK_STYLE)
                )
                req = style_requirements[_FALLBACK_STYLE]
            else:
                logger.warning("Undefined style: '{0}' [para#{1}].".format(
                    style_name, para_idx))
                continue

            exclude_pattern = req.get('exclude', {}).get('text_regex')
            if exclude_pattern and re.match(exclude_pattern, paragraph.text):
                logger.info("SKIP para#{0} (excluded by text_regex): '{1}'".format(
                    para_idx, paragraph.text.strip()))
                continue

            self.validate_paragraph(paragraph, req['paragraph'], para_idx)
            self.validate_font(paragraph, req['font'], para_idx)

    def validate_font(self, paragraph, font_requirements, para_idx=None):
        """Validate font in a specified paragraph."""
        unit = font_requirements['unit']
        requirements = font_requirements['attributes']
        fetched_attr = self._docx.get_font_attributes(paragraph, unit=unit)
        loc = f"para#{para_idx}" if para_idx is not None else "para#?"

        for i, attr in enumerate(fetched_attr):
            req_set    = set(requirements)
            actual_set = set(attr)

            req_nums    = {x for x in req_set    if isinstance(x, (int, float))}
            actual_nums = {x for x in actual_set if isinstance(x, (int, float))}
            req_strs    = req_set    - req_nums
            actual_strs = actual_set - actual_nums

            size_ok = all(
                any(math.isclose(r, a, rel_tol=1e-02) for a in actual_nums)
                for r in req_nums
            )
            str_ok = req_strs.issubset(actual_strs)

            if size_ok and str_ok:
                logger.info("CHECK [{0}] font ({1}) PASS".format(
                    loc, paragraph.style.name))
            else:
                missing = []
                if not size_ok:
                    missing += [str(r) for r in req_nums
                                if not any(math.isclose(r, a, rel_tol=1e-02)
                                           for a in actual_nums)]
                if not str_ok:
                    missing += [str(s) for s in req_strs - actual_strs]

                logger.info("CHECK [{0}] font ({1}) FAIL missing={2}".format(
                    loc, paragraph.style.name, ','.join(missing)))
                msg = ("[{0}] Font attributes ({1}) mismatch required ({2}) — "
                       "missing: [{3}] in paragraph with style '{4}':"
                       "\n'{5}'".format(
                        loc,
                        ', '.join(str(a) for a in attr),
                        ', '.join(str(r) for r in requirements),
                        ', '.join(missing),
                        paragraph.style.name,
                        paragraph.runs[i].text))
                logger.error(msg)

    def validate_paragraph(self, paragraph, paragraph_requirements, para_idx=None):
        """Validate paragraph."""

        unit = paragraph_requirements['unit']
        fetched_attr = self._docx.get_paragraph_attributes(paragraph, unit=unit)
        loc = f"para#{para_idx}" if para_idx is not None else "para#?"

        for attr, value in paragraph_requirements['attributes'].items():
            if fetched_attr[attr] is not None:
                if not math.isclose(fetched_attr[attr], value, rel_tol=1e-02):
                    logger.info("CHECK [{0}] {1} ({2}) FAIL actual={3} expected={4}".format(
                        loc, attr, paragraph.style.name, fetched_attr[attr], value))
                    msg = ("[{0}] The attribute of paragraph '{1}' ({2}) with value "
                           "{3} does not match required value {4}: "
                           "\n'{5}'".format(loc, attr, paragraph.style.name,
                                            fetched_attr[attr], value,
                                            paragraph.text))
                    logger.error(msg)
                else:
                    logger.info("CHECK [{0}] {1} ({2}) PASS".format(
                        loc, attr, paragraph.style.name))
            else:
                logger.info("CHECK [{0}] {1} ({2}) INHERITED".format(
                    loc, attr, paragraph.style.name))
                logger.warning("[{0}] The attribute of paragraph '{1}' ({2}) is not "
                               "set explicitly (inherited from Word default). "
                               "Required value is {3}: "
                               "\n'{4}'".format(loc, attr, paragraph.style.name,
                                                value, paragraph.text))

    def validate(self, document_requirements):
        """Validate the whole document."""

        self._validate_schema(document_requirements,
                              self.schema.requirements_schema)
        logger.info("Start validating sections.")
        self.validate_sections(document_requirements['sections'])
        logger.info("Start validating styles.")
        self.validate_styles(document_requirements['styles'])
        logger.info("Validation process completed.")

    @staticmethod
    def _validate_schema(requirements, schema):
        """Validate requirements schema."""

        logger.info("Start validating requirements schema.")
        try:
            jsonschema.validate(requirements, schema)
        except jsonschema.exceptions.ValidationError as e:
            logger.exception(e)
            raise


def validate(docx, requirements, *, doc=None):
    """Validates docx document.

    :param docx: path to docx file (as a string) or a file-like object
    :param requirements: document requirements as a dict (see examples)
    :param doc: already-opened Document object — jika diberikan, docx tidak dibuka ulang dari disk
    """
    document = doc if doc is not None else Document(docx)
    validator = Validator(document)
    validator.validate(requirements)
