"""Persistent settings management for the MusicPlayer application."""
from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

APP_FOLDER_NAME = "Localify"
SETTINGS_FILE_NAME = "settings.json"


@dataclass(slots=True)
class WindowGeometry:
    """Container describing the main window geometry."""

    width: int = 1280
    height: int = 800
    x: int = 100
    y: int = 100


@dataclass(slots=True)
class PlaybackState:
    """State persisted for playback behaviour."""

    volume: float = 0.8
    is_muted: bool = False
    shuffle_enabled: bool = False
    repeat_mode: str = "off"  # off, one, all
    crossfade_seconds: float = 3.0
    normalization_enabled: bool = True
    eq_preset: str = "Flat"


DEFAULT_SETTINGS: Dict[str, Any] = {
    "window": asdict(WindowGeometry()),
    "last_opened_folder": None,
    "pinned_folders": [],
    "recent_folders": [],
    "playback": asdict(PlaybackState()),
    "track_positions": {},
    "folder_positions": {},
}


class SettingsManager:
    """High-level helper around a JSON-backed settings store."""

    def __init__(self, settings_path: Optional[Path] = None) -> None:
        self._lock = threading.RLock()
        self._settings_path = settings_path or self._default_settings_path()
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Any] = {}
        self._load()

    @staticmethod
    def _default_settings_path() -> Path:
        appdata = Path.home()
        if "APPDATA" in os.environ:
            appdata = Path(os.environ["APPDATA"])
        elif "XDG_CONFIG_HOME" in os.environ:
            appdata = Path(os.environ["XDG_CONFIG_HOME"])
        else:
            appdata = Path.home() / ".config"
        return appdata / APP_FOLDER_NAME / SETTINGS_FILE_NAME

    def _load(self) -> None:
        with self._lock:
            if not self._settings_path.exists():
                self._data = json.loads(json.dumps(DEFAULT_SETTINGS))
                self._save_locked()
                return
            try:
                self._data = json.loads(self._settings_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                backup_path = self._settings_path.with_suffix(".bak")
                backup_path.write_text(self._settings_path.read_text(encoding="utf-8", errors="ignore"))
                self._data = json.loads(json.dumps(DEFAULT_SETTINGS))
            self._merge_defaults()

    def _merge_defaults(self) -> None:
        for key, value in DEFAULT_SETTINGS.items():
            self._data.setdefault(key, json.loads(json.dumps(value)))

    def save(self) -> None:
        with self._lock:
            self._save_locked()

    def _save_locked(self) -> None:
        temp_path = self._settings_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(self._data, indent=2, sort_keys=True), encoding="utf-8")
        temp_path.replace(self._settings_path)

    def get_window_geometry(self) -> WindowGeometry:
        window_data = self._data.get("window", {})
        defaults = asdict(WindowGeometry())
        return WindowGeometry(**{**defaults, **window_data})

    def set_window_geometry(self, geometry: WindowGeometry) -> None:
        with self._lock:
            self._data["window"] = asdict(geometry)
            self._save_locked()

    def get_playback_state(self) -> PlaybackState:
        playback_data = self._data.get("playback", {})
        defaults = asdict(PlaybackState())
        return PlaybackState(**{**defaults, **playback_data})

    def update_playback_state(self, **kwargs: Any) -> PlaybackState:
        with self._lock:
            playback = self.get_playback_state()
            for key, value in kwargs.items():
                if hasattr(playback, key):
                    setattr(playback, key, value)
            self._data["playback"] = asdict(playback)
            self._save_locked()
            return playback

    def set_last_opened_folder(self, folder: Optional[Path]) -> None:
        with self._lock:
            self._data["last_opened_folder"] = str(folder) if folder else None
            self._save_locked()

    def get_last_opened_folder(self) -> Optional[Path]:
        folder = self._data.get("last_opened_folder")
        return Path(folder) if folder else None

    def get_pinned_folders(self) -> List[Path]:
        return [Path(p) for p in self._data.get("pinned_folders", [])]

    def pin_folder(self, folder: Path) -> None:
        with self._lock:
            folders = self._data.setdefault("pinned_folders", [])
            folder_str = str(folder)
            if folder_str not in folders:
                folders.insert(0, folder_str)
                self._save_locked()

    def unpin_folder(self, folder: Path) -> None:
        with self._lock:
            folders = self._data.setdefault("pinned_folders", [])
            folder_str = str(folder)
            if folder_str in folders:
                folders.remove(folder_str)
                self._save_locked()

    def add_recent_folder(self, folder: Path, limit: int = 10) -> None:
        with self._lock:
            recents = self._data.setdefault("recent_folders", [])
            folder_str = str(folder)
            if folder_str in recents:
                recents.remove(folder_str)
            recents.insert(0, folder_str)
            del recents[limit:]
            self._save_locked()

    def get_recent_folders(self) -> List[Path]:
        return [Path(p) for p in self._data.get("recent_folders", [])]

    def remember_track_position(self, track: Path, position_seconds: float) -> None:
        with self._lock:
            positions = self._data.setdefault("track_positions", {})
            positions[str(track)] = position_seconds
            self._save_locked()

    def get_track_position(self, track: Path) -> float:
        position = self._data.get("track_positions", {}).get(str(track), 0.0)
        return float(position)

    def remember_folder_position(self, folder: Path, track: Path, position_seconds: float) -> None:
        with self._lock:
            folders = self._data.setdefault("folder_positions", {})
            folder_key = str(folder)
            folder_entry = folders.setdefault(folder_key, {})
            track_key = str(track)
            if track_key in folder_entry:
                folder_entry.pop(track_key)
            folder_entry[track_key] = position_seconds
            self._save_locked()

    def get_folder_last_track(self, folder: Path) -> Optional[Tuple[Path, float]]:
        folder_entry = self._data.get("folder_positions", {}).get(str(folder))
        if not folder_entry:
            return None
        track_str, position = next(reversed(folder_entry.items()))
        return Path(track_str), float(position)

    def clear_folder_history(self, folder: Path) -> None:
        with self._lock:
            if str(folder) in self._data.get("folder_positions", {}):
                self._data["folder_positions"].pop(str(folder))
                self._save_locked()

    def remove_folder(self, folder: Path) -> None:
        with self._lock:
            folder_str = str(folder)
            for key in ("pinned_folders", "recent_folders"):
                items = self._data.get(key, [])
                if folder_str in items:
                    items.remove(folder_str)
            self._data.get("folder_positions", {}).pop(folder_str, None)
            self._save_locked()


__all__ = ["SettingsManager", "WindowGeometry", "PlaybackState"]
