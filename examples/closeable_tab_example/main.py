#!/usr/bin/env python3
# This Python file uses the following encoding: utf-8
"""
CloseableTabWidget Example

This example demonstrates how to use the CloseableTabWidget from the OPAQUE framework.
It shows various features including:
- Creating tabs with different widget types
- Adding and removing tabs
- Renaming tabs
- Workspace save/load functionality
- Custom widget factories
"""

from opaque.view.widgets import CloseableTabWidget
import json
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QLabel, QTextEdit, QSpinBox,
    QListWidget, QMenuBar, QFileDialog, QMessageBox
)
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TextWidget(QWidget):
    """A simple text editor widget for demonstration."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)

        # Add a label
        label = QLabel("Text Editor Tab")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        # Add a text editor
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(
            "This is a text editor widget.\nYou can type here...")
        layout.addWidget(self.text_edit)

    def get_workspace_data(self):
        """Return workspace data for this widget."""
        return {
            'text_content': self.text_edit.toPlainText()
        }

    def load_workspace_data(self, data):
        """Load workspace data for this widget."""
        if 'text_content' in data:
            self.text_edit.setPlainText(data['text_content'])


class CounterWidget(QWidget):
    """A simple counter widget for demonstration."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)

        # Add a label
        label = QLabel("Counter Tab")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        # Add counter controls
        controls_layout = QHBoxLayout()

        self.spin_box = QSpinBox()
        self.spin_box.setRange(-1000, 1000)
        self.spin_box.setValue(0)
        controls_layout.addWidget(QLabel("Value:"))
        controls_layout.addWidget(self.spin_box)

        increment_btn = QPushButton("+1")
        increment_btn.clicked.connect(
            lambda: self.spin_box.setValue(self.spin_box.value() + 1))
        controls_layout.addWidget(increment_btn)

        decrement_btn = QPushButton("-1")
        decrement_btn.clicked.connect(
            lambda: self.spin_box.setValue(self.spin_box.value() - 1))
        controls_layout.addWidget(decrement_btn)

        layout.addLayout(controls_layout)

        # Add some info
        info_label = QLabel(
            "This is a counter widget with workspace save/load support.")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        layout.addStretch()

    def get_workspace_data(self):
        """Return workspace data for this widget."""
        return {
            'counter_value': self.spin_box.value()
        }

    def load_workspace_data(self, data):
        """Load workspace data for this widget."""
        if 'counter_value' in data:
            self.spin_box.setValue(data['counter_value'])


