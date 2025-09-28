"""Audio processing helpers (equalizer, crossfade preparation, etc.)."""
from __future__ import annotations

import hashlib
import logging
import tempfile
from pathlib import Path

from pydub import AudioSegment

LOGGER = logging.getLogger(__name__)


class EqualizerEngine:
    """Applies simple equalizer presets using pydub filters."""

    def __init__(self) -> None:
        self._cache_dir = Path(tempfile.gettempdir()) / "musicplayer" / "eq-cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._preset_functions = {
            "Flat": self._apply_flat,
            "Bass Boost": self._apply_bass_boost,
            "Treble Boost": self._apply_treble_boost,
            "Vocal": self._apply_vocal,
            "Soft": self._apply_soft,
        }

    def prepare_track(self, source: Path, preset: str) -> Path:
        preset = preset if preset in self._preset_functions else "Flat"
        if preset == "Flat":
            return source
        cache_key = self._cache_key(source, preset)
        cached_file = self._cache_dir / cache_key
        if cached_file.exists() and cached_file.stat().st_mtime >= source.stat().st_mtime:
            return cached_file
        try:
            segment = AudioSegment.from_file(source)
            processed = self._preset_functions[preset](segment)
            processed.export(cached_file, format=source.suffix.replace(".", ""))
            return cached_file
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.exception("Equalizer processing failed, falling back to original: %s", exc)
            return source

    def clean_cache(self) -> None:
        for file in self._cache_dir.glob("*"):
            try:
                if file.is_file():
                    file.unlink()
            except OSError:
                continue

    def _cache_key(self, source: Path, preset: str) -> str:
        signature = f"{source.resolve()}::{source.stat().st_mtime}::{preset}".encode("utf-8")
        digest = hashlib.md5(signature, usedforsecurity=False).hexdigest()
        extension = source.suffix.lower().lstrip(".") or "mp3"
        return f"{digest}.{extension}"

    @staticmethod
    def _apply_flat(segment: AudioSegment) -> AudioSegment:
        return segment

    @staticmethod
    def _apply_bass_boost(segment: AudioSegment) -> AudioSegment:
        low = segment.low_pass_filter(120).apply_gain(6)
        return segment.overlay(low)

    @staticmethod
    def _apply_treble_boost(segment: AudioSegment) -> AudioSegment:
        high = segment.high_pass_filter(4000).apply_gain(4)
        return segment.overlay(high)

    @staticmethod
    def _apply_vocal(segment: AudioSegment) -> AudioSegment:
        mid = segment.band_pass_filter(1000, 1200).apply_gain(5)
        return segment.overlay(mid)

    @staticmethod
    def _apply_soft(segment: AudioSegment) -> AudioSegment:
        return segment - 3


__all__ = ["EqualizerEngine"]
