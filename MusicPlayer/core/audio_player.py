"""Audio playback management built on top of pygame.mixer."""
from __future__ import annotations

import logging
import math
import random
from collections import deque
from pathlib import Path
from typing import Deque, List, Optional

import pygame
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .audio_effects import EqualizerEngine
from .folder_manager import FolderPlaylist, TrackItem
from .settings import PlaybackState, SettingsManager

LOGGER = logging.getLogger(__name__)


class AudioPlayer(QObject):
    """High-level audio controller coordinating pygame playback."""

    position_changed = pyqtSignal(float, float)
    state_changed = pyqtSignal(str)
    track_changed = pyqtSignal(object)
    queue_updated = pyqtSignal(list)

    def __init__(self, settings: SettingsManager, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._playback_state = settings.get_playback_state()
        self._equalizer = EqualizerEngine()
        self._queue: List[TrackItem] = []
        self._history: Deque[TrackItem] = deque(maxlen=50)
        self._current_index: int = -1
        self._current_track: Optional[TrackItem] = None
        self._current_offset: float = 0.0
        self._active_audio_path: Optional[Path] = None
        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._poll)
        self._timer.start()
        self._crossfade_pending = False
        self._state = "stopped"
        self._init_mixer()
        self._apply_volume(self._playback_state.volume)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def load_playlist(self, playlist: FolderPlaylist, start_index: int = 0) -> None:
        if not playlist.tracks:
            return
        self._queue = list(playlist.tracks)
        self.queue_updated.emit(list(self._queue))
        self._current_index = max(min(start_index, len(self._queue) - 1), 0)
        track = self._queue[self._current_index]
        last_position = self._settings.get_track_position(track.path)
        self.play_track(track, start_position=last_position)

    def play_track(self, track: TrackItem, start_position: float = 0.0, *, force_restart: bool = False) -> None:
        self._ensure_mixer()
        if start_position <= 0.0 and not force_restart:
            saved_position = self._settings.get_track_position(track.path)
            if saved_position > 0.0:
                start_position = saved_position
        if track not in self._queue:
            self._queue.append(track)
            self.queue_updated.emit(list(self._queue))
            self._current_index = len(self._queue) - 1
        else:
            self._current_index = self._queue.index(track)
        try:
            playback_path = self._equalizer.prepare_track(track.path, self._playback_state.eq_preset)
            self._active_audio_path = playback_path
            if force_restart:
                self._settings.remember_track_position(track.path, 0.0)
            pygame.mixer.music.load(playback_path.as_posix())
            fade_in_ms = int(max(self._playback_state.crossfade_seconds - 0.5, 0) * 1000)
            pygame.mixer.music.play(loops=0, start=start_position, fade_ms=fade_in_ms)
            adjusted_volume = self._compute_normalized_volume(track)
            self._set_mixer_volume(adjusted_volume)
            self._current_track = track
            self._current_offset = start_position
            self._crossfade_pending = False
            try:
                self._history.remove(track)
            except ValueError:
                pass
            self._history.append(track)
            self.track_changed.emit(track)
            self._update_state("playing")
        except pygame.error as exc:
            LOGGER.exception("Failed to play %s: %s", track.path, exc)
            self._update_state("error")

    def toggle_play_pause(self) -> None:
        if not pygame.mixer.get_init():
            return
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self._update_state("paused")
        else:
            pygame.mixer.music.unpause()
            self._update_state("playing")

    def stop(self) -> None:
        if not pygame.mixer.get_init():
            return
        pygame.mixer.music.stop()
        self._current_track = None
        self._active_audio_path = None
        self._update_state("stopped")
        self.track_changed.emit(None)

    def next_track(self) -> None:
        if not self._queue:
            return
        if self._playback_state.shuffle_enabled:
            self._current_index = random.randint(0, len(self._queue) - 1)
        else:
            self._current_index += 1
            if self._current_index >= len(self._queue):
                if self._playback_state.repeat_mode == "all":
                    self._current_index = 0
                else:
                    self.stop()
                    return
        track = self._queue[self._current_index]
        self.play_track(track)

    def previous_track(self) -> None:
        if not self._queue:
            return
        if self._playback_state.shuffle_enabled and self._history:
            if self._history:
                self._history.pop()  # drop current
            if self._history:
                track = self._history.pop()
                self.play_track(track)
                return
        self._current_index -= 1
        if self._current_index < 0:
            if self._playback_state.repeat_mode == "all":
                self._current_index = len(self._queue) - 1
            else:
                self._current_index = 0
        track = self._queue[self._current_index]
        self.play_track(track)

    def seek(self, position_seconds: float) -> None:
        if not self._current_track:
            return
        position_seconds = max(0.0, min(position_seconds, self._current_track.metadata.duration_seconds))
        self.play_track(self._current_track, start_position=position_seconds)

    def set_volume(self, volume: float) -> None:
        volume = max(0.0, min(volume, 1.0))
        self._playback_state = self._settings.update_playback_state(volume=volume)
        self._apply_volume(volume)

    def toggle_mute(self) -> None:
        self.set_mute(not self._playback_state.is_muted)

    def set_mute(self, muted: bool) -> None:
        self._playback_state = self._settings.update_playback_state(is_muted=muted)
        self._apply_volume(self._playback_state.volume)

    def is_muted(self) -> bool:
        return self._playback_state.is_muted

    def set_shuffle(self, enabled: bool) -> None:
        self._playback_state = self._settings.update_playback_state(shuffle_enabled=enabled)

    def set_repeat_mode(self, mode: str) -> None:
        if mode not in {"off", "one", "all"}:
            raise ValueError("Repeat mode must be 'off', 'one' or 'all'")
        self._playback_state = self._settings.update_playback_state(repeat_mode=mode)

    def set_crossfade(self, seconds: float) -> None:
        seconds = max(0.0, min(seconds, 10.0))
        self._playback_state = self._settings.update_playback_state(crossfade_seconds=seconds)

    def set_normalization(self, enabled: bool) -> None:
        self._playback_state = self._settings.update_playback_state(normalization_enabled=enabled)
        if self._current_track:
            self._apply_volume(self._playback_state.volume)

    def set_eq_preset(self, preset: str) -> None:
        self._playback_state = self._settings.update_playback_state(eq_preset=preset)
        if self._current_track:
            pos_ms = pygame.mixer.music.get_pos()
            if pos_ms < 0:
                pos_ms = 0
            current_pos = self._current_offset + pos_ms / 1000.0
            self.play_track(self._current_track, start_position=current_pos)

    def enqueue_next(self, track: TrackItem) -> None:
        if track in self._queue:
            self._queue.remove(track)
        insert_index = self._current_index + 1 if self._current_index >= 0 else 0
        self._queue.insert(insert_index, track)
        if self._current_index == -1:
            self._current_index = 0
            self.play_track(track)
        else:
            self.queue_updated.emit(list(self._queue))

    def append_to_queue(self, track: TrackItem) -> None:
        if track in self._queue:
            self._queue.remove(track)
        self._queue.append(track)
        self.queue_updated.emit(list(self._queue))

    def current_queue(self) -> List[TrackItem]:
        return list(self._queue)

    def current_track(self) -> Optional[TrackItem]:
        return self._current_track

    def current_position(self) -> float:
        if not self._current_track or not pygame.mixer.get_init():
            return 0.0
        pos_ms = pygame.mixer.music.get_pos()
        if pos_ms < 0:
            pos_ms = 0
        return self._current_offset + pos_ms / 1000.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _update_state(self, state: str) -> None:
        self._state = state
        self.state_changed.emit(state)
        if self._current_track and state in {"playing", "paused"}:
            pos_ms = pygame.mixer.music.get_pos()
            if pos_ms < 0:
                pos_ms = 0
            self._settings.remember_track_position(
                self._current_track.path, self._current_offset + pos_ms / 1000.0
            )

    def _poll(self) -> None:
        if not pygame.mixer.get_init() or not self._current_track:
            return
        busy = pygame.mixer.music.get_busy()
        current_pos = self._current_offset + pygame.mixer.music.get_pos() / 1000.0
        if busy:
            duration = max(self._current_track.metadata.duration_seconds, current_pos)
            self.position_changed.emit(current_pos, duration)
            self._settings.remember_track_position(self._current_track.path, current_pos)
            if not self._crossfade_pending and self._playback_state.crossfade_seconds > 0:
                if duration - current_pos <= self._playback_state.crossfade_seconds:
                    self._crossfade_pending = True
                    self._handle_crossfade()
            return
        if self._state == "paused":
            self.position_changed.emit(current_pos, self._current_track.metadata.duration_seconds)
            return
        self.position_changed.emit(current_pos, self._current_track.metadata.duration_seconds)
        if self._playback_state.repeat_mode == "one":
            self.play_track(self._current_track, start_position=0.0, force_restart=True)
        else:
            self.next_track()

    def _handle_crossfade(self) -> None:
        if self._playback_state.repeat_mode == "one":
            return
        next_index = self._current_index + 1
        if self._playback_state.shuffle_enabled:
            next_index = random.randint(0, len(self._queue) - 1)
        elif next_index >= len(self._queue):
            if self._playback_state.repeat_mode == "all":
                next_index = 0
            else:
                return
        next_track = self._queue[next_index]
        fade_ms = int(self._playback_state.crossfade_seconds * 1000)
        pygame.mixer.music.fadeout(fade_ms)
        try:
            playback_path = self._equalizer.prepare_track(next_track.path, self._playback_state.eq_preset)
            self._active_audio_path = playback_path
            pygame.mixer.music.load(playback_path.as_posix())
            pygame.mixer.music.play(loops=0, fade_ms=fade_ms)
            self._current_offset = 0.0
            self._current_track = next_track
            self._current_index = next_index
            self._set_mixer_volume(self._compute_normalized_volume(next_track))
            try:
                self._history.remove(next_track)
            except ValueError:
                pass
            self._history.append(next_track)
            self.track_changed.emit(next_track)
            self._crossfade_pending = False
        except pygame.error as exc:
            LOGGER.exception("Crossfade load failed: %s", exc)
            self._crossfade_pending = False

    def _apply_volume(self, volume: float) -> None:
        if not pygame.mixer.get_init():
            return
        effective_volume = 0.0 if self._playback_state.is_muted else volume
        self._set_mixer_volume(effective_volume)

    def _set_mixer_volume(self, volume: float) -> None:
        volume = max(0.0, min(volume, 1.0))
        pygame.mixer.music.set_volume(volume)

    def _compute_normalized_volume(self, track: TrackItem) -> float:
        base_volume = 0.0 if self._playback_state.is_muted else self._playback_state.volume
        if not self._playback_state.normalization_enabled or track.normalized_gain_db == 0.0:
            return base_volume
        adjustment = math.pow(10.0, track.normalized_gain_db / 20.0)
        return max(0.0, min(base_volume * adjustment, 1.0))

    def _ensure_mixer(self) -> None:
        if not pygame.mixer.get_init():
            self._init_mixer()

    def _init_mixer(self) -> None:
        if pygame.mixer.get_init():
            return
        pygame.mixer.init(buffer=512)
        LOGGER.info("pygame.mixer initialised")


__all__ = ["AudioPlayer"]
