"""
Data Viewer View - UI components and user interaction
"""
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QWidget, QFileDialog,
    QInputDialog, QMessageBox, QHeaderView
)
from PySide6.QtCore import Signal, QDateTime
from opaque.view.view import BaseView
from opaque.view.application import BaseApplication
from typing import Any, Dict, List, Optional


class DataViewerView(BaseView):
    """View for the data viewer feature."""

    # Signals for user interactions
    refresh_clicked = Signal()
    add_clicked = Signal()
    remove_clicked = Signal()
    clear_clicked = Signal()
    export_clicked = Signal()
    import_clicked = Signal()

    def __init__(self, app: BaseApplication, parent: Optional[QWidget] = None):
        """Initialize the view."""
        super().__init__(app, parent)
        self.init_ui()

    def feature_id(self) -> str:
        """Return the feature ID."""
        return "data_viewer"


    def init_ui(self):
        """Initialize the UI components."""
        # Create main layout
        layout = QVBoxLayout()

        # Create toolbar
        toolbar_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_clicked.emit)
        toolbar_layout.addWidget(self.refresh_btn)

        self.add_btn = QPushButton("Add Item")
        self.add_btn.clicked.connect(self.add_clicked.emit)
        toolbar_layout.addWidget(self.add_btn)

        self.remove_btn = QPushButton("Remove Item")
        self.remove_btn.clicked.connect(self.remove_clicked.emit)
        toolbar_layout.addWidget(self.remove_btn)

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.clear_clicked.emit)
        toolbar_layout.addWidget(self.clear_btn)

        toolbar_layout.addStretch()

        self.import_btn = QPushButton("Import")
        self.import_btn.clicked.connect(self.import_clicked.emit)
        toolbar_layout.addWidget(self.import_btn)

        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self.export_clicked.emit)
        toolbar_layout.addWidget(self.export_btn)

        layout.addLayout(toolbar_layout)

        # Create info bar
        info_layout = QHBoxLayout()
        self.item_count_label = QLabel("Items: 0")
        info_layout.addWidget(self.item_count_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)

        # Create table
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        # Create status bar
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

        # Set the layout
        container = QWidget()
        container.setLayout(layout)
        self.setWidget(container)

    def update_table(self, data: List[Dict[str, Any]]):
        """Update the table with data."""
        if not data:
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return

        # Set up columns
        if data:
            columns = list(data[0].keys())
            self.table.setColumnCount(len(columns))
            self.table.setHorizontalHeaderLabels(columns)

            # Set row count
            self.table.setRowCount(len(data))

            # Populate table
            for row_idx, item in enumerate(data):
                for col_idx, column in enumerate(columns):
                    value = item.get(column, '')
                    # Convert to string for display
                    if isinstance(value, bool):
                        value = "Yes" if value else "No"
                    elif value is None:
                        value = ""
                    else:
                        value = str(value)

                    table_item = QTableWidgetItem(value)
                    self.table.setItem(row_idx, col_idx, table_item)

            # Resize columns to content
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

    def update_item_count(self, count: int):
        """Update the item count label."""
        self.item_count_label.setText(f"Items: {count}")

    def update_filters(self, filters: Dict[str, Any]):
        """Update filter display (if we had filter UI)."""
        # In a real implementation, this would update filter UI elements
        pass

    def set_status(self, message: str):
        """Update the status label."""
        self.status_label.setText(message)

    def get_selected_item_id(self) -> Optional[str]:
        """Get the ID of the selected item."""
        current_row = self.table.currentRow()
        if current_row >= 0:
            # Assuming first column is ID
            id_item = self.table.item(current_row, 0)
            if id_item:
                return id_item.text()
        return None

    def get_new_item_data(self) -> Optional[Dict[str, Any]]:
        """Show dialog to get new item data."""
        # Simple input dialog for demonstration
        text, ok = QInputDialog.getText(
            self,
            "Add Item",
            "Enter item name:"
        )

        if ok and text:
            import random
            return {
                'id': f'item_{random.randint(1000, 9999)}',
                'name': text,
                'value': random.randint(100, 1000),
                'category': random.choice(['A', 'B', 'C']),
                'created': QDateTime.currentDateTime().toString(),
                'active': random.choice([True, False])
            }
        return None

    def get_export_path(self) -> Optional[str]:
        """Get file path for export."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Data",
            "",
            "JSON Files (*.json);;All Files (*.*)"
        )
        return file_path if file_path else None

    def get_import_path(self) -> Optional[str]:
        """Get file path for import."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Data",
            "",
            "JSON Files (*.json);;All Files (*.*)"
        )
        return file_path if file_path else None

    def show_error(self, title: str, message: str):
        """Show an error message."""
        QMessageBox.critical(self, title, message)

    def show_info(self, title: str, message: str):
        """Show an information message."""
        QMessageBox.information(self, title, message)

    def confirm_action(self, title: str, message: str) -> bool:
        """Show a confirmation dialog."""
        reply = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes
