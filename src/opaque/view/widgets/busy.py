# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

One busy state for the whole framework.

A user must know within 400 milliseconds that the interface received the
action. An operation longer than one second must show a progress indicator.
Every feature uses this one overlay, so busy always looks the same.
"""

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from opaque.view.theme import TypeScale, on_surface, surface_variant


class BusyOverlay(QWidget):
    """A panel that covers its parent while a long operation runs."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAccessibleName(self.tr("Busy"))
        self.setAutoFillBackground(True)
        self.setStyleSheet(
            f"BusyOverlay {{ background-color: {surface_variant()}; }}")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.message_label = QLabel("", self)
        self.message_label.setFont(TypeScale.body())
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet(f"color: {on_surface()};")
        layout.addWidget(self.message_label)

        # A busy bar, not a percentage. The framework cannot know how long an
        # arbitrary feature operation takes, and a false percentage is worse
        # than none.
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setMaximumWidth(240)
        self.progress.setAccessibleName(self.tr("Work in progress"))
        layout.addWidget(self.progress, alignment=Qt.AlignmentFlag.AlignCenter)

        self.hide()
        parent.installEventFilter(self)

    def start(self, message: str) -> None:
        """
        Cover the parent and say what is happening.

        Args:
            message: What the user is waiting for. Call tr() on the literal
                before you pass it here.
        """
        self.message_label.setText(message)
        self.setAccessibleDescription(message)
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())
        self.raise_()
        self.show()

    def stop(self) -> None:
        """Uncover the parent."""
        self.hide()
        self.setAccessibleDescription("")

    def eventFilter(self, watched, event) -> bool:
        """Keep covering the whole parent when it changes size.

        A plain Qt-parented child widget is not notified when its parent
        resizes - only the parent itself gets a resize event. Watching the
        parent directly is the only way to track its size live.
        """
        parent = self.parentWidget()
        if (watched is parent
                and parent is not None
                and event.type() == QEvent.Type.Resize
                and self.isVisible()):
            self.setGeometry(parent.rect())
        return super().eventFilter(watched, event)
