"""Dialog helpers for MusicPlayer."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QSlider,
    QVBoxLayout,
)

from ..core.settings import PlaybackState


class FolderSelectionDialog(QFileDialog):
    """Convenience wrapper with sensible defaults for picking music folders."""

    @staticmethod
    def get_folder(parent=None, caption: str = "Select music folder") -> Optional[Path]:
        dialog = QFileDialog(parent, caption)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dialog.setDirectory(str(Path.home()))
        if dialog.exec():
            selected = dialog.selectedFiles()
            if selected:
                return Path(selected[0])
        return None


class PreferencesDialog(QDialog):
    """Preferences dialog for playback options."""

    def __init__(self, playback_state: PlaybackState, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Playback Preferences")
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self._crossfade_slider = QSlider(Qt.Orientation.Horizontal, self)
        self._crossfade_slider.setRange(0, 100)
        self._crossfade_slider.setValue(int(playback_state.crossfade_seconds * 10))
        form.addRow("Crossfade (seconds)", self._crossfade_slider)

        self._normalization_checkbox = QCheckBox("Enable volume normalization", self)
        self._normalization_checkbox.setChecked(playback_state.normalization_enabled)
        layout.addWidget(self._normalization_checkbox)

        self._repeat_combo = QComboBox(self)
        self._repeat_combo.addItems(["off", "one", "all"])
        self._repeat_combo.setCurrentText(playback_state.repeat_mode)
        form.addRow("Repeat mode", self._repeat_combo)

        self._shuffle_checkbox = QCheckBox("Enable shuffle", self)
        self._shuffle_checkbox.setChecked(playback_state.shuffle_enabled)
        layout.addWidget(self._shuffle_checkbox)

        self._eq_combo = QComboBox(self)
        self._eq_combo.addItems(["Flat", "Bass Boost", "Treble Boost", "Vocal", "Soft"])
        self._eq_combo.setCurrentText(playback_state.eq_preset)
        form.addRow("Equalizer preset", self._eq_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result_state(self) -> Dict[str, object]:
        return {
            "crossfade_seconds": self._crossfade_slider.value() / 10.0,
            "normalization_enabled": self._normalization_checkbox.isChecked(),
            "repeat_mode": self._repeat_combo.currentText(),
            "shuffle_enabled": self._shuffle_checkbox.isChecked(),
            "eq_preset": self._eq_combo.currentText(),
        }


__all__ = ["FolderSelectionDialog", "PreferencesDialog"]