class ListWidget(QWidget):
    """A simple list widget for demonstration."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)

        # Add a label
        label = QLabel("List Tab")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        # Add list widget
        self.list_widget = QListWidget()
        self.list_widget.addItems([
            "Item 1",
            "Item 2",
            "Item 3",
            "Click 'Add Item' to add more items"
        ])
        layout.addWidget(self.list_widget)

        # Add controls
        controls_layout = QHBoxLayout()

        add_btn = QPushButton("Add Item")
        add_btn.clicked.connect(self._add_item)
        controls_layout.addWidget(add_btn)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_selected)
        controls_layout.addWidget(remove_btn)

        layout.addLayout(controls_layout)

    def _add_item(self):
        """Add a new item to the list."""
        count = self.list_widget.count()
        self.list_widget.addItem(f"New Item {count + 1}")

    def _remove_selected(self):
        """Remove the selected item from the list."""
        current_row = self.list_widget.currentRow()
        if current_row >= 0:
            self.list_widget.takeItem(current_row)

    def get_workspace_data(self):
        """Return workspace data for this widget."""
        items = []
        for i in range(self.list_widget.count()):
            items.append(self.list_widget.item(i).text())
        return {
            'list_items': items,
            'selected_row': self.list_widget.currentRow()
        }

    def load_workspace_data(self, data):
        """Load workspace data for this widget."""
        if 'list_items' in data:
            self.list_widget.clear()
            self.list_widget.addItems(data['list_items'])

        if 'selected_row' in data and data['selected_row'] >= 0:
            self.list_widget.setCurrentRow(data['selected_row'])


class MainWindow(QMainWindow):
    """Main window demonstrating the CloseableTabWidget."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("CloseableTabWidget Example")
        self.setGeometry(100, 100, 800, 600)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Create info label
        info_label = QLabel(
            "This example demonstrates the CloseableTabWidget.\n"
            "• Double-click tabs to rename them\n"
            "• Click the '+' tab to add new tabs\n"
            "• Click 'X' on tabs to close them\n"
            "• Use the menu to save/load workspace or create specific tab types"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            "QLabel { background-color: #f0f0f0; padding: 10px; }")
        layout.addWidget(info_label)

        # Create the closeable tab widget with different factory functions
        self.tab_widget = CloseableTabWidget(
            widget_factory=self._create_text_widget,
            default_tab_name="Text Editor",
            minimum_tabs=1,
            show_plus_tab=True
        )

        layout.addWidget(self.tab_widget)

        # Connect signals for demonstration
        self.tab_widget.currentTabChanged.connect(self._on_tab_changed)
        self.tab_widget.tabAdded.connect(self._on_tab_added)
        self.tab_widget.tabRemoved.connect(self._on_tab_removed)
        self.tab_widget.tabRenamed.connect(self._on_tab_renamed)

        # Create menu bar
        self._setup_menu()

        # Create status bar
        self.statusBar().showMessage("Ready - Tab widget example loaded")

    def _create_text_widget(self):
        """Factory function to create text editor widgets."""
        return TextWidget()

    def _create_counter_widget(self):
        """Factory function to create counter widgets."""
        return CounterWidget()

    def _create_list_widget(self):
        """Factory function to create list widgets."""
        return ListWidget()

    def _setup_menu(self):
        """Set up the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        save_action = QAction("Save Workspace", self)
        save_action.triggered.connect(self._save_workspace)
        file_menu.addAction(save_action)

        load_action = QAction("Load Workspace", self)
        load_action.triggered.connect(self._load_workspace)
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Add Tab menu
        tab_menu = menubar.addMenu("Add Tab")

        add_text_action = QAction("Add Text Editor", self)
        add_text_action.triggered.connect(lambda: self.tab_widget.add_tab(
            "Text Editor", self._create_text_widget()))
        tab_menu.addAction(add_text_action)

        add_counter_action = QAction("Add Counter", self)
        add_counter_action.triggered.connect(
            lambda: self.tab_widget.add_tab("Counter", self._create_counter_widget()))
        tab_menu.addAction(add_counter_action)

        add_list_action = QAction("Add List", self)
        add_list_action.triggered.connect(
            lambda: self.tab_widget.add_tab("List", self._create_list_widget()))
        tab_menu.addAction(add_list_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _on_tab_changed(self, index):
        """Handle tab change events."""
        tab_name = self.tab_widget.get_tab_name(index)
        if tab_name:
            self.statusBar().showMessage(f"Switched to tab: {tab_name}")

    def _on_tab_added(self, index, name):
        """Handle tab added events."""
        self.statusBar().showMessage(f"Added tab: {name} at index {index}")

    def _on_tab_removed(self, index, name):
        """Handle tab removed events."""
        self.statusBar().showMessage(f"Removed tab: {name} from index {index}")

    def _on_tab_renamed(self, index, old_name, new_name):
        """Handle tab renamed events."""
        self.statusBar().showMessage(
            f"Renamed tab at index {index}: '{old_name}' -> '{new_name}'")

    def _save_workspace(self):
        """Save the current workspace to a file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Workspace",
            "workspace.json",
            "JSON Files (*.json)"
        )

        if file_path:
            try:
                workspace_data = self.tab_widget.get_workspace_data()
                with open(file_path, 'w') as f:
                    json.dump(workspace_data, f, indent=2)

                self.statusBar().showMessage(
                    f"Workspace saved to: {file_path}")
                QMessageBox.information(
                    self, "Success", f"Workspace saved successfully to:\n{file_path}")

            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to save workspace:\n{str(e)}")

    def _load_workspace(self):
        """Load a workspace from a file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Workspace",
            "",
            "JSON Files (*.json)"
        )

        if file_path:
            try:
                with open(file_path, 'r') as f:
                    workspace_data = json.load(f)

                # Update the tab widget's factory based on loaded data
                success = self.tab_widget.load_workspace_data(workspace_data)

                if success:
                    self.statusBar().showMessage(
                        f"Workspace loaded from: {file_path}")
                    QMessageBox.information(
                        self, "Success", f"Workspace loaded successfully from:\n{file_path}")
                else:
                    QMessageBox.warning(
                        self, "Warning", "Workspace loaded with some errors. Check the console for details.")

            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to load workspace:\n{str(e)}")

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About CloseableTabWidget Example",
            "This example demonstrates the CloseableTabWidget from the OPAQUE framework.\n\n"
            "Features demonstrated:\n"
            "• Closeable and renameable tabs\n"
            "• Different widget types in tabs\n"
            "• Workspace save/load functionality\n"
            "• Custom widget factories\n"
            "• Tab management signals\n\n"
            "Double-click on tabs to rename them.\n"
            "Click the '+' tab to add new tabs.\n"
            "Use the menu to create specific widget types."
        )


def main():
    """Main function to run the example."""
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("CloseableTabWidget Example")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("OPAQUE Framework")

    # Create and show main window
    window = MainWindow()
    window.show()

    # Run the application
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
