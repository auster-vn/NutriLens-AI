from dataclasses import dataclass
from hashlib import sha256

from app.rag.contracts import ChunkDraft, SourceDocument
from app.rag.text import tokenize


@dataclass(frozen=True)
class MarkdownBlock:
    heading_path: tuple[str, ...]
    text: str


def markdown_blocks(body: str) -> list[MarkdownBlock]:
    headings: list[str] = []
    paragraph: list[str] = []
    blocks: list[MarkdownBlock] = []

    def flush() -> None:
        text = " ".join(line.strip() for line in paragraph if line.strip()).strip()
        if text:
            blocks.append(MarkdownBlock(tuple(headings), text))
        paragraph.clear()

    for raw_line in body.splitlines():
        line = raw_line.strip()
        if line.startswith("#"):
            flush()
            level = len(line) - len(line.lstrip("#"))
            title = line[level:].strip()
            headings[:] = headings[: max(0, level - 1)]
            headings.append(title)
        elif not line:
            flush()
        else:
            paragraph.append(line)
    flush()
    return blocks


def chunk_document(document: SourceDocument, max_tokens: int = 140, overlap_tokens: int = 24) -> list[ChunkDraft]:
    if max_tokens < 16:
        raise ValueError("max_tokens must be at least 16")
    if overlap_tokens < 0 or overlap_tokens >= max_tokens:
        raise ValueError("overlap_tokens must be non-negative and smaller than max_tokens")

    chunks: list[ChunkDraft] = []
    previous_tail: list[str] = []
    for block in markdown_blocks(document.body):
        words = block.text.split()
        cursor = 0
        while cursor < len(words):
            prefix = previous_tail if cursor == 0 else words[max(0, cursor - overlap_tokens) : cursor]
            capacity = max_tokens - len(prefix)
            content_words = prefix + words[cursor : cursor + capacity]
            if not content_words:
                break
            content = " ".join(content_words).strip()
            chunks.append(
                ChunkDraft(
                    source_filename=document.filename,
                    source_title=document.title,
                    source_url=document.metadata.get("source_url"),
                    source_document_id=document.document_id,
                    chunk_index=len(chunks),
                    heading_path=block.heading_path,
                    content=content,
                    content_hash=sha256(content.encode()).hexdigest(),
                    token_count=len(tokenize(content)),
                    metadata=dict(document.metadata),
                )
            )
            cursor += capacity
            previous_tail = content_words[-overlap_tokens:] if overlap_tokens else []
        if len(words) <= max_tokens:
            previous_tail = words[-overlap_tokens:] if overlap_tokens else []
    return chunks
