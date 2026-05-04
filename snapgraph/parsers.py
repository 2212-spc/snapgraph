from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from html import unescape
from pathlib import Path

from .models import ParsedSource


SUPPORTED_EXTENSIONS = {
    ".gif",
    ".htm",
    ".html",
    ".jpeg",
    ".jpg",
    ".markdown",
    ".md",
    ".pdf",
    ".png",
    ".txt",
    ".webp",
}

IMAGE_EXTENSIONS = {".gif", ".png", ".jpg", ".jpeg", ".webp"}


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

    if suffix == ".pdf":
        text = _text_from_pdf(source_path)
        return ParsedSource(
            path=source_path,
            source_type="pdf",
            title=source_path.stem,
            text=text,
            content_hash=content_hash,
        )

    if suffix in {".html", ".htm"}:
        raw_text = raw_bytes.decode("utf-8", errors="replace")
        text = _text_from_html(raw_text)
        return ParsedSource(
            path=source_path,
            source_type="webpage",
            title=_title_from_html(source_path.stem, raw_text, text),
            text=text,
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


def _text_from_html(raw_html: str) -> str:
    without_head = re.sub(r"<head[^>]*>.*?</head>", " ", raw_html, flags=re.I | re.S)
    without_scripts = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", without_head, flags=re.I | re.S)
    with_breaks = re.sub(r"</(p|div|li|h[1-6]|br|section|article)>", "\n", without_scripts, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", with_breaks)
    lines = [" ".join(unescape(line).split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _title_from_html(fallback: str, raw_html: str, text: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, flags=re.I | re.S)
    if match:
        title = " ".join(unescape(match.group(1)).split())
        if title:
            return title
    return _title_from_text(fallback, text)


def _text_from_pdf(source_path: Path) -> str:
    fallback = (
        f"PDF 文件：{source_path.name}。当前版本已保存 PDF 文件和用户写下的情境，"
        "但没有从这份 PDF 中提取到可用正文。\n\n"
        "如果这份 PDF 很重要，请在保存时补一句为什么值得记下。"
    )
    pdftotext = _pdftotext_executable()
    if not pdftotext:
        return fallback
    try:
        completed = subprocess.run(
            [pdftotext, "-layout", str(source_path), "-"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return fallback

    text = "\n".join(line.rstrip() for line in completed.stdout.splitlines()).strip()
    if completed.returncode != 0 or not text:
        return fallback
    return f"{text}\n\nPDF 文件：{source_path.name}"


def _pdftotext_executable() -> str | None:
    detected = shutil.which("pdftotext")
    if detected:
        return detected
    for candidate in ("/opt/homebrew/bin/pdftotext", "/usr/local/bin/pdftotext"):
        if Path(candidate).exists():
            return candidate
    return None


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
