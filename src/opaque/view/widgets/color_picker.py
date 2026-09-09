# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.
"""
from PySide6.QtWidgets import QWidget, QPushButton, QColorDialog, QHBoxLayout, QLineEdit
from PySide6.QtGui import QColor
from PySide6.QtCore import Signal, Slot

from opaque.view.theme import (
    MINIMUM_HIT_TARGET,
    StatusRole,
    interactive,
    outline,
    readable_foreground,
    status_colors,
)


class ColorPicker(QWidget):
    """A widget for selecting a color."""
    colorChanged = Signal(str)

    BUTTON_SIZE = MINIMUM_HIT_TARGET

    def __init__(self, initial_color: str = "#ffffff", parent=None):
        super().__init__(parent)
        self._color = QColor(initial_color)
        self._text_is_valid = True

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.line_edit = QLineEdit(self._color.name())
        self.line_edit.setAccessibleName(self.tr("Colour value"))
        self.line_edit.textChanged.connect(self._on_text_changed)
        # The colour is taken when the user leaves the box, not on every key.
        self.line_edit.editingFinished.connect(self._commit_text)
        self.layout.addWidget(self.line_edit)

        self.button = QPushButton("...")
        self.button.setFixedSize(self.BUTTON_SIZE, self.BUTTON_SIZE)
        self.button.setAccessibleName(self.tr("Choose a colour"))
        self.button.setToolTip(self.tr("Open the colour dialog"))
        self.button.clicked.connect(self._on_button_clicked)
        self.layout.addWidget(self.button)

        self._update_button_color()
        self._update_validation_style()

    def color(self) -> str:
        return self._color.name()

    def setColor(self, color: str):
        new_color = QColor(color)
        if self._color != new_color:
            self._color = new_color
            self.line_edit.setText(self._color.name())
            self._update_button_color()
            self.colorChanged.emit(self._color.name())

    @Slot()
    def _on_button_clicked(self):
        dialog = QColorDialog(self._color, self)
        if dialog.exec():
            self.setColor(dialog.selectedColor().name())

    def is_text_valid(self) -> bool:
        """Return True when the text in the box names a colour Qt understands."""
        return self._text_is_valid

    @Slot(str)
    def _on_text_changed(self, text: str) -> None:
        """
        Say whether the typed text is a colour. Do not take it yet.

        The old code took the value on every key press, so typing a six digit
        hex value emitted six colours the user never asked for, and it said
        nothing at all when the text was not a colour.
        """
        self._text_is_valid = QColor(text).isValid()
        self._update_validation_style()

    def _update_validation_style(self) -> None:
        """Mark the box when the text is not a colour."""
        if self._text_is_valid:
            self.line_edit.setStyleSheet("")
            self.line_edit.setAccessibleDescription("")
            self.line_edit.setToolTip(
                self.tr("A colour name or a hex value, for example #3366cc"))
            return

        # The border colour is not the only cue. The tooltip and the
        # accessible description say the same thing in words.
        error = status_colors(StatusRole.ERROR)
        self.line_edit.setStyleSheet(
            f"QLineEdit {{ border: 1px solid {error.border}; }}")
        message = self.tr("This is not a colour. Use a name or a hex value.")
        self.line_edit.setAccessibleDescription(message)
        self.line_edit.setToolTip(message)

    def _commit_text(self) -> None:
        """Take the typed colour when the user leaves the box."""
        if not self._text_is_valid:
            # Put the last good colour back. The box must never keep a value
            # that the widget does not hold.
            self.line_edit.setText(self._color.name())
            self._text_is_valid = True
            self._update_validation_style()
            return
        self.setColor(self.line_edit.text())

    def _update_button_color(self) -> None:
        """
        Paint the swatch with a style sheet.

        The palette cannot be used here. Every theme this framework ships
        installs an application wide style sheet, and a style sheet beats the
        palette for every property it names, so a swatch set through the
        palette's Button role never appeared on the screen.
        """
        self.button_text_colour = readable_foreground(self._color.name())
        self.button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color.name()};
                color: {self.button_text_colour};
                border: 1px solid {outline()};
                border-radius: 3px;
            }}
            QPushButton:focus {{
                border: 2px solid {interactive()};
            }}
        """)
