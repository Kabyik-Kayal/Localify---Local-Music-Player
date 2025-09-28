"""Main application window replicating Spotify-like layout."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor, QDragEnterEvent, QDropEvent, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSystemTrayIcon,
    QStyle,
    QWidget,
    QVBoxLayout,
)

from ..core.audio_player import AudioPlayer
from ..core.folder_manager import FolderManager, FolderPlaylist, TrackItem
from ..core.settings import SettingsManager, WindowGeometry
from ..resources.styles import MAIN_STYLESHEET
from ..utils.helpers import format_duration
from .components import NowPlayingWidget, PlaybackControls, ProgressWidget, SidebarWidget, TrackTable
from .dialogs import FolderSelectionDialog, PreferencesDialog

LOGGER = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Primary window orchestrating UI and core services."""

    def __init__(
        self,
        settings: SettingsManager,
        folder_manager: FolderManager,
        player: AudioPlayer,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._folder_manager = folder_manager
        self._player = player
        self._current_playlist: Optional[FolderPlaylist] = None
        self._display_tracks: List[TrackItem] = []
        self._tray_icon: Optional[QSystemTrayIcon] = None

        self._build_ui()
        self._connect_signals()
        self._apply_initial_state()
        self._restore_geometry()
        self._refresh_sidebar()
        self.setAcceptDrops(True)
        self._register_shortcuts()
        self._init_tray_icon()
        self._load_last_folder()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.setWindowTitle("Localify — Local Music")
        self.setMinimumSize(1200, 760)
        self.setStyleSheet(MAIN_STYLESHEET)

        central = QWidget(self)
        outer_layout = QVBoxLayout(central)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        content_row = QHBoxLayout()
        content_row.setContentsMargins(24, 24, 24, 24)
        content_row.setSpacing(24)

        self._sidebar = SidebarWidget(self)
        self._sidebar.setFixedWidth(280)
        content_row.addWidget(self._sidebar)

        center_container = QWidget(self)
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(16)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        self._folder_label = QLabel("Select a folder to start", self)
        self._folder_label.setObjectName("heading")
        self._folder_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        header_layout.addWidget(self._folder_label, 1)

        self._add_folder_button = QPushButton("Add Folder", self)
        self._add_folder_button.setObjectName("accent")
        header_layout.addWidget(self._add_folder_button)

        center_layout.addLayout(header_layout)

        self._track_table = TrackTable(self)
        center_layout.addWidget(self._track_table, 1)

        content_row.addWidget(center_container, 1)

        self._now_playing = NowPlayingWidget(self)
        self._now_playing.setFixedWidth(300)
        content_row.addWidget(self._now_playing)

        outer_layout.addLayout(content_row, 1)

        controls_container = QWidget(self)
        controls_layout = QVBoxLayout(controls_container)
        controls_layout.setContentsMargins(24, 0, 24, 24)
        controls_layout.setSpacing(12)

        self._progress = ProgressWidget(self)
        controls_layout.addWidget(self._progress)

        self._playback_controls = PlaybackControls(self)
        controls_layout.addWidget(self._playback_controls)

        outer_layout.addWidget(controls_container)

        self.setCentralWidget(central)

    def _connect_signals(self) -> None:
        self._sidebar.folder_selected.connect(self._load_folder)
        self._sidebar.folder_pinned.connect(self._pin_folder)
        self._sidebar.folder_unpinned.connect(self._unpin_folder)
        self._sidebar.folder_remove_requested.connect(self._remove_folder)
        self._sidebar.search_requested.connect(self._perform_search)
        self._add_folder_button.clicked.connect(self.add_folder_via_dialog)

        self._track_table.track_activated.connect(self._play_track_at_index)
        self._track_table.track_context_menu.connect(self._show_track_context_menu)

        self._progress.seek_requested.connect(self._player.seek)
        self._playback_controls.previous_clicked.connect(self._player.previous_track)
        self._playback_controls.play_pause_clicked.connect(self._handle_play_pause)
        self._playback_controls.next_clicked.connect(self._player.next_track)
        self._playback_controls.shuffle_toggled.connect(self._player.set_shuffle)
        self._playback_controls.repeat_mode_changed.connect(self._player.set_repeat_mode)
        self._playback_controls.volume_changed.connect(self._player.set_volume)
        self._playback_controls.mute_toggled.connect(self._player.set_mute)

        self._player.position_changed.connect(self._on_position_changed)
        self._player.track_changed.connect(self._on_track_changed)
        self._player.queue_updated.connect(self._now_playing.update_queue)
        self._player.state_changed.connect(self._on_state_changed)
        self._now_playing.queue_track_activated.connect(self._play_queue_track)

    def _register_shortcuts(self) -> None:
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, activated=self._player.toggle_play_pause)
        QShortcut(QKeySequence(Qt.Key.Key_MediaPlay), self, activated=self._player.toggle_play_pause)
        QShortcut(QKeySequence(Qt.Key.Key_MediaStop), self, activated=self._player.stop)
        QShortcut(QKeySequence(Qt.Key.Key_MediaNext), self, activated=self._player.next_track)
        QShortcut(QKeySequence(Qt.Key.Key_MediaPrevious), self, activated=self._player.previous_track)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, activated=lambda: self._nudge_seek(-5))
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, activated=lambda: self._nudge_seek(5))
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self.add_folder_via_dialog)
        QShortcut(QKeySequence("Ctrl+,"), self, activated=self.open_preferences)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._sidebar.focus_search)

    def _apply_initial_state(self) -> None:
        playback = self._settings.get_playback_state()
        self._playback_controls.set_shuffle(playback.shuffle_enabled)
        self._playback_controls.set_repeat_mode(playback.repeat_mode)
        self._playback_controls.volume_slider.setValue(int(playback.volume * 100))
        self._playback_controls.set_playing(False)
        self._playback_controls.set_muted(playback.is_muted)

    def _init_tray_icon(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            LOGGER.warning("System tray not available")
            return
        icon = QIcon.fromTheme("media-playback-start")
        if icon.isNull():
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        tray = QSystemTrayIcon(icon, self)
        tray.setToolTip("Localify")
        menu = QMenu(self)
        play_action = menu.addAction("Play/Pause")
        play_action.triggered.connect(self._player.toggle_play_pause)
        menu.addAction("Next").triggered.connect(self._player.next_track)
        menu.addAction("Previous").triggered.connect(self._player.previous_track)
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(QApplication.quit)
        tray.setContextMenu(menu)
        tray.activated.connect(self._on_tray_activated)
        tray.show()
        self._tray_icon = tray

    # ------------------------------------------------------------------
    # Folder and track handling
    # ------------------------------------------------------------------
    def _load_folder(self, folder: Path) -> None:
        playlist = self._folder_manager.get_folder(folder)
        if not playlist:
            QMessageBox.warning(self, "Folder not accessible", f"Unable to open {folder}")
            return
        self._current_playlist = playlist
        self._display_tracks = playlist.tracks
        self._track_table.populate(self._display_tracks)
        stats = f"{playlist.name} — {playlist.track_count} tracks • {format_duration(playlist.total_duration)}"
        self._folder_label.setText(stats)
        self._settings.add_recent_folder(folder)
        self._settings.set_last_opened_folder(folder)
        self._refresh_sidebar()
        last_track = self._settings.get_folder_last_track(folder)
        if last_track:
            track_path, _ = last_track
            for row, track_item in enumerate(self._display_tracks):
                if track_item.path == track_path:
                    self._track_table.selectRow(row)
                    break

    def _play_track_at_index(self, index: int) -> None:
        if not self._display_tracks or index >= len(self._display_tracks):
            return
        track = self._display_tracks[index]
        if self._current_playlist and track in self._current_playlist.tracks:
            playlist_index = self._current_playlist.tracks.index(track)
            self._player.load_playlist(self._current_playlist, start_index=playlist_index)
        else:
            self._player.play_track(track)

    def _perform_search(self, query: str) -> None:
        if not query:
            if self._current_playlist:
                self._display_tracks = self._current_playlist.tracks
                self._track_table.populate(self._display_tracks)
                self._folder_label.setText(
                    f"{self._current_playlist.name} — {self._current_playlist.track_count} tracks • {format_duration(self._current_playlist.total_duration)}"
                )
            return

        results: List[TrackItem] = []
        if self._current_playlist:
            results = self._folder_manager.search_tracks(self._current_playlist.path, query)
        if not results:
            results = self._folder_manager.global_search(query)
        self._display_tracks = results
        self._track_table.populate(results)
        if results:
            self._folder_label.setText(f"Search results for '{query}' ({len(results)} tracks)")
        else:
            self._folder_label.setText(f"No results for '{query}'")

    def _show_track_context_menu(self, index: int) -> None:
        if not self._display_tracks or index >= len(self._display_tracks):
            return
        track = self._display_tracks[index]
        menu = QMenu(self)
        menu.addAction("Play").triggered.connect(lambda: self._player.play_track(track))
        menu.addAction("Play Next").triggered.connect(lambda: self._player.enqueue_next(track))
        menu.addAction("Add to Queue").triggered.connect(lambda: self._player.append_to_queue(track))
        menu.addSeparator()
        menu.addAction("Open in Explorer").triggered.connect(lambda: os.startfile(track.path))
        menu.exec(QCursor.pos())

    # ------------------------------------------------------------------
    # Player signal handlers
    # ------------------------------------------------------------------
    def _on_position_changed(self, position: float, duration: float) -> None:
        self._progress.update_position(position, duration)

    def _on_track_changed(self, track: Optional[TrackItem]) -> None:
        self._now_playing.update_now_playing(track)
        if track and self._current_playlist and track in self._current_playlist.tracks:
            row = self._current_playlist.tracks.index(track)
            self._track_table.selectRow(row)
            self._settings.remember_folder_position(
                self._current_playlist.path,
                track.path,
                self._player.current_position(),
            )

    def _on_state_changed(self, state: str) -> None:
        self._playback_controls.set_playing(state == "playing")
        self._playback_controls.set_muted(self._player.is_muted())

    def _nudge_seek(self, delta: float) -> None:
        track = self._player.current_track()
        if not track:
            return
        current_pos = self._player.current_position()
        self._player.seek(max(current_pos + delta, 0.0))

    def _handle_play_pause(self) -> None:
        if self._player.current_track() is None:
            if self._current_playlist and self._current_playlist.tracks:
                row = self._track_table.currentRow()
                if row < 0 or row >= len(self._current_playlist.tracks):
                    row = 0
                self._player.load_playlist(self._current_playlist, start_index=row)
            return
        self._player.toggle_play_pause()

    def _play_queue_track(self, index: int) -> None:
        queue = self._player.current_queue()
        if 0 <= index < len(queue):
            track = queue[index]
            self._player.play_track(track)
            if self._current_playlist and track in self._current_playlist.tracks:
                row = self._current_playlist.tracks.index(track)
                self._track_table.selectRow(row)

    # ------------------------------------------------------------------
    # Sidebar helpers
    # ------------------------------------------------------------------
    def _refresh_sidebar(self) -> None:
        self._sidebar.set_pinned_folders(self._settings.get_pinned_folders())
        self._sidebar.set_recent_folders(self._settings.get_recent_folders())

    def _pin_folder(self, folder: Path) -> None:
        self._folder_manager.pin_folder(folder)
        self._refresh_sidebar()

    def _unpin_folder(self, folder: Path) -> None:
        self._folder_manager.unpin_folder(folder)
        self._refresh_sidebar()

    def _remove_folder(self, folder: Path) -> None:
        self._folder_manager.remove_folder(folder)
        self._refresh_sidebar()
        if self._current_playlist and self._current_playlist.path == folder:
            self._player.stop()
            self._current_playlist = None
            self._display_tracks = []
            self._track_table.setRowCount(0)
            self._folder_label.setText("Select a folder to start")

    def add_folder_via_dialog(self) -> None:
        folder = FolderSelectionDialog.get_folder(self)
        if folder:
            self._folder_manager.add_folder(folder)
            self._refresh_sidebar()
            self._load_folder(folder)

    # ------------------------------------------------------------------
    # Drag and drop support
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802 - Qt override
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802 - Qt override
        added = []
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.is_dir():
                self._folder_manager.add_folder(path)
                added.append(path)
        event.acceptProposedAction()
        if added:
            self._refresh_sidebar()
            self._load_folder(added[0])

    # ------------------------------------------------------------------
    # Tray handling
    # ------------------------------------------------------------------
    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.showNormal()
            self.activateWindow()

    # ------------------------------------------------------------------
    # Geometry persistence
    # ------------------------------------------------------------------
    def _restore_geometry(self) -> None:
        geometry = self._settings.get_window_geometry()
        self.resize(geometry.width, geometry.height)
        self.move(geometry.x, geometry.y)

    def _store_geometry(self) -> None:
        rect = self.geometry()
        geometry = WindowGeometry(width=rect.width(), height=rect.height(), x=rect.x(), y=rect.y())
        self._settings.set_window_geometry(geometry)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._store_geometry()
        if self._tray_icon and self._tray_icon.isVisible():
            event.ignore()
            self.hide()
            self._tray_icon.showMessage("Localify", "Still running in the tray")
        else:
            super().closeEvent(event)

    def _load_last_folder(self) -> None:
        last_folder = self._settings.get_last_opened_folder()
        if last_folder and last_folder.exists():
            self._load_folder(last_folder)

    # ------------------------------------------------------------------
    # Preferences dialog shortcut
    # ------------------------------------------------------------------
    def open_preferences(self) -> None:
        dialog = PreferencesDialog(self._settings.get_playback_state(), self)
        if dialog.exec():
            result = dialog.result_state()
            self._player.set_crossfade(result["crossfade_seconds"])
            self._player.set_normalization(result["normalization_enabled"])
            self._player.set_repeat_mode(result["repeat_mode"])
            self._player.set_shuffle(result["shuffle_enabled"])
            self._player.set_eq_preset(result["eq_preset"])
            self._apply_initial_state()


__all__ = ["MainWindow"]
