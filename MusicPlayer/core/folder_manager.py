"""Folder scanning and playlist management."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from .metadata_handler import MetadataHandler, SUPPORTED_EXTENSIONS, TrackMetadata
from .settings import SettingsManager

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class TrackItem:
    """Represents a track on disk with extracted metadata."""

    path: Path
    metadata: TrackMetadata
    normalized_gain_db: float = 0.0

    def matches(self, query: str) -> bool:
        query_lower = query.lower()
        for value in (self.metadata.title, self.metadata.artist, self.metadata.album, str(self.path)):
            if query_lower in value.lower():
                return True
        return False


@dataclass(slots=True)
class FolderPlaylist:
    """A folder parsed into a playlist."""

    path: Path
    tracks: List[TrackItem] = field(default_factory=list)
    total_duration: float = 0.0
    subfolders: List[Path] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.path.name or str(self.path)

    @property
    def track_count(self) -> int:
        return len(self.tracks)


class FolderManager:
    """Service to manage folder discovery and playlist caching."""

    def __init__(self, settings: SettingsManager, metadata_handler: Optional[MetadataHandler] = None) -> None:
        self._settings = settings
        self._metadata_handler = metadata_handler or MetadataHandler()
        self._folder_cache: Dict[Path, FolderPlaylist] = {}

    def clear_cache(self) -> None:
        self._folder_cache.clear()

    def add_folder(self, folder: Path) -> FolderPlaylist:
        folder = folder.resolve()
        playlist = self._scan_folder(folder)
        self._settings.add_recent_folder(folder)
        self._settings.set_last_opened_folder(folder)
        return playlist

    def remove_folder(self, folder: Path) -> None:
        folder = folder.resolve()
        self._folder_cache.pop(folder, None)
        self._settings.remove_folder(folder)

    def pin_folder(self, folder: Path) -> None:
        self._settings.pin_folder(folder.resolve())

    def unpin_folder(self, folder: Path) -> None:
        self._settings.unpin_folder(folder.resolve())

    def get_folder(self, folder: Path, use_cache: bool = True) -> Optional[FolderPlaylist]:
        folder = folder.resolve()
        if use_cache and folder in self._folder_cache:
            return self._folder_cache[folder]
        if not folder.exists() or not folder.is_dir():
            LOGGER.warning("Folder %s does not exist", folder)
            return None
        playlist = self._scan_folder(folder)
        return playlist

    def get_cached_folders(self) -> Sequence[FolderPlaylist]:
        return tuple(self._folder_cache.values())

    def search_tracks(self, folder: Path, query: str) -> List[TrackItem]:
        playlist = self.get_folder(folder)
        if not playlist:
            return []
        if not query:
            return playlist.tracks
        return [track for track in playlist.tracks if track.matches(query)]

    def global_search(self, query: str) -> List[TrackItem]:
        results: List[TrackItem] = []
        for playlist in list(self._folder_cache.values()):
            results.extend(self.search_tracks(playlist.path, query))
        # If cache is empty we attempt last opened folder
        if not results:
            last_folder = self._settings.get_last_opened_folder()
            if last_folder:
                playlist = self.get_folder(last_folder)
                if playlist:
                    results.extend(self.search_tracks(last_folder, query))
        return results

    def discover_audio_folders(self, base_path: Path) -> List[Path]:
        folders: List[Path] = []
        for candidate in base_path.rglob("*"):
            if candidate.is_dir():
                try:
                    iterator = candidate.iterdir()
                except OSError:
                    continue
                if any(file.suffix.lower() in SUPPORTED_EXTENSIONS for file in iterator if file.is_file()):
                    folders.append(candidate)
        return folders

    def _scan_folder(self, folder: Path) -> FolderPlaylist:
        LOGGER.info("Scanning folder %s", folder)
        tracks: List[TrackItem] = []
        subfolders: List[Path] = []
        total_duration = 0.0

        try:
            entries = sorted(folder.iterdir())
        except OSError as exc:
            LOGGER.warning("Unable to access folder %s: %s", folder, exc)
            playlist = FolderPlaylist(path=folder)
            self._folder_cache[folder] = playlist
            return playlist

        for entry in entries:
            if entry.is_dir():
                subfolders.append(entry)
                continue
            if entry.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            try:
                metadata = self._metadata_handler.extract(entry)
                normalized_gain = metadata.replaygain_track_gain or 0.0
                track = TrackItem(path=entry, metadata=metadata, normalized_gain_db=normalized_gain)
                tracks.append(track)
                total_duration += metadata.duration_seconds
            except Exception as exc:  # pragma: no cover - defensive
                LOGGER.exception("Failed to read metadata for %s: %s", entry, exc)

        playlist = FolderPlaylist(path=folder, tracks=tracks, total_duration=total_duration, subfolders=subfolders)
        self._folder_cache[folder] = playlist
        return playlist


__all__ = ["FolderManager", "FolderPlaylist", "TrackItem"]
