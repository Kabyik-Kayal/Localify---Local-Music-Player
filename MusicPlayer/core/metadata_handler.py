"""Audio metadata extraction helpers."""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from mutagen import File
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from PIL import Image

LOGGER = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".oga", ".m4a"}


@dataclass(slots=True)
class TrackMetadata:
    """Container describing rich metadata for a track."""

    title: str
    artist: str
    album: str
    duration_seconds: float
    track_number: Optional[int] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    album_art_image: Optional[Image.Image] = None
    replaygain_track_gain: Optional[float] = None


class MetadataHandler:
    """Service used to extract metadata for supported audio formats."""

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in SUPPORTED_EXTENSIONS

    def extract(self, file_path: Path) -> TrackMetadata:
        if not self.supports(file_path):
            raise ValueError(f"Unsupported audio format: {file_path.suffix}")

        audio = File(file_path, easy=False)
        if audio is None:
            raise ValueError(f"Unable to read audio metadata for {file_path}")

        title = self._first_valid(
            [
                self._extract_tag(audio, ("TIT2", "title")),
                file_path.stem,
            ]
        )
        artist = self._first_valid(
            [
                self._extract_tag(audio, ("TPE1", "artist")),
                "Unknown Artist",
            ]
        )
        album = self._first_valid(
            [
                self._extract_tag(audio, ("TALB", "album")),
                "Unknown Album",
            ]
        )
        duration = float(getattr(audio.info, "length", 0.0))
        track_number = self._parse_int(self._extract_tag(audio, ("TRCK", "tracknumber")))
        year = self._parse_int(self._extract_tag(audio, ("TDRC", "date", "year")))
        genre = self._extract_tag(audio, ("TCON", "genre"))
        album_art = self._extract_album_art(audio)
        replaygain = self._extract_replaygain(audio)

        return TrackMetadata(
            title=title,
            artist=artist,
            album=album,
            duration_seconds=duration,
            track_number=track_number,
            year=year,
            genre=genre,
            album_art_image=album_art,
            replaygain_track_gain=replaygain,
        )

    def _extract_tag(self, audio: File, keys: tuple[str, ...]) -> Optional[str]:
        for key in keys:
            if hasattr(audio, "tags") and audio.tags is not None:
                value = audio.tags.get(key)
                if value:
                    if isinstance(value, list):
                        value = value[0]
                    if hasattr(value, "text"):
                        text = getattr(value, "text")
                        if isinstance(text, list):
                            return str(text[0])
                        return str(text)
                    return str(value)
            if hasattr(audio, key):
                attr = getattr(audio, key)
                if attr:
                    if isinstance(attr, list):
                        return str(attr[0])
                    return str(attr)
        return None

    def _extract_album_art(self, audio: File) -> Optional[Image.Image]:
        try:
            if isinstance(audio, MP3) and getattr(audio, "tags", None):
                for tag in audio.tags.values():
                    description = getattr(tag, "desc", "")
                    if tag.FrameID == "APIC" and ("cover" in description.lower() or True):
                        return Image.open(io.BytesIO(tag.data)).convert("RGBA")
            if isinstance(audio, FLAC):
                if audio.pictures:
                    return Image.open(io.BytesIO(audio.pictures[0].data)).convert("RGBA")
            if isinstance(audio, MP4) and getattr(audio, "tags", None):
                covers = audio.tags.get("covr")
                if covers:
                    return Image.open(io.BytesIO(covers[0])).convert("RGBA")
            if isinstance(audio, OggVorbis) and getattr(audio, "tags", None):
                pictures = audio.tags.get("metadata_block_picture")
                if pictures:
                    import base64

                    data = base64.b64decode(pictures[0])
                    return Image.open(io.BytesIO(data)).convert("RGBA")
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.warning("Failed to extract album art: %s", exc)
        return None

    def _extract_replaygain(self, audio: File) -> Optional[float]:
        for key in ("replaygain_track_gain", "REPLAYGAIN_TRACK_GAIN"):
            if hasattr(audio, key):
                value = getattr(audio, key)
                if isinstance(value, (list, tuple)):
                    value = value[0]
                try:
                    return float(str(value).split(" ")[0])
                except ValueError:
                    continue
            if hasattr(audio, "tags") and audio.tags:
                tag_value = audio.tags.get(key)
                if tag_value:
                    if isinstance(tag_value, (list, tuple)):
                        tag_value = tag_value[0]
                    try:
                        return float(str(tag_value).split(" ")[0])
                    except ValueError:
                        continue
        return None

    @staticmethod
    def _parse_int(value: Optional[str]) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(str(value).split("/")[0])
        except ValueError:
            return None

    @staticmethod
    def _first_valid(candidates: list[Optional[str]]) -> str:
        for candidate in candidates:
            if candidate:
                if hasattr(candidate, "text"):
                    text = getattr(candidate, "text")
                    if isinstance(text, list):
                        return str(text[0])
                    return str(text)
                return str(candidate)
        return ""


__all__ = ["MetadataHandler", "TrackMetadata", "SUPPORTED_EXTENSIONS"]
