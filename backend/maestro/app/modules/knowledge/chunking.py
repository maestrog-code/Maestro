"""
HybridChunker — independently testable text chunking for the knowledge engine.

Strategy:
    Markdown / plain-text with headings:
        1. Split on # / ## / ### headings
        2. If a section exceeds CHUNK_SIZE_TOKENS → further split by token window with overlap

    PDF / plain-text without headings:
        1. Split on paragraph boundaries (double newline)
        2. If a paragraph exceeds CHUNK_SIZE_TOKENS → split by sentence boundary
        3. Merge small pieces until window is filled, then slide with overlap

Each output Chunk carries enough metadata to populate knowledge_chunks fully.
"""
import hashlib
import re
from dataclasses import dataclass, field
from typing import List, Optional

try:
    import tiktoken
    _ENCODER = tiktoken.get_encoding("cl100k_base")
    def _count_tokens(text: str) -> int:
        return len(_ENCODER.encode(text))
except Exception:
    # Fallback: rough word-based approximation if tiktoken is unavailable
    def _count_tokens(text: str) -> int:  # type: ignore[misc]
        return max(1, len(text.split()) * 4 // 3)

try:
    from langdetect import detect as _detect_lang
    def _detect(text: str) -> str:
        try:
            return _detect_lang(text[:500]) or "en"
        except Exception:
            return "en"
except ImportError:
    def _detect(text: str) -> str:  # type: ignore[misc]
        return "en"

from app.core.ai_settings import ai_settings


@dataclass
class Chunk:
    """A single processable unit of a document, ready to be embedded."""
    content: str
    chunk_index: int
    token_count: int
    checksum: str
    language: str
    page_number: Optional[int] = None
    section: Optional[str] = None   # full heading path, e.g. "Sales > Pipeline"
    heading: Optional[str] = None   # immediate heading text


class HybridChunker:
    """
    Hybrid chunking strategy.

    - Markdown / RST → heading-aware splitting first, token fallback second.
    - PDF / plain text → paragraph → sentence → token window.

    All tuning values come from `ai_settings` so they can be changed via env vars.
    """

    def __init__(
        self,
        chunk_size: int = ai_settings.CHUNK_SIZE_TOKENS,
        overlap: int = ai_settings.CHUNK_OVERLAP_TOKENS,
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chunk(self, content: str, mime_type: Optional[str] = None) -> List[Chunk]:
        """
        Chunk the given content string based on its MIME type.

        Args:
            content:   Raw extracted text.
            mime_type: MIME type of the source file (e.g. "text/markdown", "application/pdf").
                       When None or unknown, plain-text strategy is used.

        Returns:
            Ordered list of Chunk objects (chunk_index 0-based).
        """
        if not content or not content.strip():
            return []

        is_markdown = mime_type in (
            "text/markdown", "text/x-markdown", "text/plain", None
        ) and self._looks_like_markdown(content)

        if is_markdown:
            raw_chunks = self._chunk_markdown(content)
        else:
            raw_chunks = self._chunk_plain(content)

        language = _detect(content)

        results: List[Chunk] = []
        for idx, (text, page_num, section, heading) in enumerate(raw_chunks):
            results.append(Chunk(
                content=text,
                chunk_index=idx,
                token_count=_count_tokens(text),
                checksum=self._sha256(text),
                language=language,
                page_number=page_num,
                section=section,
                heading=heading,
            ))
        return results

    # ------------------------------------------------------------------
    # Markdown strategy
    # ------------------------------------------------------------------

    def _looks_like_markdown(self, text: str) -> bool:
        """Heuristic: does this text contain Markdown headings?"""
        return bool(re.search(r"^#{1,6}\s+\S", text, re.MULTILINE))

    def _chunk_markdown(self, content: str) -> List[tuple]:
        """
        Split Markdown by headings, then apply token chunking if a section is too large.
        Returns list of (text, page_number, section_path, heading) tuples.
        """
        # Split into sections on heading lines
        heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
        sections = []
        last_end = 0
        heading_stack: List[str] = []
        current_heading = None

        for match in heading_pattern.finditer(content):
            # Capture text before this heading
            if match.start() > last_end:
                preceding = content[last_end:match.start()].strip()
                if preceding:
                    sections.append((preceding, None, " > ".join(heading_stack) or None, current_heading))

            level = len(match.group(1))
            heading_text = match.group(2).strip()

            # Update heading stack to reflect nesting
            heading_stack = heading_stack[:level - 1] + [heading_text]
            current_heading = heading_text
            last_end = match.end()

        # Remaining text after last heading
        remainder = content[last_end:].strip()
        if remainder:
            sections.append((remainder, None, " > ".join(heading_stack) or None, current_heading))

        # Now split any section that's too large
        result = []
        for text, page, section, heading in sections:
            if _count_tokens(text) <= self.chunk_size:
                result.append((text, page, section, heading))
            else:
                for sub in self._token_window(text, page, section, heading):
                    result.append(sub)

        return result

    # ------------------------------------------------------------------
    # Plain-text strategy
    # ------------------------------------------------------------------

    def _chunk_plain(self, content: str) -> List[tuple]:
        """
        Split plain text (PDF, DOCX body, TXT without headings):
        paragraph → sentence boundary → token window with overlap.
        """
        paragraphs = re.split(r"\n\s*\n", content)
        result = []
        buffer = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            candidate = (buffer + " " + para).strip() if buffer else para

            if _count_tokens(candidate) <= self.chunk_size:
                buffer = candidate
            else:
                # Flush buffer
                if buffer:
                    result.extend(self._token_window(buffer, None, None, None))
                # Start fresh with this paragraph
                if _count_tokens(para) <= self.chunk_size:
                    buffer = para
                else:
                    result.extend(self._token_window(para, None, None, None))
                    buffer = ""

        if buffer:
            result.extend(self._token_window(buffer, None, None, None))

        return result

    # ------------------------------------------------------------------
    # Token-window splitter (shared by both strategies)
    # ------------------------------------------------------------------

    def _token_window(
        self,
        text: str,
        page_number: Optional[int],
        section: Optional[str],
        heading: Optional[str],
    ) -> List[tuple]:
        """
        Split `text` into overlapping token windows of size `chunk_size`.
        Uses word-level splitting as a proxy for tokens.
        """
        words = text.split()
        if not words:
            return []

        # Approximate: assume avg ~1.33 tokens/word for English
        # Use a conservative word count: chunk_size / 1.5 ≈ safe word limit
        word_limit = max(1, int(self.chunk_size / 1.5))
        word_overlap = max(0, int(self.overlap / 1.5))

        chunks = []
        start = 0
        while start < len(words):
            end = min(start + word_limit, len(words))
            chunk_text = " ".join(words[start:end])
            chunks.append((chunk_text, page_number, section, heading))

            if end >= len(words):
                break
            start = end - word_overlap  # slide back by overlap

        return chunks

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
