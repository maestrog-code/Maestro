"""
Document parsers — BaseParser abstraction for text extraction.

Each parser accepts raw file bytes and returns plain text.
The HybridChunker then splits that text into chunks.

Sprint 005 implementations:
    TextParser     — .txt, .md files
    PDFParser      — .pdf files via PyPDF2
    DOCXParser     — .docx files via python-docx
    FallbackParser — UTF-8 decode of any file

Adding support for a new format: implement BaseParser, register in PARSER_REGISTRY.
"""
import io
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, Type

logger = logging.getLogger(__name__)

PARSER_VERSION = "hybrid-v1"  # bump when chunking or parsing logic changes


class BaseParser(ABC):
    """Abstract base for all document text extractors."""

    @abstractmethod
    def extract(self, content: bytes, file_name: Optional[str] = None) -> str:
        """
        Extract plain text from raw file bytes.

        Args:
            content:   Raw file bytes.
            file_name: Optional original filename (used as hints for format detection).

        Returns:
            Plain text string. Empty string on failure (callers handle empty content).
        """
        pass

    @property
    @abstractmethod
    def supported_mime_types(self) -> list[str]:
        """List of MIME types this parser handles."""
        pass


class TextParser(BaseParser):
    """Handles plain text (.txt) and Markdown (.md) files."""

    @property
    def supported_mime_types(self) -> list[str]:
        return ["text/plain", "text/markdown", "text/x-markdown"]

    def extract(self, content: bytes, file_name: Optional[str] = None) -> str:
        return content.decode("utf-8", errors="replace")


class PDFParser(BaseParser):
    """Handles PDF files via PyPDF2."""

    @property
    def supported_mime_types(self) -> list[str]:
        return ["application/pdf"]

    def extract(self, content: bytes, file_name: Optional[str] = None) -> str:
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text.strip())
            return "\n\n".join(pages)
        except Exception as exc:
            logger.error("PDFParser.extract failed: %s", exc)
            return ""


class DOCXParser(BaseParser):
    """Handles .docx files via python-docx."""

    @property
    def supported_mime_types(self) -> list[str]:
        return [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ]

    def extract(self, content: bytes, file_name: Optional[str] = None) -> str:
        try:
            import docx
            document = docx.Document(io.BytesIO(content))
            return "\n\n".join(p.text for p in document.paragraphs if p.text.strip())
        except Exception as exc:
            logger.error("DOCXParser.extract failed: %s", exc)
            return ""


class FallbackParser(BaseParser):
    """Last-resort UTF-8 decode for unknown file types."""

    @property
    def supported_mime_types(self) -> list[str]:
        return []

    def extract(self, content: bytes, file_name: Optional[str] = None) -> str:
        try:
            return content.decode("utf-8", errors="replace")
        except Exception:
            return ""


# ---------------------------------------------------------------------------
# Parser registry — maps MIME types to parser instances
# ---------------------------------------------------------------------------

_text_parser    = TextParser()
_pdf_parser     = PDFParser()
_docx_parser    = DOCXParser()
_fallback       = FallbackParser()

PARSER_REGISTRY: Dict[str, BaseParser] = {}
for _parser in [_text_parser, _pdf_parser, _docx_parser]:
    for _mime in _parser.supported_mime_types:
        PARSER_REGISTRY[_mime] = _parser


def get_parser(mime_type: Optional[str], file_name: Optional[str] = None) -> BaseParser:
    """
    Return the appropriate parser for a MIME type.
    Falls back by file extension, then to FallbackParser.
    """
    if mime_type and mime_type in PARSER_REGISTRY:
        return PARSER_REGISTRY[mime_type]

    # Extension-based fallback
    if file_name:
        fn = file_name.lower()
        if fn.endswith((".txt", ".md", ".markdown")):
            return _text_parser
        if fn.endswith(".pdf"):
            return _pdf_parser
        if fn.endswith(".docx"):
            return _docx_parser

    return _fallback
