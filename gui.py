"""Chanakya's File Organizer: GUI (PyQt6)"""

import sys
from html import escape
from pathlib import Path

from PyQt6.QtCore import Qt, QSettings, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QGraphicsDropShadowEffect, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizeGrip, QTextEdit, QVBoxLayout, QWidget,
)

import core

APP_NAME = "Chanakya's File Organizer"
BASE = Path(__file__).resolve().parent
ICON_PATH = str(BASE / "app.png")

LOG_COLORS = {
    "info": "#8E8E93", "rename": "#0A84FF", "moved": "#28A745",
    "skip": "#AF52DE", "error": "#FF3B30",
}
LOG_LABELS = {
    "info": "Info", "rename": "Renaming", "moved": "Moved",
    "skip": "Skipped", "error": "Error",
}

QSS = """
#card { background: #F5F5F7; border: 1px solid #D1D1D6; border-radius: 12px; }
#card[max="true"] { border: none; border-radius: 0px; }

#titlebar { background: #ECECEF; border-bottom: 1px solid #D8D8DC;
            border-top-left-radius: 12px; border-top-right-radius: 12px; }
#titlebar[max="true"] { border-radius: 0px; }
#title { color: #3C3C43; font-size: 13px; font-weight: 600; }

QLabel#field { color: #8E8E93; font-size: 11px; font-weight: 600; letter-spacing: 1px; }

QLineEdit { background: white; border: 1px solid #D1D1D6; border-radius: 7px;
            padding: 7px 10px; font-size: 13px; color: #1C1C1E;
            selection-background-color: #0A84FF; }
QLineEdit:focus { border: 1px solid #0A84FF; }

QPushButton#secondary { background: white; border: 1px solid #D1D1D6;
            border-radius: 7px; padding: 7px 14px; font-size: 13px; color: #1C1C1E; }
QPushButton#secondary:hover { background: #F0F0F3; }
QPushButton#secondary:pressed { background: #E5E5EA; }

QPushButton#primary { background: #0A84FF; border: none; border-radius: 8px;
            padding: 9px 22px; font-size: 13px; font-weight: 600; color: white; }
QPushButton#primary:hover { background: #2B95FF; }
QPushButton#primary:pressed { background: #0070E0; }
QPushButton#primary:disabled { background: #A7CFFF; }

QTextEdit { background: white; border: 1px solid #D1D1D6; border-radius: 9px;
            padding: 8px; font-family: "JetBrains Mono","DejaVu Sans Mono",monospace;
            font-size: 12px; color: #1C1C1E; }
#status { color: #8E8E93; font-size: 12px; }
"""


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


# ───────────────────────── Title bar ─────────────────────────
class CtrlButton(QPushButton):

    def __init__(self, text, hover_bg, hover_fg="#1C1C1E"):
        super().__init__(text)
        self.hover_bg, self.hover_fg = hover_bg, hover_fg
        self.setFixedSize(44, 44)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.set_corner(0)

    def set_corner(self, radius_top_right: int):
        self.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;color:#3C3C43;"
            f"font-size:15px;border-top-right-radius:{radius_top_right}px;}}"
            f"QPushButton:hover{{background:{self.hover_bg};color:{self.hover_fg};}}"
        )


