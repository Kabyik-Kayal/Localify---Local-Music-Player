"""Centralised Qt stylesheet definitions."""
from __future__ import annotations

import textwrap

PRIMARY_BG = "#121212"
SECONDARY_BG = "#181818"
ACCENT = "#1DB954"
TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#B3B3B3"

MAIN_STYLESHEET = textwrap.dedent(
    f"""
    QWidget {{
        background-color: {PRIMARY_BG};
        color: {TEXT_SECONDARY};
        font-family: 'Segoe UI', 'Helvetica Neue', Arial;
        font-size: 10pt;
    }}
    QLabel#heading {{
        color: {TEXT_PRIMARY};
        font-size: 16pt;
        font-weight: 600;
    }}
    QLabel#subheading {{
        color: {TEXT_SECONDARY};
        font-size: 11pt;
    }}
    QPushButton {{
        background-color: transparent;
        color: {TEXT_PRIMARY};
        border: none;
        padding: 6px 12px;
    }}
    QPushButton:hover {{
        color: {ACCENT};
    }}
    QPushButton:pressed {{
        color: {TEXT_PRIMARY};
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 4px;
    }}
    QPushButton#accent {{
        background-color: {ACCENT};
        border-radius: 20px;
        color: {TEXT_PRIMARY};
        padding: 8px 20px;
    }}
    QPushButton#accent:disabled {{
        background-color: rgba(29, 185, 84, 0.3);
    }}
    QListWidget, QTreeView, QTableView {{
        background-color: {SECONDARY_BG};
        border: none;
        selection-background-color: rgba(255, 255, 255, 0.1);
        selection-color: {TEXT_PRIMARY};
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(255, 255, 255, 0.2);
        border-radius: 4px;
    }}
    QSlider::groove:horizontal {{
        border: none;
        height: 6px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: {ACCENT};
        width: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    QProgressBar {{
        background-color: rgba(255, 255, 255, 0.1);
        border: none;
        height: 6px;
        border-radius: 3px;
    }}
    QProgressBar::chunk {{
        background-color: {ACCENT};
        border-radius: 3px;
    }}
    QLineEdit {{
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 4px;
        color: {TEXT_PRIMARY};
        padding: 6px 10px;
    }}
    QMenu {{
        background-color: {SECONDARY_BG};
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}
    QMenu::item:selected {{
        background-color: rgba(255, 255, 255, 0.08);
    }}
    QToolTip {{
        background-color: {SECONDARY_BG};
        color: {TEXT_PRIMARY};
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}
    """
).strip()


__all__ = [
    "PRIMARY_BG",
    "SECONDARY_BG",
    "ACCENT",
    "TEXT_PRIMARY",
    "TEXT_SECONDARY",
    "MAIN_STYLESHEET",
]
