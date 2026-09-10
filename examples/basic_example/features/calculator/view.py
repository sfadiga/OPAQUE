"""
Calculator View - Handles the UI for the calculator
"""
from typing import List, Optional, Callable, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton,
    QLineEdit, QGridLayout, QTextEdit, QLabel, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon

from opaque.view.view import BaseView
from opaque.view.theme import (
    TypeScale, interactive, on_interactive, readable_foreground,
)


class CalculatorView(BaseView):
    """View for the calculator feature."""

    # Signals for user interactions
    digit_clicked = Signal(str)
    operation_clicked = Signal(str)
    equals_clicked = Signal()
    clear_clicked = Signal()
    clear_entry_clicked = Signal()
    backspace_clicked = Signal()
    toggle_sign_clicked = Signal()
    clear_history_clicked = Signal()

    def setup_ui(self) -> None:
        """Setup the calculator UI."""
        layout = QVBoxLayout()

        # Display
        self.display = QLineEdit()
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.display.setText("0")

        # Make display larger
        font = QFont()
        font.setPointSize(20)
        self.display.setFont(font)
        self.display.setMinimumHeight(50)

        layout.addWidget(self.display)

        # Button grid
        button_layout = QGridLayout()

        # Define buttons
        buttons: list[tuple[str, int, int, Any]] = [
            ('C', 0, 0, self.clear_clicked),
            ('CE', 0, 1, self.clear_entry_clicked),
            ('←', 0, 2, self.backspace_clicked),
            ('/', 0, 3, lambda: self.operation_clicked.emit('/')),

            ('7', 1, 0, lambda: self.digit_clicked.emit('7')),
            ('8', 1, 1, lambda: self.digit_clicked.emit('8')),
            ('9', 1, 2, lambda: self.digit_clicked.emit('9')),
            ('*', 1, 3, lambda: self.operation_clicked.emit('*')),

            ('4', 2, 0, lambda: self.digit_clicked.emit('4')),
            ('5', 2, 1, lambda: self.digit_clicked.emit('5')),
            ('6', 2, 2, lambda: self.digit_clicked.emit('6')),
            ('-', 2, 3, lambda: self.operation_clicked.emit('-')),

            ('1', 3, 0, lambda: self.digit_clicked.emit('1')),
            ('2', 3, 1, lambda: self.digit_clicked.emit('2')),
            ('3', 3, 2, lambda: self.digit_clicked.emit('3')),
            ('+', 3, 3, lambda: self.operation_clicked.emit('+')),

            ('±', 4, 0, self.toggle_sign_clicked),
            ('0', 4, 1, lambda: self.digit_clicked.emit('0')),
            ('.', 4, 2, lambda: self.digit_clicked.emit('.')),
            ('=', 4, 3, self.equals_clicked),
        ]

        # Create buttons
        self._operator_buttons: List[QPushButton] = []
        self._theme_color: Optional[str] = None
        for text, row, col, callback in buttons:
            button = QPushButton(text)
            button.setMinimumSize(60, 60)
            button.clicked.connect(callback)

            if text in ['+', '-', '*', '/', '=']:
                self._operator_buttons.append(button)
            button.setFont(TypeScale.body())

            button_layout.addWidget(button, row, col)

        layout.addLayout(button_layout)

        # History section
        history_group = QGroupBox("History")
        history_layout = QVBoxLayout()

        self.history_display = QTextEdit()
        self.history_display.setReadOnly(True)
        self.history_display.setMaximumHeight(100)
        history_layout.addWidget(self.history_display)

        clear_history_btn = QPushButton("Clear History")
        clear_history_btn.clicked.connect(self.clear_history_clicked)
        history_layout.addWidget(clear_history_btn)

        history_group.setLayout(history_layout)
        layout.addWidget(history_group)

        # Status bar
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(layout)
        self.setWidget(container)

        self.apply_theme()

    def apply_theme(self) -> None:
        """Rebuild the operator style from the current theme.

        A token value baked into a stylesheet goes stale after a theme
        change, so the shell calls this method after every change. The
        user-picked colour wins over the theme token, and the text colour
        must then stay readable on whatever the user picked.
        """
        background = self._theme_color or interactive()
        if self._theme_color is None:
            text_color = on_interactive()
        else:
            text_color = readable_foreground(self._theme_color)
        style = (
            f"QPushButton {{"
            f" background-color: {background};"
            f" color: {text_color};"
            f" font-weight: bold;"
            f" }}")
        for button in self._operator_buttons:
            button.setStyleSheet(style)

    def update_display(self, value: str):
        """Update the calculator display."""
        self.display.setText(value)

    def update_history(self, history: List[str]):
        """Update the history display."""
        # Check if history_display exists and is valid
        if hasattr(self, 'history_display') and self.history_display:
            try:
                self.history_display.clear()
                for entry in history[-10:]:  # Show last 10 entries
                    self.history_display.append(entry)
            except RuntimeError:
                # Widget was deleted, skip update
                pass

    def set_status(self, message: str):
        """Set status message."""
        self.status_label.setText(message)

    def set_theme_color(self, color: str):
        """Store the user-picked colour and repaint with it."""
        self._theme_color = color
        self.apply_theme()
