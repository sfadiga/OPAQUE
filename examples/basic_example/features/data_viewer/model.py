"""
Data Viewer Model - Business logic and state management
"""
import json
from typing import List, Dict, Any
from datetime import datetime
from PySide6.QtGui import QIcon
from opaque.core.model import BaseModel
from opaque.models.annotations import BoolField, IntField, StringField


class DataViewerModel(BaseModel):
    """Model for the data viewer feature."""

    # --- Feature Interface ---
    FEATURE_NAME = "Data Viewer"
    FEATURE_TITLE = "Data Viewer"
    FEATURE_ICON = "format-justify-left"
    FEATURE_DESCRIPTION = "A tool to view and manage data."
    FEATURE_MODAL = False
    # ----------------------------------

    # Settings that persist across sessions
    auto_refresh = BoolField(default=True, binding=True,
                             settings=True, description="Auto-refresh data on startup")
    refresh_interval = IntField(
        default=30,
        description="Refresh interval in seconds",
        binding=True,
        settings=True,
        min_value=0,
        max_value=100
    )

    max_items = IntField(
        default=100, description="Maximum items to display",  settings=True,
        binding=True,
        min_value=10,
        max_value=100)

    # Workspace state that saves with workspace
    last_filter = StringField(
        default="", worskpace=True, description="Last applied filter")
    sort_column = StringField(
        default="id", worskpace=True, description="Column to sort by")
    sort_order = StringField(
        default="asc", worskpace=True, description="Sort order")

    def __init__(self, feature_id: str):
        """Initialize the model."""
        super().__init__(feature_id)
        self.data = []
        self.filters = {}
        self.selected_item = None

        # Initialize with sample data if auto_refresh is enabled
        if self.auto_refresh:
            self.generate_sample_data()

    def get_data(self) -> List[Dict[str, Any]]:
        """Get the current data."""
        return self.data

    def set_data(self, data: List[Dict[str, Any]]):
        """Set the data and notify observers."""
        self.data = data
        self.notify("data", data)

    def add_item(self, item: Dict[str, Any]):
        """Add an item to the data."""
        if len(self.data) >= self.max_items:
            self.notify(
                "error", f"Maximum items limit ({self.max_items}) reached")
            return

        self.data.append(item)
        self.notify("data", self.data)

    def remove_item(self, item_id: str):
        """Remove an item from the data."""
        initial_length = len(self.data)
        self.data = [item for item in self.data if item.get('id') != item_id]

        if len(self.data) < initial_length:
            self.notify("data", self.data)
        else:
            self.notify("error", f"Item with id {item_id} not found")

    def clear_data(self):
        """Clear all data."""
        self.data = []
        self.notify("data", self.data)

    def generate_sample_data(self):
        """Generate sample data for demonstration."""
        sample_data = []
        for i in range(10):
            sample_data.append({
                'id': f'item_{i+1}',
                'name': f'Sample Item {i+1}',
                'value': (i + 1) * 100,
                'category': ['A', 'B', 'C'][i % 3],
                'created': datetime.now().isoformat(),
                'active': i % 2 == 0
            })

        self.set_data(sample_data)

    def apply_filter(self, filter_dict: Dict[str, Any]):
        """Apply filters to the data."""
        self.filters = filter_dict
        # In a real implementation, this would filter the data
        # For now, just store the filters
        self.last_filter = json.dumps(filter_dict)
        self.notify("filters", filter_dict)

    def sort_data(self, column: str, order: str = "asc"):
        """Sort the data by the specified column."""
        self.sort_column = column
        self.sort_order = order

        try:
            reverse = (order == "desc")
            self.data = sorted(self.data, key=lambda x: x.get(
                column, ''), reverse=reverse)
            self.notify("data", self.data)
        except Exception as e:
            self.notify("error", f"Failed to sort: {str(e)}")

    def export_data(self, file_path: str) -> bool:
        """Export data to a JSON file."""
        try:
            with open(file_path, 'w') as f:
                json.dump(self.data, f, indent=2)
            return True
        except Exception as e:
            self.notify("error", f"Export failed: {str(e)}")
            return False

    def import_data(self, file_path: str) -> bool:
        """Import data from a JSON file."""
        try:
            with open(file_path, 'r') as f:
                imported_data = json.load(f)

            if not isinstance(imported_data, list):
                raise ValueError("Imported data must be a list")

            self.set_data(imported_data)
            return True
        except Exception as e:
            self.notify("error", f"Import failed: {str(e)}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the current data."""
        if not self.data:
            return {
                'total_items': 0,
                'categories': {},
                'active_count': 0,
                'total_value': 0
            }

        categories = {}
        active_count = 0
        total_value = 0

        for item in self.data:
            # Count by category
            category = item.get('category', 'Unknown')
            categories[category] = categories.get(category, 0) + 1

            # Count active items
            if item.get('active', False):
                active_count += 1

            # Sum values
            total_value += item.get('value', 0)

        return {
            'total_items': len(self.data),
            'categories': categories,
            'active_count': active_count,
            'total_value': total_value,
            'average_value': total_value / len(self.data) if self.data else 0
        }

    # --- Model Interface --------------------------------

    def feature_name(self) -> str:
        """Get the feature name associated with this model."""
        return self.FEATURE_NAME

    def feature_icon(self) -> QIcon:
        """Override in subclasses to provide icon (can return str or QIcon)"""
        return QIcon.fromTheme(self.FEATURE_ICON)

    def feature_description(self) -> str:
        """Override in subclasses"""
        return self.FEATURE_DESCRIPTION

    def feature_modal(self) -> bool:
        """Override in subclasses"""
        return self.FEATURE_MODAL
