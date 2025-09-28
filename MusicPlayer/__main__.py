"""Executable module for Localify."""
from __future__ import annotations

import logging
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from .core.audio_player import AudioPlayer
from .core.folder_manager import FolderManager
from .core.metadata_handler import MetadataHandler
from .core.settings import SettingsManager
from .ui.main_window import MainWindow

LOGGER = logging.getLogger(__name__)


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main() -> int:
    _configure_logging()
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(  # type: ignore[attr-defined]
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except AttributeError:
        pass
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    settings = SettingsManager()
    metadata_handler = MetadataHandler()
    folder_manager = FolderManager(settings, metadata_handler)
    player = AudioPlayer(settings)

    window = MainWindow(settings, folder_manager, player)
    window.show()

    exit_code = app.exec()
    player.stop()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
