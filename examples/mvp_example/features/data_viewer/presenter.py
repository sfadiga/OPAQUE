"""
Data Viewer Presenter - Coordinates between Model and View
"""
from typing import Any

from opaque.core.presenter import BasePresenter
from .model import DataViewerModel
from .view import DataViewerView


class DataViewerPresenter(BasePresenter):
    """Presenter for the data viewer feature."""
    model_class = DataViewerModel
    view_class = DataViewerView

    @property
    def feature_name(self) -> str:
        return "Data Viewer"

    @property
    def icon_path(self) -> str:
        return ""

    def __init__(self, app: Any, view: DataViewerView = None):
        """
        Initialize the data viewer presenter.
        
        Args:
            app: Application instance for service access
        """
        # Initialize base presenter
        super().__init__(app=app, view=view)
        
        # Log initialization
        self._log("info", "Data Viewer initialized")
    
    def initialize(self):
        """Initialize the presenter (required by BasePresenter)."""
        # Initialize the model
        self.model.initialize()
        
        # Initialize view with model data
        self._update_view()
    
    def bind_events(self):
        """Bind view events to presenter methods (required by BasePresenter)."""
        self.view.refresh_clicked.connect(self._on_refresh)
        self.view.add_clicked.connect(self._on_add_item)
        self.view.remove_clicked.connect(self._on_remove_item)
        self.view.clear_clicked.connect(self._on_clear)
        self.view.export_clicked.connect(self._on_export)
        self.view.import_clicked.connect(self._on_import)
    
    def update(self, property_name: str, value):
        """Handle model property changes (called by BaseModel)."""
        self._update_view()
        
        # Update status based on property
        if property_name == "data":
            self.view.set_status(f"Data updated: {len(value)} items")
            self._log("info", f"Data updated with {len(value)} items")
        elif property_name == "error":
            self.view.set_status(f"Error: {value}")
            self._log("error", f"Data viewer error: {value}")
    
    def _update_view(self):
        """Update view with current model state."""
        data = self.model.get_data()
        self.view.update_table(data)
        self.view.update_item_count(len(data))
        
        # Update filters if they've changed
        if hasattr(self.model, 'filters'):
            self.view.update_filters(self.model.filters)
    
    def _on_refresh(self):
        """Handle refresh button click."""
        # Use data service if available
        if self.app:
            data_service = self.app.get_service("data")
            if data_service:
                data = data_service.get_all_data()
                self.model.set_data(data)
                self._log("info", "Data refreshed from service")
            else:
                # Generate sample data
                self.model.generate_sample_data()
                self._log("info", "Sample data generated")
        else:
            self.model.generate_sample_data()
    
    def _on_add_item(self):
        """Handle add item button click."""
        # Get item details from view dialog
        item_data = self.view.get_new_item_data()
        if item_data:
            self.model.add_item(item_data)
            
            # Add to data service if available
            if self.app:
                data_service = self.app.get_service("data")
                if data_service:
                    data_service.add_data(item_data['id'], item_data)
    
    def _on_remove_item(self):
        """Handle remove item button click."""
        # Get selected item from view
        selected_id = self.view.get_selected_item_id()
        if selected_id:
            self.model.remove_item(selected_id)
            
            # Remove from data service if available
            if self.app:
                data_service = self.app.get_service("data")
                if data_service:
                    data_service.remove_data(selected_id)
    
    def _on_clear(self):
        """Handle clear button click."""
        self.model.clear_data()
        
        # Clear data service if available
        if self.app:
            data_service = self.app.get_service("data")
            if data_service:
                data_service.clear_data()
        
        self._log("info", "All data cleared")
    
    def _on_export(self):
        """Handle export button click."""
        # Get export path from view
        export_path = self.view.get_export_path()
        if export_path:
            success = self.model.export_data(export_path)
            if success:
                self.view.set_status(f"Data exported to {export_path}")
                self._log("info", f"Data exported to {export_path}")
            else:
                self.view.set_status("Export failed")
                self._log("error", "Data export failed")
    
    def _on_import(self):
        """Handle import button click."""
        # Get import path from view
        import_path = self.view.get_import_path()
        if import_path:
            success = self.model.import_data(import_path)
            if success:
                self.view.set_status(f"Data imported from {import_path}")
                self._log("info", f"Data imported from {import_path}")
                
                # Update data service if available
                if self.app:
                    data_service = self.app.get_service("data")
                    if data_service:
                        for item in self.model.get_data():
                            data_service.add_data(item['id'], item)
            else:
                self.view.set_status("Import failed")
                self._log("error", "Data import failed")
    
    def _log(self, level: str, message: str):
        """Log a message using the logging service if available."""
        if self.app:
            logging_service = self.app.get_service("logging")
            if logging_service:
                logging_service.log(level, f"[DataViewer] {message}")
    
    def on_view_show(self):
        """Show the data viewer view."""
        # Load initial data
        self._on_refresh()
    
    def cleanup(self):
        """Clean up resources."""
        self._log("info", "Data Viewer shutting down")
        super().cleanup()
