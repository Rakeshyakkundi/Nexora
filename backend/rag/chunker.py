"""Heading-based chunker for the FCRM knowledge markdown files, with a
word-count ceiling and overlap so a single oversized section can never
become one giant, low-precision retrieval chunk.

Still no token-counting library - word count is a close-enough proxy for
token count at this corpus's scale, and keeps this dependency-light.
"""

import re
from dataclasses import dataclass

from backend.config import CHUNK_MAX_WORDS, CHUNK_OVERLAP_WORDS


@dataclass
class Chunk:
    text: str
    source: str
    section: str


def _sliding_windows(words: list[str], max_words: int, overlap_words: int) -> list[list[str]]:
    """Split a word list into overlapping windows of at most `max_words`.
    Returns a single window unchanged if it already fits - this is the path
    every current knowledge/*.md section takes (max ~116 words vs. the 180
    word ceiling), so existing behavior is unaffected.
    """
    if len(words) <= max_words:
        return [words]

    step = max(max_words - overlap_words, 1)
    windows = []
    start = 0
    while start < len(words):
        end = start + max_words
        windows.append(words[start:end])
        if end >= len(words):
            break
        start += step
    return windows


def chunk_markdown(
    text: str,
    source: str,
    max_words: int = CHUNK_MAX_WORDS,
    overlap_words: int = CHUNK_OVERLAP_WORDS,
) -> list[Chunk]:
    """Split a knowledge markdown doc into retrieval chunks.

    First splits on '##' section headings (semantic boundaries - unchanged
    from before). Any section whose body exceeds `max_words` is then split
    into overlapping word-count windows, with the section heading repeated
    at the top of every sub-chunk so each one stays self-describing for
    retrieval on its own.
    """
    body = re.sub(r"^#\s+.*\n", "", text, count=1).strip()
    parts = re.split(r"\n(?=##\s)", body)

    chunks: list[Chunk] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue

        heading_match = re.match(r"(##\s+(.*))\n?", part)
        if heading_match:
            heading_line, section = heading_match.group(1), heading_match.group(2).strip()
            body_text = part[heading_match.end():].strip()
        else:
            heading_line, section, body_text = None, source, part

        word_windows = _sliding_windows(body_text.split(), max_words, overlap_words) if body_text else []

        if not word_windows:
            # Heading with no body, or a non-heading fallback with no content
            # to window - keep the single chunk as-is (matches prior behavior).
            if heading_line or body_text:
                chunks.append(Chunk(text=heading_line or body_text, source=source, section=section))
            continue

        for words in word_windows:
            sub_body = " ".join(words)
            chunk_text = f"{heading_line}\n\n{sub_body}".strip() if heading_line else sub_body
            chunks.append(Chunk(text=chunk_text, source=source, section=section))

    return chunks