class TitleBar(QFrame):
    SIDE = 132

    def __init__(self, window):
        super().__init__()
        self.win = window
        self.setObjectName("titlebar")
        self.setFixedHeight(44)

        # left: app icon
        icon = QLabel()
        icon.setPixmap(
            QPixmap(ICON_PATH).scaled(
                24, 24, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        left = QWidget()
        left.setFixedWidth(self.SIDE)
        ll = QHBoxLayout(left)
        ll.setContentsMargins(14, 0, 0, 0)
        ll.addWidget(icon, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # centre: title
        title = QLabel(APP_NAME)
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # right: minimize, maximize, close
        mini = CtrlButton("–", "#E2E2E7")
        self.zoom = CtrlButton("□", "#E2E2E7")
        self.close_btn = CtrlButton("✕", "#FF3B30", "white")
        self.close_btn.set_corner(12)
        mini.clicked.connect(window.showMinimized)
        self.zoom.clicked.connect(self.toggle_zoom)
        self.close_btn.clicked.connect(window.close)

        right = QWidget()
        right.setFixedWidth(self.SIDE)
        rl = QHBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        for b in (mini, self.zoom, self.close_btn):
            rl.addWidget(b)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(left)
        lay.addWidget(title, 1)
        lay.addWidget(right)

    def toggle_zoom(self):
        if self.win.isMaximized():
            self.win.showNormal()
        else:
            self.win.showMaximized()

    def sync_state(self, maximized: bool):
        self.zoom.setText("❐" if maximized else "□")
        self.close_btn.set_corner(0 if maximized else 12)
        self.setProperty("max", maximized)
        repolish(self)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.win.windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, e):
        self.toggle_zoom()


# ───────────────────────── Worker thread ─────────────────────────
class Worker(QThread):
    line = pyqtSignal(str, str)
    done = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, src, dst):
        super().__init__()
        self.src, self.dst = src, dst

    def run(self):
        try:
            stats = core.organize(self.src, self.dst, lambda k, t: self.line.emit(k, t))
            self.done.emit(stats)
        except Exception as e:
            self.failed.emit(str(e))


# ───────────────────────── Main window ─────────────────────────
class Window(QWidget):
    MARGINS = (18, 14, 18, 22)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(780, 600)
        self.setMinimumSize(620, 480)

        self.worker = None
        self.settings = QSettings("c-file-organizer", "c-file-organizer")

        home = Path.home()
        self.src = QLineEdit(self.settings.value("src", str(home)))
        self.dst = QLineEdit(self.settings.value("dst", str(home)))

        self.card = QFrame()
        self.card.setObjectName("card")
        self.shadow = QGraphicsDropShadowEffect(blurRadius=32, xOffset=0, yOffset=8)
        self.shadow.setColor(QColor(0, 0, 0, 70))
        self.card.setGraphicsEffect(self.shadow)

        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(*self.MARGINS)
        self.outer.addWidget(self.card)

        root = QVBoxLayout(self.card)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.titlebar = TitleBar(self)
        root.addWidget(self.titlebar)

        body = QVBoxLayout()
        body.setContentsMargins(24, 20, 24, 16)
        body.setSpacing(14)
        body.addLayout(self.path_row("From", self.src))
        body.addLayout(self.path_row("To", self.dst))

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Activity will appear here…")
        body.addWidget(self.log, 1)

        foot = QHBoxLayout()
        foot.setSpacing(8)
        self.status = QLabel("Ready")
        self.status.setObjectName("status")

        clear = QPushButton("Clear log")
        clear.setObjectName("secondary")
        clear.clicked.connect(self.clear_log)

        self.go = QPushButton("Organize")
        self.go.setObjectName("primary")
        self.go.clicked.connect(self.start)

        for b in (clear, self.go):
            b.setCursor(Qt.CursorShape.PointingHandCursor)

        foot.addWidget(self.status, 1)
        foot.addWidget(clear)
        foot.addWidget(self.go)
        body.addLayout(foot)
        root.addLayout(body, 1)

        self.grip = QSizeGrip(self)
        self.grip.setFixedSize(16, 16)
        self.grip.raise_()

        self.setStyleSheet(QSS)

    # ---------- Window state ----------
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.grip.move(self.width() - self.grip.width() - 4,
                       self.height() - self.grip.height() - 4)

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() == e.Type.WindowStateChange:
            maxed = self.isMaximized()
            self.outer.setContentsMargins(*((0, 0, 0, 0) if maxed else self.MARGINS))
            self.shadow.setEnabled(not maxed)
            self.grip.setVisible(not maxed)
            self.card.setProperty("max", maxed)
            repolish(self.card)
            self.titlebar.sync_state(maxed)

    # ---------- UI helpers ----------
    def path_row(self, label, edit):
        box = QVBoxLayout()
        box.setSpacing(5)

        lab = QLabel(label.upper())
        lab.setObjectName("field")

        btn = QPushButton("Browse…")
        btn.setObjectName("secondary")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self.browse(edit))

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(edit, 1)
        row.addWidget(btn)

        box.addWidget(lab)
        box.addLayout(row)
        return box

    def browse(self, edit):
        start = edit.text() if Path(edit.text()).is_dir() else str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Choose Folder", start)
        if folder:
            edit.setText(folder)

    def add_log(self, kind, text):
        color = LOG_COLORS.get(kind, "#1C1C1E")
        label = (LOG_LABELS.get(kind, kind) + ":").ljust(10).replace(" ", "&nbsp;")
        self.log.append(
            f'<span style="white-space:pre"><b style="color:{color}">{label}</b> '
            f'<span style="color:#1C1C1E">{escape(text)}</span></span>'
        )

    def clear_log(self):
        self.log.clear()
        if self.go.isEnabled():
            self.status.setText("Ready")

    # ---------- Run ----------
    def start(self):
        src, dst = self.src.text().strip(), self.dst.text().strip()
        if not Path(src).is_dir():
            self.add_log("error", f"Source folder not found: {src}")
            return
        if not dst:
            self.add_log("error", "Choose a destination folder.")
            return

        self.settings.setValue("src", src)
        self.settings.setValue("dst", dst)
        self.go.setEnabled(False)
        self.status.setText("Organizing…")
        self.add_log("info", f"{src}  →  {dst}")

        self.worker = Worker(src, dst)
        self.worker.line.connect(self.add_log)
        self.worker.done.connect(self.finish)
        self.worker.failed.connect(self.fail)
        self.worker.start()

    def finish(self, s):
        self.status.setText(
            f"Done · {s.moved} moved · {s.skipped} skipped · {s.errors} errors · {s.total} total"
        )
        self.go.setEnabled(True)

    def fail(self, msg):
        self.add_log("error", msg)
        self.status.setText("Failed")
        self.go.setEnabled(True)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("c-file-organizer")
    app.setDesktopFileName("c-file-organizer")
    w = Window()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
