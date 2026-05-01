from __future__ import annotations

import hashlib
from pathlib import Path

from .models import ParsedSource


SUPPORTED_EXTENSIONS = {".md", ".markdown", ".txt", ".png", ".jpg", ".jpeg", ".webp"}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def parse_source(path: Path) -> ParsedSource:
    source_path = path.expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Source not found: {source_path}")

    suffix = source_path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported source type '{suffix}'. Supported: {supported}")

    raw_bytes = source_path.read_bytes()
    content_hash = hashlib.sha256(raw_bytes).hexdigest()

    if suffix in IMAGE_EXTENSIONS:
        return ParsedSource(
            path=source_path,
            source_type="screenshot",
            title=source_path.stem,
            text="",
            content_hash=content_hash,
        )

    text = raw_bytes.decode("utf-8")
    source_type = "markdown" if suffix in {".md", ".markdown"} else "text"
    return ParsedSource(
        path=source_path,
        source_type=source_type,
        title=_title_from_text(source_path.stem, text),
        text=text,
        content_hash=content_hash,
    )


def _title_from_text(fallback: str, text: str) -> str:
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned.startswith("#"):
            title = cleaned.lstrip("#").strip()
            if title:
                return title
        if cleaned:
            break
    return fallback
