"""
Console widget for displaying captured stdout/stderr output.

@copyright 2025 Sandro Fadiga
Licensed under MIT License
"""

from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QToolBar, QLineEdit,
    QLabel, QCheckBox, QPushButton, QFileDialog, QSplitter
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import (
    QTextCursor, QColor, QTextCharFormat, QIcon, QAction, QKeySequence,
    QShortcut,
)

from opaque.view.view import BaseView
from opaque.models.console_model import ConsoleOutputItem
from opaque.view.widgets.close_button import CloseButton
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
    search_requested = Signal()

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
        self.console_display.setAccessibleName(self.tr("Console output"))
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

        # F3 and Shift+F3 on most platforms. QKeySequence picks the right key
        # for the platform, so do not write the key names by hand.
        self.next_shortcut = QShortcut(
            QKeySequence.StandardKey.FindNext, self)
        self.next_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut)
        # A QShortcut carries no label, and the keyboard map dialog needs one.
        self.next_shortcut.setWhatsThis(self.tr("Console: find next"))
        self.next_shortcut.activated.connect(self._search_next)

        self.prev_shortcut = QShortcut(
            QKeySequence.StandardKey.FindPrevious, self)
        self.prev_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.prev_shortcut.setWhatsThis(self.tr("Console: find previous"))
        self.prev_shortcut.activated.connect(self._search_previous)

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

        self.clear_action = QAction(
            QIcon.fromTheme("edit-clear"), self.tr("Clear"), self)
        self.clear_action.setShortcut(QKeySequence("Ctrl+L"))
        self.clear_action.setShortcutContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.clear_action.setToolTip(self.tr("Clear console output (Ctrl+L)"))
        self.clear_action.triggered.connect(self.clear_requested.emit)
        self.addAction(self.clear_action)
        toolbar.addAction(self.clear_action)

        toolbar.addSeparator()

        # Auto-scroll checkbox
        self.auto_scroll_checkbox = QCheckBox(self.tr("Auto-scroll"))
        self.auto_scroll_checkbox.setToolTip(
            self.tr("Automatically scroll to bottom when new output arrives"))
        self.auto_scroll_checkbox.setChecked(True)
        toolbar.addWidget(self.auto_scroll_checkbox)

        # Word wrap checkbox
        self.word_wrap_checkbox = QCheckBox(self.tr("Word wrap"))
        self.word_wrap_checkbox.setToolTip(self.tr("Enable word wrapping"))
        self.word_wrap_checkbox.setChecked(True)
        self.word_wrap_checkbox.toggled.connect(self._toggle_word_wrap)
        toolbar.addWidget(self.word_wrap_checkbox)

        toolbar.addSeparator()

        # Timestamps checkbox
        self.show_timestamps_checkbox = QCheckBox(self.tr("Timestamps"))
        self.show_timestamps_checkbox.setToolTip(
            self.tr("Show timestamps for each output line"))
        self.show_timestamps_checkbox.setChecked(True)
        toolbar.addWidget(self.show_timestamps_checkbox)

        # Show stdout checkbox
        self.show_stdout_checkbox = QCheckBox(self.tr("stdout"))
        self.show_stdout_checkbox.setToolTip(self.tr("Show standard output"))
        self.show_stdout_checkbox.setChecked(True)
        toolbar.addWidget(self.show_stdout_checkbox)

        # Show stderr checkbox
        self.show_stderr_checkbox = QCheckBox(self.tr("stderr"))
        self.show_stderr_checkbox.setToolTip(self.tr("Show standard error output"))
        self.show_stderr_checkbox.setChecked(True)
        toolbar.addWidget(self.show_stderr_checkbox)

        toolbar.addSeparator()

        self.search_action = QAction(
            QIcon.fromTheme("edit-find"), self.tr("Search"), self)
        self.search_action.setShortcut(QKeySequence.StandardKey.Find)
        self.search_action.setShortcutContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.search_action.setToolTip(self.tr("Search console output (Ctrl+F)"))
        self.search_action.triggered.connect(self._toggle_search)
        self.addAction(self.search_action)
        toolbar.addAction(self.search_action)

        export_icon = QIcon.fromTheme("document-save")
        if export_icon.isNull():
            # Create a simple fallback icon using Unicode
            export_icon = QIcon()
        self.export_action = QAction(export_icon, self.tr("Export"), self)
        self.export_action.setShortcut(QKeySequence("Ctrl+E"))
        self.export_action.setShortcutContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.export_action.setToolTip(
            self.tr("Export console output to file (Ctrl+E)"))
        self.export_action.triggered.connect(self._export_output)
        self.addAction(self.export_action)
        toolbar.addAction(self.export_action)

        return toolbar

    def _create_search_panel(self) -> QWidget:
        """Create the search panel."""
        panel = QWidget()
        layout = QHBoxLayout(panel)

        layout.addWidget(QLabel(self.tr("Search:")))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("Enter search text..."))
        self.search_input.setAccessibleName(self.tr("Search console output"))
        self.search_input.returnPressed.connect(self.search_requested.emit)
        layout.addWidget(self.search_input)

        # Search navigation buttons
        self.prev_button = QPushButton(self.tr("Previous"))
        self.prev_button.clicked.connect(self._search_previous)
        self.prev_button.setEnabled(False)
        layout.addWidget(self.prev_button)

        self.next_button = QPushButton(self.tr("Next"))
        self.next_button.clicked.connect(self._search_next)
        self.next_button.setEnabled(False)
        layout.addWidget(self.next_button)

        # Case sensitive checkbox
        self.case_sensitive_checkbox = QCheckBox(self.tr("Case sensitive"))
        layout.addWidget(self.case_sensitive_checkbox)

        self.close_search_button = CloseButton()
        self.close_search_button.setAccessibleName(self.tr("Close search"))
        self.close_search_button.setToolTip(self.tr("Close search (Escape)"))
        self.close_search_button.clicked.connect(self.hide_search)
        layout.addWidget(self.close_search_button)

        return panel

    def _create_status_bar(self) -> QWidget:
        """Create the status bar."""
        status_widget = QWidget()
        layout = QHBoxLayout(status_widget)
        layout.setContentsMargins(5, 2, 5, 2)

        self.status_label = QLabel(self.tr("Ready"))
        layout.addWidget(self.status_label)

        layout.addStretch()

        self.stats_label = QLabel(self.tr("0 lines"))
        layout.addWidget(self.stats_label)

        return status_widget

    def _toggle_word_wrap(self, enabled: bool):
        """Toggle word wrapping in the console display."""
        if enabled:
            self.console_display.setLineWrapMode(
                QTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.console_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

    def show_search(self) -> None:
        """Open the search panel and put the caret in the search box."""
        self.search_panel.setVisible(True)
        self.search_input.setFocus()

    def hide_search(self) -> None:
        """Close the search panel and give the focus back to the output."""
        self.search_panel.setVisible(False)
        self.console_display.setFocus()

    def _toggle_search(self) -> None:
        """Open the search panel, or close it if it is already open."""
        # isVisibleTo() answers for this widget alone. isVisible() would answer
        # False whenever the console window itself is not on the screen.
        if self.search_panel.isVisibleTo(self):
            self.hide_search()
        else:
            self.show_search()

    def keyPressEvent(self, event) -> None:
        """Escape closes the search panel and returns to the output."""
        if (event.key() == Qt.Key.Key_Escape
                and self.search_panel.isVisibleTo(self)):
            self.hide_search()
            event.accept()
            return
        super().keyPressEvent(event)

    def _search_previous(self) -> None:
        """Go to the previous match. Wrap to the last match at the start."""
        if not self._last_search_matches:
            return
        self._current_search_index = (
            self._current_search_index - 1) % len(self._last_search_matches)
        self._highlight_search_result()

    def _search_next(self) -> None:
        """Go to the next match. Wrap to the first match at the end."""
        if not self._last_search_matches:
            return
        self._current_search_index = (
            self._current_search_index + 1) % len(self._last_search_matches)
        self._highlight_search_result()

    def _highlight_search_result(self) -> None:
        """Select the line of the current match and scroll it into view."""
        if not self._last_search_matches:
            return

        item_index = self._last_search_matches[self._current_search_index]
        if item_index < 0 or item_index >= len(self._item_block_numbers):
            return

        block = self.console_display.document().findBlockByNumber(
            self._item_block_numbers[item_index])
        if not block.isValid():
            return

        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                            QTextCursor.MoveMode.KeepAnchor)
        self.console_display.setTextCursor(cursor)
        self.console_display.ensureCursorVisible()
        self._update_search_status()

    def _update_search_status(self) -> None:
        """Say which match of how many the user is looking at."""
        total = len(self._last_search_matches)
        if total == 0:
            self.status_label.setText(self.tr("No matches found"))
            return
        position = self._current_search_index + 1
        self.status_label.setText(
            self.tr("Match {0} of {1}").format(position, total))

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
            self._highlight_search_result()
        else:
            self._update_search_status()


class ConsoleView(BaseView):
    """Console view that integrates with the OPAQUE framework."""

    def __init__(self, context, parent: Optional[QWidget] = None):
        super().__init__(context, parent)

    def setup_ui(self) -> None:
        self.setWindowTitle(self.tr("Console"))

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
