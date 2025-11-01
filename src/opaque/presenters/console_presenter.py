"""
Console presenter for coordinating console service, model, and view.

@copyright 2025 Sandro Fadiga
Licensed under MIT License
"""

from typing import Dict, Any, TYPE_CHECKING
from PySide6.QtWidgets import QMessageBox

from opaque.presenters.presenter import BasePresenter
from opaque.models.console_model import ConsoleModel, ConsoleOutputItem
from opaque.view.widgets.console_widget import ConsoleView
from opaque.services.service import ServiceLocator
from opaque.services.console_service import ConsoleService

if TYPE_CHECKING:
    from opaque.view.application import BaseApplication


class ConsolePresenter(BasePresenter):
    """Presenter for managing the console feature."""

    def __init__(self, model: ConsoleModel, app: 'BaseApplication'):
        # Create view with app parameter
        view = ConsoleView(app)

        # Initialize base class - need to pass model as Any since ConsoleModel doesn't inherit from BaseModel
        super().__init__(model, view, app, "console")  # type: ignore

        self._initialized = False

        # Get or create console service
        self.console_service = ServiceLocator.get_service("console")
        if self.console_service is None:
            self.console_service = ConsoleService()
            self.console_service.initialize()
            ServiceLocator.register_service(self.console_service)

        self._setup_connections()

    def initialize(self):
        """Initialize the presenter and start console capture."""
        self._initialized = True

        # Start console capture if enabled in configuration
        self._start_console_capture()

        # Update initial stats
        self._update_stats()

    def cleanup(self):
        """Clean up resources when presenter is destroyed."""
        if self.console_service:
            self.console_service.stop_capture()
        self._initialized = False

    def _setup_connections(self):
        """Set up signal/slot connections between components."""
        # Connect console service to model
        if hasattr(self.console_service, 'output_received'):
            self.console_service.output_received.connect(
                self._on_console_output)

        # Connect model to view
        self.model.output_added.connect(self._on_output_added)
        self.model.output_cleared.connect(self._on_output_cleared)

        # Connect view actions to presenter methods
        console_widget = self.view.get_console_widget()
        console_widget.clear_requested.connect(self._clear_console)
        console_widget.export_requested.connect(self._export_console)

        # Connect search functionality
        search_input = console_widget.search_input
        search_input.textChanged.connect(self._perform_search)
        console_widget.case_sensitive_checkbox.toggled.connect(
            self._perform_search)

        # Connect filter checkboxes
        console_widget.show_stdout_checkbox.toggled.connect(
            self._update_filters)
        console_widget.show_stderr_checkbox.toggled.connect(
            self._update_filters)
        console_widget.show_timestamps_checkbox.toggled.connect(
            self._update_display)

        # Connect model settings to view checkboxes
        console_widget.auto_scroll_checkbox.toggled.connect(
            lambda checked: setattr(self.model, '_auto_scroll', checked)
        )
        console_widget.word_wrap_checkbox.toggled.connect(
            lambda checked: setattr(self.model, '_word_wrap', checked)
        )

    def _start_console_capture(self):
        """Start console capture if service is available."""
        if self.console_service and not self.console_service.is_capturing():
            # Always preserve original streams so regular console still works
            self.console_service.start_capture(preserve_original=True)

    def _on_console_output(self, output_dict: Dict[str, Any]):
        """Handle new console output from the service."""
        try:
            # Add output to model (model will emit signal to update view)
            self.model.add_output_from_dict(output_dict)
            self._update_stats()
        except Exception as e:
            print(f"Error processing console output: {e}")

    def _on_output_added(self, output_item: ConsoleOutputItem):
        """Handle when output is added to the model."""
        # Check if this output type should be displayed
        if self._should_display_output(output_item):
            self.view.add_output_item(output_item)

    def _on_output_cleared(self):
        """Handle when console output is cleared."""
        self.view.clear_display()
        self._update_stats()

    def _should_display_output(self, output_item: ConsoleOutputItem) -> bool:
        """Check if output item should be displayed based on current filters."""
        console_widget = self.view.get_console_widget()

        if output_item.output_type == 'stdout':
            return console_widget.show_stdout_checkbox.isChecked()
        elif output_item.output_type == 'stderr':
            return console_widget.show_stderr_checkbox.isChecked()

        return True

    def _clear_console(self):
        """Clear the console output."""
        self.model.clear_output()

    def _export_console(self, file_path: str):
        """Export console output to file."""
        try:
            console_widget = self.view.get_console_widget()
            include_timestamps = console_widget.show_timestamps_checkbox.isChecked()

            success = self.model.export_to_file(file_path, include_timestamps)

            if success:
                console_widget.status_label.setText(f"Exported to {file_path}")
            else:
                QMessageBox.warning(
                    self.view,
                    "Export Failed",
                    "Failed to export console output to file."
                )
        except Exception as e:
            QMessageBox.critical(
                self.view,
                "Export Error",
                f"An error occurred while exporting: {e}"
            )

    def _perform_search(self):
        """Perform search in console output."""
        try:
            console_widget = self.view.get_console_widget()
            search_text = console_widget.search_input.text().strip()

            if not search_text:
                self.view.set_search_results([])
                return

            case_sensitive = console_widget.case_sensitive_checkbox.isChecked()
            matches = self.model.search_output(search_text, case_sensitive)

            self.view.set_search_results(matches)
        except Exception as e:
            print(f"Error performing search: {e}")

    def _update_filters(self):
        """Update output filters and refresh display."""
        try:
            console_widget = self.view.get_console_widget()

            # Update model settings
            show_stdout = console_widget.show_stdout_checkbox.isChecked()
            show_stderr = console_widget.show_stderr_checkbox.isChecked()

            # Update model properties directly
            self.model.show_stdout = show_stdout
            self.model.show_stderr = show_stderr

            # Refresh the display
            self._refresh_display()
            self._update_stats()
        except Exception as e:
            print(f"Error updating filters: {e}")

    def _update_display(self):
        """Update display settings and refresh."""
        try:
            console_widget = self.view.get_console_widget()

            # Update timestamps setting
            show_timestamps = console_widget.show_timestamps_checkbox.isChecked()
            self.model.show_timestamps = show_timestamps

            # Refresh display
            self._refresh_display()
        except Exception as e:
            print(f"Error updating display: {e}")

    def _refresh_display(self):
        """Refresh the console display with current filters."""
        try:
            # Clear the current display
            console_widget = self.view.get_console_widget()
            console_widget.console_display.clear()

            # Re-add filtered output
            filtered_output = self.model.get_filtered_output()
            for output_item in filtered_output:
                console_widget.add_output_item(output_item)

        except Exception as e:
            print(f"Error refreshing display: {e}")

    def _update_stats(self):
        """Update console statistics display."""
        try:
            stats = self.model.get_buffer_stats()
            self.view.update_stats(stats)
        except Exception as e:
            print(f"Error updating stats: {e}")

    def toggle_console_capture(self, enabled: bool):
        """
        Toggle console capture on/off.

        Args:
            enabled: Whether to enable or disable console capture
        """
        if not self.console_service:
            return

        if enabled and not self.console_service.is_capturing():
            self.console_service.start_capture(preserve_original=True)
        elif not enabled and self.console_service.is_capturing():
            self.console_service.stop_capture()

    def is_console_capturing(self) -> bool:
        """Check if console is currently capturing output."""
        return self.console_service and self.console_service.is_capturing()

    def write_to_console(self, text: str, output_type: str = 'stdout'):
        """
        Programmatically write text to the console.

        Args:
            text: Text to write
            output_type: 'stdout' or 'stderr'
        """
        if self.console_service:
            self.console_service.write_to_console(text, output_type)

    def get_console_stats(self) -> Dict[str, Any]:
        """Get current console statistics."""
        return self.model.get_buffer_stats()

    def bind_events(self):
        """Bind events - required abstract method implementation."""
        # Events are already bound in _setup_connections
        pass

    def update(self, field_name: str, new_value: Any, old_value: Any = None, model: Any = None) -> None:
        """Update the presenter - required abstract method implementation."""
        # Handle model field updates
        # Refresh stats and display when any field changes
        self._update_stats()

    def on_view_show(self):
        """Called when view is shown - required abstract method implementation."""
        # Ensure console capture is running when view is shown
        if not self.is_console_capturing():
            self._start_console_capture()
        self._update_stats()

    def on_view_close(self):
        """Called when view is closed - required abstract method implementation."""
        # Optionally stop capture when view is closed (or keep it running)
        # For now, keep capture running so output is still collected
        pass
