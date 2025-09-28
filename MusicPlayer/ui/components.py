"""Reusable PyQt6 widgets used across the MusicPlayer UI."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QStyle,
    QWidget,
)

from PIL.ImageQt import ImageQt

PROGRESS_SLIDER_STYLE = """
QSlider::groove:horizontal {
    height: 8px;
    background: rgba(255, 255, 255, 0.06);
    border-radius: 4px;
}
QSlider::sub-page:horizontal {
    background: #1DB954;
    border-radius: 4px;
}
QSlider::add-page:horizontal {
    background: rgba(255, 255, 255, 0.03);
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    width: 12px;
    margin: -3px 0;
    border-radius: 6px;
}
QSlider::handle:horizontal:hover {
    background: #1ed760;
}
"""

VOLUME_SLIDER_STYLE = """
QSlider::groove:horizontal {
    height: 8px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 4px;
}
QSlider::sub-page:horizontal {
    background: #1DB954;
    border-radius: 4px;
}
QSlider::add-page:horizontal {
    background: rgba(255, 255, 255, 0.02);
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    width: 10px;
    margin: -2px 0;
    border-radius: 5px;
}
QSlider::handle:horizontal:hover {
    background: #1ed760;
}
"""

from ..core.folder_manager import TrackItem
from ..resources.styles import ACCENT
from ..utils.helpers import format_duration


class SidebarWidget(QWidget):
    """Spotify-inspired sidebar with pinned and recent sections."""

    folder_selected = pyqtSignal(Path)
    folder_pinned = pyqtSignal(Path)
    folder_unpinned = pyqtSignal(Path)
    folder_remove_requested = pyqtSignal(Path)
    search_requested = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._search = QLineEdit(self)
        self._search.setPlaceholderText("Search your library")
        self._search.returnPressed.connect(self._on_search)
        layout.addWidget(self._search)

        layout.addWidget(self._create_label("Pinned"))
        self._pinned = QListWidget(self)
        self._pinned.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._pinned.itemActivated.connect(lambda item: self.folder_selected.emit(Path(item.data(Qt.ItemDataRole.UserRole))))
        self._pinned.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._pinned.customContextMenuRequested.connect(self._on_pinned_menu)
        layout.addWidget(self._pinned, 2)

        layout.addWidget(self._create_label("Recents"))
        self._recents = QListWidget(self)
        self._recents.itemActivated.connect(lambda item: self.folder_selected.emit(Path(item.data(Qt.ItemDataRole.UserRole))))
        self._recents.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._recents.customContextMenuRequested.connect(self._on_recents_menu)
        layout.addWidget(self._recents, 3)

        layout.addStretch(1)

    def set_pinned_folders(self, folders: Iterable[Path]) -> None:
        self._populate_list(self._pinned, folders)

    def set_recent_folders(self, folders: Iterable[Path]) -> None:
        self._populate_list(self._recents, folders)

    def focus_search(self) -> None:
        self._search.setFocus()
        self._search.selectAll()

    def _populate_list(self, widget: QListWidget, folders: Iterable[Path]) -> None:
        widget.clear()
        for folder in folders:
            item = QListWidgetItem(folder.name or str(folder), widget)
            item.setData(Qt.ItemDataRole.UserRole, str(folder))
            widget.addItem(item)

    def _create_label(self, text: str) -> QLabel:
        label = QLabel(text, self)
        label.setObjectName("subheading")
        return label

    def _on_search(self) -> None:
        self.search_requested.emit(self._search.text())

    def _on_pinned_menu(self, pos) -> None:
        item = self._pinned.itemAt(pos)
        if not item:
            return
        folder = Path(item.data(Qt.ItemDataRole.UserRole))
        menu = QMenu(self)
        unpin_action = menu.addAction("Unpin")
        unpin_action.triggered.connect(lambda: self.folder_unpinned.emit(folder))
        remove_action = menu.addAction("Remove")
        remove_action.triggered.connect(lambda: self.folder_remove_requested.emit(folder))
        menu.exec(self._pinned.mapToGlobal(pos))

    def _on_recents_menu(self, pos) -> None:
        item = self._recents.itemAt(pos)
        if not item:
            return
        folder = Path(item.data(Qt.ItemDataRole.UserRole))
        menu = QMenu(self)
        pin_action = menu.addAction("Pin folder")
        pin_action.triggered.connect(lambda: self.folder_pinned.emit(folder))
        remove_action = menu.addAction("Remove")
        remove_action.triggered.connect(lambda: self.folder_remove_requested.emit(folder))
        menu.exec(self._recents.mapToGlobal(pos))


class TrackTable(QTableWidget):
    """Table displaying tracks within the selected folder."""

    track_activated = pyqtSignal(int)
    track_context_menu = pyqtSignal(int)

    headers = ["Title", "Artist", "Album", "Duration"]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(0, len(self.headers), parent)
        self.setHorizontalHeaderLabels(self.headers)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)
        self.cellDoubleClicked.connect(lambda row, _column: self.track_activated.emit(row))
        self.setColumnWidth(0, 280)
        self.setColumnWidth(1, 180)
        self.setColumnWidth(2, 220)
        self.horizontalHeader().setStretchLastSection(True)

    def populate(self, tracks: List[TrackItem]) -> None:
        self.setRowCount(len(tracks))
        for row, track in enumerate(tracks):
            self._set_item(row, 0, track.metadata.title)
            self._set_item(row, 1, track.metadata.artist)
            self._set_item(row, 2, track.metadata.album)
            self._set_item(row, 3, format_duration(track.metadata.duration_seconds))

    def _set_item(self, row: int, column: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setItem(row, column, item)

    def _on_context_menu(self, pos) -> None:
        index = self.indexAt(pos)
        if index and index.isValid():
            self.track_context_menu.emit(index.row())


class PlaybackControls(QWidget):
    """Playback controls bar mirroring Spotify's layout."""

    previous_clicked = pyqtSignal()
    play_pause_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    shuffle_toggled = pyqtSignal(bool)
    repeat_mode_changed = pyqtSignal(str)
    volume_changed = pyqtSignal(float)
    mute_toggled = pyqtSignal(bool)

    repeat_modes = ["off", "one", "all"]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(24)

        layout.addStretch(1)

        controls_row = QHBoxLayout()
        controls_row.setSpacing(12)

        self.shuffle_button = self._create_icon_button(
            tooltip="Shuffle",
            theme_icon="media-playlist-shuffle",
            fallback_text="🔀",
            checkable=True,
        )
        self.shuffle_button.clicked.connect(lambda checked: self.shuffle_toggled.emit(checked))
        controls_row.addWidget(self.shuffle_button)

        self.previous_button = self._create_icon_button(
            tooltip="Previous",
            standard_icon=QStyle.StandardPixmap.SP_MediaSkipBackward,
        )
        self.previous_button.clicked.connect(self.previous_clicked.emit)
        controls_row.addWidget(self.previous_button)

        self.play_button = self._create_play_button()
        self.play_button.clicked.connect(self.play_pause_clicked.emit)
        controls_row.addWidget(self.play_button)

        self.next_button = self._create_icon_button(
            tooltip="Next",
            standard_icon=QStyle.StandardPixmap.SP_MediaSkipForward,
        )
        self.next_button.clicked.connect(self.next_clicked.emit)
        controls_row.addWidget(self.next_button)

        self.repeat_button = self._create_icon_button(
            tooltip="Repeat",
            theme_icon="media-playlist-repeat",
            fallback_text="🔁",
            checkable=True,
        )
        self._current_repeat_mode_index = 0
        self.repeat_button.clicked.connect(self._cycle_repeat_mode)
        controls_row.addWidget(self.repeat_button)

        layout.addLayout(controls_row)
        layout.addStretch(1)

        volume_row = QHBoxLayout()
        volume_row.setSpacing(10)

        self._volume_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume)
        self._muted_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolumeMuted)
        self.mute_button = self._create_icon_button(
            tooltip="Mute",
            standard_icon=QStyle.StandardPixmap.SP_MediaVolume,
            checkable=True,
        )
        self.mute_button.clicked.connect(self._on_mute_clicked)
        volume_row.addWidget(self.mute_button)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(140)
        self.volume_slider.setStyleSheet(VOLUME_SLIDER_STYLE)
        self.volume_slider.valueChanged.connect(lambda value: self.volume_changed.emit(value / 100.0))
        volume_row.addWidget(self.volume_slider)

        layout.addLayout(volume_row)
        layout.setAlignment(volume_row, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.set_playing(False)
        self.set_muted(False)

    def _create_icon_button(
        self,
        *,
        tooltip: str,
        theme_icon: Optional[str] = None,
        standard_icon: Optional[QStyle.StandardPixmap] = None,
        fallback_text: str = "",
        checkable: bool = False,
    ) -> QToolButton:
        button = QToolButton(self)
        button.setCheckable(checkable)
        button.setAutoRaise(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setToolTip(tooltip)
        button.setIconSize(QSize(26, 26))

        icon = QIcon()
        if theme_icon:
            theme = QIcon.fromTheme(theme_icon)
            if not theme.isNull():
                icon = theme
        if icon.isNull() and standard_icon is not None:
            icon = self.style().standardIcon(standard_icon)

        button.setStyleSheet("QToolButton { background: transparent; border: none; }")

        if not icon.isNull():
            icon_variants = {
                "normal": self._tinted_icon(icon, QColor("#FFFFFF"), button.iconSize()),
                "active": self._tinted_icon(icon, QColor(ACCENT), button.iconSize()),
            }
            button.setProperty("_icon_variants", icon_variants)
            button.setIcon(icon_variants["normal"])
        else:
            button.setProperty("_icon_variants", None)
            button.setText(fallback_text or tooltip)
            self._apply_text_button_style(button, active=False)

        button.pressed.connect(lambda b=button: self._set_button_active(b, True))
        button.released.connect(lambda b=button: self._set_button_active(b, b.isCheckable() and b.isChecked()))
        if checkable:
            button.toggled.connect(lambda checked, b=button: self._set_button_active(b, checked))
        else:
            button.toggled.connect(lambda _checked, b=button: self._set_button_active(b, False))
        self._set_button_active(button, checkable and button.isChecked())

        return button

    def _create_play_button(self) -> QPushButton:
        button = QPushButton(self)
        button.setObjectName("accent")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedSize(56, 56)
        button.setFlat(False)
        self._play_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        self._pause_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause)
        button.setIcon(self._play_icon)
        button.setIconSize(QSize(32, 32))
        button.setToolTip("Play")
        return button

    def set_playing(self, playing: bool) -> None:
        if playing:
            self.play_button.setIcon(self._pause_icon)
            self.play_button.setToolTip("Pause")
        else:
            self.play_button.setIcon(self._play_icon)
            self.play_button.setToolTip("Play")

    def set_shuffle(self, enabled: bool) -> None:
        self.shuffle_button.setChecked(enabled)

    def set_repeat_mode(self, mode: str) -> None:
        if mode in self.repeat_modes:
            self._current_repeat_mode_index = self.repeat_modes.index(mode)
            self._update_repeat_button()
            self.repeat_button.setChecked(mode != "off")

    def set_muted(self, muted: bool) -> None:
        self.mute_button.blockSignals(True)
        self.mute_button.setChecked(muted)
        if not self._volume_icon.isNull() and not self._muted_icon.isNull():
            base_icon = self._muted_icon if muted else self._volume_icon
            icon_variants = {
                "normal": self._tinted_icon(base_icon, QColor("#FFFFFF"), self.mute_button.iconSize()),
                "active": self._tinted_icon(base_icon, QColor(ACCENT), self.mute_button.iconSize()),
            }
            self.mute_button.setProperty("_icon_variants", icon_variants)
        else:
            self.mute_button.setProperty("_icon_variants", None)
            self.mute_button.setText("🔇" if muted else "🔊")
            self._apply_text_button_style(self.mute_button, muted)
        self._set_button_active(self.mute_button, muted)
        self.mute_button.setToolTip("Unmute" if muted else "Mute")
        self.mute_button.blockSignals(False)

    def _cycle_repeat_mode(self) -> None:
        self._current_repeat_mode_index = (self._current_repeat_mode_index + 1) % len(self.repeat_modes)
        mode = self.repeat_modes[self._current_repeat_mode_index]
        self._update_repeat_button()
        self.repeat_mode_changed.emit(mode)

    def _update_repeat_button(self) -> None:
        mode = self.repeat_modes[self._current_repeat_mode_index]
        labels = {
            "off": ("🔁", "Repeat"),
            "one": ("🔂", "Repeat One"),
            "all": ("🔁", "Repeat All"),
        }
        icon_text, tooltip = labels[mode]
        if self.repeat_button.icon().isNull():
            self.repeat_button.setText(icon_text)
        self.repeat_button.setToolTip(tooltip)
        repeat_icon = QIcon.fromTheme("media-playlist-repeat-one" if mode == "one" else "media-playlist-repeat")
        if not repeat_icon.isNull():
            self.repeat_button.setIcon(repeat_icon)

    def _on_mute_clicked(self, checked: bool) -> None:
        self.set_muted(checked)
        self.mute_toggled.emit(checked)

    def _set_button_active(self, button: QToolButton, active: bool) -> None:
        icon_variants = button.property("_icon_variants")
        if icon_variants:
            button.setIcon(icon_variants["active" if active else "normal"])
        else:
            self._apply_text_button_style(button, active)

    @staticmethod
    def _apply_text_button_style(button: QToolButton, active: bool) -> None:
        color = ACCENT if active else "#FFFFFF"
        button.setStyleSheet(
            f"QToolButton {{ color: {color}; background: transparent; border: none; }}"
        )

    @staticmethod
    def _tinted_icon(icon: QIcon, color: QColor, size: QSize) -> QIcon:
        pixmap = icon.pixmap(size)
        if pixmap.isNull():
            return icon
        image = pixmap.toImage()
        painter = QPainter(image)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(image.rect(), color)
        painter.end()
        return QIcon(QPixmap.fromImage(image))


class ProgressWidget(QWidget):
    """Slider and labels representing track progress."""

    seek_requested = pyqtSignal(float)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setColumnStretch(1, 1)
        self._duration: float = 0.0

        self._elapsed = QLabel("0:00", self)
        self._elapsed.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._elapsed, 0, 0)

        self._slider = QSlider(Qt.Orientation.Horizontal, self)
        self._slider.setRange(0, 1000)
        self._slider.setStyleSheet(PROGRESS_SLIDER_STYLE)
        self._slider.sliderReleased.connect(self._on_slider_released)
        layout.addWidget(self._slider, 0, 1)

        self._remaining = QLabel("0:00", self)
        self._remaining.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._remaining, 0, 2)

    def update_position(self, position: float, duration: float) -> None:
        duration = max(duration, 0.1)
        self._duration = duration
        ratio = min(max(position / duration, 0.0), 1.0)
        self._slider.blockSignals(True)
        self._slider.setValue(int(ratio * self._slider.maximum()))
        self._slider.blockSignals(False)
        self._elapsed.setText(format_duration(position))
        self._remaining.setText(format_duration(max(duration - position, 0.0)))

    def _on_slider_released(self) -> None:
        ratio = self._slider.value() / self._slider.maximum()
        target = ratio * max(self._duration, 0.1)
        self.seek_requested.emit(target)


