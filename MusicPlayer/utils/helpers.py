"""Miscellaneous helper utilities for the MusicPlayer app."""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Iterable, List


def format_duration(seconds: float) -> str:
    """Format seconds into a human readable duration string."""
    try:
        seconds = max(0, int(seconds))
    except (TypeError, ValueError):
        seconds = 0
    return str(timedelta(seconds=seconds))


def humanize_path(path: Path, root: Path | None = None) -> str:
    """Return a friendly label for a path."""
    try:
        if root and root in path.parents:
            return str(path.relative_to(root))
    except ValueError:
        pass
    return path.name or str(path)


def chunk_iterable(items: Iterable, size: int) -> List[list]:
    """Chunk an iterable into lists of ``size`` elements."""
    chunk: list = []
    chunks: List[list] = []
    for item in items:
        chunk.append(item)
        if len(chunk) == size:
            chunks.append(chunk)
            chunk = []
    if chunk:
        chunks.append(chunk)
    return chunks
