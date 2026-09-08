"""
Console widget for displaying captured stdout/stderr output.

@copyright 2025 Sandro Fadiga
Licensed under MIT License
"""

from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QToolBar, QLineEdit,
    QLabel, QCheckBox, QPushButton, QFileDialog, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QTextCursor, QColor, QTextCharFormat, QIcon, QAction

from opaque.view.view import BaseView
from opaque.models.console_model import ConsoleOutputItem
from opaque.view.theme import (
    StatusRole,
    TypeScale,
    interactive,
    on_interactive,
    on_surface,
    outline,
    status_colors,
    surface,
)


class ConsoleWidget(QWidget):
    """Widget for displaying console output with toolbar controls."""

    # Signals
    clear_requested = Signal()
    export_requested = Signal(str)  # file path

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        # The block number where each displayed item starts. The model returns
        # a match as an index into this list, and a QTextEdit can only find a
        # line by its block number, so this list joins the two.
        self._item_block_numbers: List[int] = []
        self.setup_ui()
        self._last_search_matches: List[int] = []
        self._current_search_index = 0

        # Auto-scroll timer to batch scroll operations
        self._scroll_timer = QTimer()
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.timeout.connect(self._do_auto_scroll)
        self._scroll_timer.setInterval(10)  # 10ms delay

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # Create toolbar
        self.toolbar = self._create_toolbar()
        layout.addWidget(self.toolbar)

        # Create main content area with splitter
        splitter = QSplitter(Qt.Orientation.Vertical)

        self.console_display = QTextEdit()
        self.console_display.setReadOnly(True)
        self.console_display.setLineWrapMode(
            QTextEdit.LineWrapMode.WidgetWidth)
        self.apply_theme()

        splitter.addWidget(self.console_display)

        # Search panel (initially hidden)
        self.search_panel = self._create_search_panel()
        self.search_panel.setVisible(False)
        splitter.addWidget(self.search_panel)

        # Set splitter proportions
        splitter.setSizes([400, 50])  # Console gets most space

        layout.addWidget(splitter)

        # Status bar
        self.status_bar = self._create_status_bar()
        layout.addWidget(self.status_bar)

    def apply_theme(self) -> None:
        """
        Take every console colour and the console font from the active theme.

        The console used to paint one editor palette into a style sheet, so it
        stayed dark inside a light theme and its text failed the contrast
        minimum. Call this method again after the theme changes.
        """
        self.background_colour = surface()
        self.stdout_colour = on_surface()
        self.stderr_colour = status_colors(StatusRole.ERROR).background

        self.console_display.setFont(TypeScale.mono())
        self.console_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.background_colour};
                color: {self.stdout_colour};
                border: 1px solid {outline()};
                selection-background-color: {interactive()};
                selection-color: {on_interactive()};
            }}
        """)

    def _create_toolbar(self) -> QToolBar:
        """Create the console toolbar."""
        toolbar = QToolBar()
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        # Clear button
        clear_action = QAction(QIcon.fromTheme("edit-clear"), "Clear", self)
        clear_action.setToolTip("Clear console output")
        clear_action.triggered.connect(self.clear_requested.emit)
        toolbar.addAction(clear_action)

        toolbar.addSeparator()

        # Auto-scroll checkbox
        self.auto_scroll_checkbox = QCheckBox("Auto-scroll")
        self.auto_scroll_checkbox.setToolTip(
            "Automatically scroll to bottom when new output arrives")
        self.auto_scroll_checkbox.setChecked(True)
        toolbar.addWidget(self.auto_scroll_checkbox)

        # Word wrap checkbox
        self.word_wrap_checkbox = QCheckBox("Word wrap")
        self.word_wrap_checkbox.setToolTip("Enable word wrapping")
        self.word_wrap_checkbox.setChecked(True)
        self.word_wrap_checkbox.toggled.connect(self._toggle_word_wrap)
        toolbar.addWidget(self.word_wrap_checkbox)

        toolbar.addSeparator()

        # Timestamps checkbox
        self.show_timestamps_checkbox = QCheckBox("Timestamps")
        self.show_timestamps_checkbox.setToolTip(
            "Show timestamps for each output line")
        self.show_timestamps_checkbox.setChecked(True)
        toolbar.addWidget(self.show_timestamps_checkbox)

        # Show stdout checkbox
        self.show_stdout_checkbox = QCheckBox("stdout")
        self.show_stdout_checkbox.setToolTip("Show standard output")
        self.show_stdout_checkbox.setChecked(True)
        toolbar.addWidget(self.show_stdout_checkbox)

        # Show stderr checkbox
        self.show_stderr_checkbox = QCheckBox("stderr")
        self.show_stderr_checkbox.setToolTip("Show standard error output")
        self.show_stderr_checkbox.setChecked(True)
        toolbar.addWidget(self.show_stderr_checkbox)

        toolbar.addSeparator()

        # Search button
        search_action = QAction(QIcon.fromTheme("edit-find"), "Search", self)
        search_action.setToolTip("Search console output")
        search_action.triggered.connect(self._toggle_search)
        toolbar.addAction(search_action)

        # Export button
        export_icon = QIcon.fromTheme("document-save")
        if export_icon.isNull():
            # Create a simple fallback icon using Unicode
            export_icon = QIcon()
        export_action = QAction(export_icon, "Export", self)
        export_action.setToolTip("Export console output to file")
        export_action.triggered.connect(self._export_output)
        toolbar.addAction(export_action)

        return toolbar

    def _create_search_panel(self) -> QWidget:
        """Create the search panel."""
        panel = QWidget()
        layout = QHBoxLayout(panel)

        layout.addWidget(QLabel("Search:"))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search text...")
        self.search_input.returnPressed.connect(self._perform_search)
        layout.addWidget(self.search_input)

        # Search navigation buttons
        self.prev_button = QPushButton("Previous")
        self.prev_button.clicked.connect(self._search_previous)
        self.prev_button.setEnabled(False)
        layout.addWidget(self.prev_button)

        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self._search_next)
        self.next_button.setEnabled(False)
        layout.addWidget(self.next_button)

        # Case sensitive checkbox
        self.case_sensitive_checkbox = QCheckBox("Case sensitive")
        layout.addWidget(self.case_sensitive_checkbox)

        # Close search button
        close_button = QPushButton("×")
        close_button.setMaximumWidth(30)
        close_button.clicked.connect(
            lambda: self.search_panel.setVisible(False))
        layout.addWidget(close_button)

        return panel

    def _create_status_bar(self) -> QWidget:
        """Create the status bar."""
        status_widget = QWidget()
        layout = QHBoxLayout(status_widget)
        layout.setContentsMargins(5, 2, 5, 2)

        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

        layout.addStretch()

        self.stats_label = QLabel("0 lines")
        layout.addWidget(self.stats_label)

        return status_widget

    def _toggle_word_wrap(self, enabled: bool):
        """Toggle word wrapping in the console display."""
        if enabled:
            self.console_display.setLineWrapMode(
                QTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.console_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

    def _toggle_search(self):
        """Toggle the search panel visibility."""
        visible = not self.search_panel.isVisible()
        self.search_panel.setVisible(visible)
        if visible:
            self.search_input.setFocus()

    def _perform_search(self):
        """Perform search in console output."""
        # This will be connected to the presenter to perform actual search
        pass

    def _search_previous(self):
        """Navigate to previous search result."""
        if self._last_search_matches and self._current_search_index > 0:
            self._current_search_index -= 1
            self._highlight_search_result()

    def _search_next(self):
        """Navigate to next search result."""
        if self._last_search_matches and self._current_search_index < len(self._last_search_matches) - 1:
            self._current_search_index += 1
            self._highlight_search_result()

    def _highlight_search_result(self):
        """Highlight the current search result."""
        if not self._last_search_matches:
            return

        # Move cursor to the current match
        cursor = self.console_display.textCursor()
        # This is a simplified implementation - would need actual line-to-position mapping
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.console_display.setTextCursor(cursor)

    def _export_output(self):
        """Export console output to file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Console Output", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            self.export_requested.emit(file_path)

    def add_output_item(self, item: ConsoleOutputItem):
        """
        Add a new output item to the console display.

        Args:
            item: The console output item to add
        """
        # Format the output text
        formatted_text = self._format_output_item(item)

        # Get current cursor position to preserve scrolling
        cursor = self.console_display.textCursor()
        was_at_bottom = cursor.atEnd()

        # Move cursor to end and insert text
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.console_display.setTextCursor(cursor)

        # Remember where this item starts, before any text is inserted.
        self._item_block_numbers.append(cursor.blockNumber())

        # The colour says which stream the line came from. The [ERROR] prefix
        # added by _format_output_item says the same thing in text, so the
        # colour is never the only cue.
        char_format = QTextCharFormat()
        if item.output_type == 'stderr':
            char_format.setForeground(QColor(self.stderr_colour))
        else:
            char_format.setForeground(QColor(self.stdout_colour))

        cursor.insertText(formatted_text, char_format)

        # Auto-scroll if we were at the bottom and auto-scroll is enabled
        if was_at_bottom and self.auto_scroll_checkbox.isChecked():
            self._scroll_timer.start()  # Batch scroll operations

    def _format_output_item(self, item: ConsoleOutputItem) -> str:
        """
        Format an output item for display.

        Args:
            item: The console output item to format

        Returns:
            Formatted text string
        """
        prefix = ""

        if self.show_timestamps_checkbox.isChecked():
            timestamp_str = item.timestamp.strftime("%H:%M:%S.%f")[:-3]
            prefix += f"[{timestamp_str}] "

        if item.output_type == 'stderr':
            prefix += "[ERROR] "

        # Ensure the text ends with a newline if it doesn't already
        text = item.text
        if not text.endswith('\n'):
            text += '\n'

        return f"{prefix}{text}"

    def _do_auto_scroll(self):
        """Perform the actual auto-scroll operation."""
        scrollbar = self.console_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_display(self):
        """Clear the console display and forget every recorded block."""
        self.console_display.clear()
        self._item_block_numbers.clear()
        self._last_search_matches = []
        self._current_search_index = 0
        self.status_label.setText(self.tr("Console cleared"))

    def displayed_item_count(self) -> int:
        """Return how many output items the display currently holds."""
        return len(self._item_block_numbers)

    def block_number_for_items(self) -> List[int]:
        """Return the starting block number of every displayed item, in order."""
        return list(self._item_block_numbers)

    def update_stats(self, stats: dict):
        """
        Update the statistics display.

        Args:
            stats: Dictionary containing console statistics
        """
        total_lines = stats.get('total_lines', 0)
        stdout_lines = stats.get('stdout_lines', 0)
        stderr_lines = stats.get('stderr_lines', 0)

        stats_text = f"{total_lines} lines"
        if stderr_lines > 0:
            stats_text += f" ({stdout_lines} stdout, {stderr_lines} stderr)"

        self.stats_label.setText(stats_text)

    def set_search_results(self, matches: List[int]):
        """
        Set the search results.

        Args:
            matches: List of line indices where matches were found
        """
        self._last_search_matches = matches
        self._current_search_index = 0

        self.prev_button.setEnabled(len(matches) > 1)
        self.next_button.setEnabled(len(matches) > 1)

        if matches:
            self.status_label.setText(f"Found {len(matches)} matches")
            self._highlight_search_result()
        else:
            self.status_label.setText("No matches found")


class ConsoleView(BaseView):
    """Console view that integrates with the OPAQUE framework."""

    def __init__(self, app, parent: Optional[QWidget] = None):
        super().__init__(app, parent)
        self.setWindowTitle("Console")

        # Create console widget as the main content
        self.console_widget = ConsoleWidget(self)

        # Set up layout - but need to set the widget properly for MDI
        self.setWidget(self.console_widget)

    def add_output_item(self, item: ConsoleOutputItem):
        """Add output item to the console display."""
        self.console_widget.add_output_item(item)

    def clear_display(self):
        """Clear the console display."""
        self.console_widget.clear_display()

    def update_stats(self, stats: dict):
        """Update console statistics."""
        self.console_widget.update_stats(stats)

    def set_search_results(self, matches: List[int]):
        """Set search results."""
        self.console_widget.set_search_results(matches)

    def get_console_widget(self) -> ConsoleWidget:
        """Get the underlying console widget."""
        return self.console_widget