class NowPlayingWidget(QWidget):
    """Displays current track metadata and album art."""

    queue_track_activated = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self._artwork = QLabel(self)
        self._artwork.setFixedSize(220, 220)
        self._artwork.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border-radius: 10px;")
        self._artwork.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._artwork)

        self._title = QLabel("Not playing", self)
        self._title.setObjectName("heading")
        layout.addWidget(self._title)

        self._subtitle = QLabel("", self)
        self._subtitle.setObjectName("subheading")
        layout.addWidget(self._subtitle)

        layout.addStretch(1)

        self._queue_label = QLabel("Queue", self)
        self._queue_label.setObjectName("subheading")
        layout.addWidget(self._queue_label)

        self._queue_list = QListWidget(self)
        self._queue_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._queue_list.itemActivated.connect(self._on_queue_item_activated)
        layout.addWidget(self._queue_list, 1)
        self._queue_tracks: List[TrackItem] = []

    def update_now_playing(self, track: Optional[TrackItem]) -> None:
        if track is None:
            self._title.setText("Not playing")
            self._subtitle.setText("")
            self._artwork.setPixmap(QPixmap())
            self._queue_list.clearSelection()
            return
        self._title.setText(track.metadata.title)
        self._subtitle.setText(f"{track.metadata.artist} • {track.metadata.album}")
        if track.metadata.album_art_image:
            image = ImageQt(track.metadata.album_art_image)
            pixmap = QPixmap.fromImage(image)
            self._artwork.setPixmap(pixmap.scaled(self._artwork.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self._artwork.setPixmap(QPixmap())
        if self._queue_tracks:
            try:
                index = self._queue_tracks.index(track)
            except ValueError:
                index = -1
            if index >= 0:
                self._queue_list.setCurrentRow(index)

    def update_queue(self, tracks: Iterable[TrackItem]) -> None:
        self._queue_list.clear()
        self._queue_tracks = list(tracks)
        for track in self._queue_tracks:
            self._queue_list.addItem(f"{track.metadata.title} — {track.metadata.artist}")

    def _on_queue_item_activated(self, item: QListWidgetItem) -> None:
        row = self._queue_list.row(item)
        self.queue_track_activated.emit(row)
