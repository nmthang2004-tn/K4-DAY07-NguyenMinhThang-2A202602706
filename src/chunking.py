from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        # Split at positions AFTER punctuation marks, keeping the punctuation
        # (?<=[.!?]) ensures we split after the punctuation, then \s+ consumes whitespace
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return []

        chunks: list[str] = []
        current: list[str] = []

        for sentence in sentences:
            current.append(sentence)
            if len(current) >= self.max_sentences_per_chunk:
                chunks.append(" ".join(current))
                current = []

        if current:
            chunks.append(" ".join(current))

        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        return self._split(text.strip(), self.separators)

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        if not current_text:
            return []

        # Base case: no more separators or text is short enough
        if not remaining_separators or len(current_text) <= self.chunk_size:
            return [current_text]

        separator = remaining_separators[0]
        rest = remaining_separators[1:]

        # If this separator doesn't exist in text, try next one
        if separator not in current_text:
            return self._split(current_text, rest)

        parts = current_text.split(separator)
        result: list[str] = []
        buffer: list[str] = []

        for part in parts:
            candidate = separator.join(buffer + [part]) if buffer else part

            if len(candidate) <= self.chunk_size:
                buffer.append(part)
            else:
                # Buffer is full or exceeds chunk_size
                if buffer:
                    result.append(separator.join(buffer))
                    buffer = [part]
                else:
                    # Single part still too big, recurse with smaller separator
                    sub_chunks = self._split(part, rest)
                    result.extend(sub_chunks[:-1] if len(sub_chunks) > 1 else [])
                    buffer = [sub_chunks[-1]] if sub_chunks else []

        if buffer:
            remaining = separator.join(buffer)
            if len(remaining) <= self.chunk_size:
                result.append(remaining)
            else:
                # Merge with last result if it exists and fits
                if result and len(result[-1]) + len(separator) + len(remaining) <= self.chunk_size:
                    result[-1] += separator + remaining
                else:
                    result.append(remaining)

        return result


class HeadingChunker:
    """Chunk Markdown by headings, preserving the heading in every chunk.

    Policy documents are already organized into semantic sections.  Sections
    larger than ``chunk_size`` are split recursively, then their heading is
    prepended to every child so it never loses its subject.
    """

    def __init__(self, chunk_size: int = 500, min_heading_level: int = 3) -> None:
        self.chunk_size = chunk_size
        self.min_heading_level = max(1, min_heading_level)
        self._heading_re = re.compile(r"^(#{1," + str(self.min_heading_level) + r"})\s+.+")

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        sections: list[list[str]] = []
        current: list[str] = []
        for line in text.splitlines(keepends=True):
            if self._heading_re.match(line.rstrip("\r\n")):
                if current:
                    sections.append(current)
                current = [line]
            else:
                current.append(line)
        if current:
            sections.append(current)

        chunks: list[str] = []
        for lines in sections:
            section = "".join(lines).strip()
            if len(section) <= self.chunk_size:
                chunks.append(section)
                continue
            heading = lines[0].strip() if self._heading_re.match(lines[0].rstrip("\r\n")) else ""
            body = "".join(lines[1:]).strip() if heading else section
            prefix = f"{heading}\n" if heading else ""
            child_size = max(1, self.chunk_size - len(prefix))
            for child in RecursiveChunker(chunk_size=child_size).chunk(body):
                chunks.append(f"{prefix}{child}".strip())
        return chunks


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    norm_a = math.sqrt(sum(x * x for x in vec_a))
    norm_b = math.sqrt(sum(x * x for x in vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return _dot(vec_a, vec_b) / (norm_a * norm_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        if not text:
            return {
                "fixed_size": {"count": 0, "avg_length": 0.0, "chunks": []},
                "by_sentences": {"count": 0, "avg_length": 0.0, "chunks": []},
                "recursive": {"count": 0, "avg_length": 0.0, "chunks": []},
            }

        fixed = FixedSizeChunker(chunk_size=chunk_size, overlap=0)
        sentence = SentenceChunker(max_sentences_per_chunk=3)
        recursive = RecursiveChunker(chunk_size=chunk_size)

        fixed_chunks = fixed.chunk(text)
        sentence_chunks = sentence.chunk(text)
        recursive_chunks = recursive.chunk(text)

        def stats(chunks: list[str]) -> dict:
            count = len(chunks)
            avg = sum(len(c) for c in chunks) / count if count > 0 else 0.0
            return {"count": count, "avg_length": avg, "chunks": chunks}

        return {
            "fixed_size": stats(fixed_chunks),
            "by_sentences": stats(sentence_chunks),
            "recursive": stats(recursive_chunks),
        }
