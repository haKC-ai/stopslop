"""File ingestion: text, markdown, HTML, PDF, DOCX."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup


def _read_txt(path: str) -> str:
    with open(path, "rb") as f:
        raw = f.read()
    try:
        from charset_normalizer import from_bytes

        best = from_bytes(raw).best()
        if best is not None:
            return str(best)
    except Exception:  # noqa: BLE001 - decoding fallback is intentional
        pass
    return raw.decode("utf-8", errors="replace")


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract_text_from_file(path: str, max_pages: int = 100) -> tuple[str, dict[str, Any]]:
    meta: dict[str, Any] = {"source": path}
    lower = path.lower()
    if lower.endswith((".md", ".txt", ".log", ".ioc", ".text")):
        return _read_txt(path), meta
    if lower.endswith((".html", ".htm")):
        return _html_to_text(_read_txt(path)), meta
    if lower.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(path)
        pages = min(len(reader.pages), max_pages)
        meta["pages"] = pages
        return "\n".join(reader.pages[i].extract_text() or "" for i in range(pages)), meta
    if lower.endswith(".docx"):
        from docx import Document

        d = Document(path)
        return "\n".join(p.text for p in d.paragraphs), meta

    import filetype

    kind = filetype.guess(path)
    mime = kind.mime if kind else ""
    if mime == "application/pdf":
        from pypdf import PdfReader

        reader = PdfReader(path)
        pages = min(len(reader.pages), max_pages)
        return "\n".join(reader.pages[i].extract_text() or "" for i in range(pages)), meta
    if mime and mime.startswith("text/"):
        return _read_txt(path), meta
    if not mime:
        return _read_txt(path), meta
    raise ValueError(f"unsupported mime type {mime!r} for {path}")
