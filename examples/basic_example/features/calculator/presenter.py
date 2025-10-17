"""
Calculator Presenter - Coordinates between Model and View
"""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from opaque.core.application import BaseApplication

from opaque.core.presenter import BasePresenter
from opaque.core.services import ServiceLocator


from .model import CalculatorModel
from .view import CalculatorView


class CalculatorPresenter(BasePresenter):
    """Presenter for the calculator feature."""
    model_class = CalculatorModel
    view_class = CalculatorView

    def __init__(self, feature_id: str, model: CalculatorModel, view: CalculatorView, app: 'BaseApplication'):
        """
        Initialize the calculator presenter.
        """
        super().__init__(feature_id=feature_id, model=model, view=view, app=app)

    def bind_events(self):
        """Bind view events to presenter methods (required by BasePresenter)."""
        self.view.digit_clicked.connect(self._on_digit_clicked)
        self.view.operation_clicked.connect(self._on_operation_clicked)
        self.view.equals_clicked.connect(self._on_equals_clicked)
        self.view.clear_clicked.connect(self._on_clear_clicked)
        self.view.clear_entry_clicked.connect(self._on_clear_entry_clicked)
        self.view.backspace_clicked.connect(self._on_backspace_clicked)
        self.view.toggle_sign_clicked.connect(self._on_toggle_sign_clicked)
        self.view.clear_history_clicked.connect(self._on_clear_history_clicked)

    def update(self, property_name: str, value):
        """Handle model property changes (called by BaseModel)."""
        self._update_view()

        # Update status based on property
        if property_name == "state" and value == "cleared":
            self.view.set_status("Calculator cleared")
        elif property_name == "operation":
            self.view.set_status(f"Operation: {value}")
        elif property_name == "current_value":
            if value == "Error":
                self.view.set_status("Error in calculation")
                self._log("error", "Calculation error")
            else:
                self.view.set_status(f"Result: {value}")
        elif property_name == "error":
            self.view.set_status(f"Error: {value}")
            self._log("error", f"Calculation error: {value}")

    def _update_view(self):
        """Update view with current model state."""
        self.view.update_display(self.model.current_value)
        self.view.update_history(self.model.get_history())

        # Update theme color if it has changed
        if hasattr(self.model, 'theme_color'):
            self.view.set_theme_color(self.model.theme_color)

    def _on_digit_clicked(self, digit: str):
        """Handle digit button click."""
        self.model.append_digit(digit)
        self._log("debug", f"Digit clicked: {digit}")

    def _on_operation_clicked(self, operation: str):
        """Handle operation button click."""
        self.model.set_operation(operation)

        # Use calculation service if available
        calc_service = ServiceLocator.get_service("calculation")
        if calc_service:
            # Store in service history
            calc_service._add_to_history(f"Operation: {operation}")

    def _on_equals_clicked(self):
        """Handle equals button click."""
        self.model.execute_operation()

        # Use calculation service if available
        calc_service = ServiceLocator.get_service("calculation")
        if calc_service and self.model.current_value != "Error":
            # Store result in service
            calc_service._add_to_history(
                f"Result: {self.model.current_value}")

    def _on_clear_clicked(self):
        """Handle clear button click."""
        self.model.clear()

    def _on_clear_entry_clicked(self):
        """Handle clear entry button click."""
        self.model.clear_entry()

    def _on_backspace_clicked(self):
        """Handle backspace button click."""
        self.model.backspace()

    def _on_toggle_sign_clicked(self):
        """Handle toggle sign button click."""
        self.model.toggle_sign()

    def _on_clear_history_clicked(self):
        """Handle clear history button click."""
        self.model.clear_history()
        self._log("info", "History cleared")

    def _log(self, level: str, message: str):
        """Log a message using the logging service if available."""
        logging_service = ServiceLocator.get_service("logging")
        if logging_service:
            logging_service.log(level, f"[Calculator] {message}")

    def on_view_show(self):
        """Show the calculator view."""
        # Update view with initial data now that widgets are ready
        self._update_view()

    def cleanup(self):
        """Clean up resources."""
        self._log("info", "Calculator shutting down")
        super().cleanup()
