"""
Calculator Model - Handles the calculator state and business logic
"""
from typing import List
from PySide6.QtGui import QIcon

from opaque.models.annotations import IntField, BoolField, StringField, ListField, UIType
from opaque.models.model import BaseModel
from opaque.view.application import BaseApplication


class CalculatorModel(BaseModel):
    """Model for the calculator feature using annotations for persistence."""

    # --- Feature Interface ---
    FEATURE_NAME = "Calculator"
    FEATURE_TITLE = "Calculator"
    FEATURE_ICON = "document-properties"
    FEATURE_DESCRIPTION = "A Simple Calculator"
    FEATURE_MODAL = False
    # ----------------------------------

    # Settings - persisted to user settings
    decimal_places = IntField(
        default=2,
        description="Number of decimal places to display",
        settings=True,
        min_value=0,
        max_value=10
    )

    scientific_notation = BoolField(
        default=False,
        description="Use scientific notation for large numbers",
        settings=True,
        binding=True
    )

    # theme can be altered in settings and also saved in the workspace
    theme_color = StringField(
        default="#4CAF50",
        description="Calculator theme color",
        settings=True,
        workspace=True,
        binding=True,
        ui_type=UIType.COLOR_PICKER
    )

    # Workspace state - persisted to workspace file
    current_value = StringField(
        default="0",
        description="Current display value",
        workspace=True,
        binding=True
    )

    last_operation = StringField(
        default="",
        description="Last operation performed",
        workspace=True,
        binding=True
    )

    history = ListField(
        default=[],
        description="Calculation history",
        workspace=True,
        binding=True
    )

    def __init__(self, app: BaseApplication):
        super().__init__(app)
        self.clear_on_next = False
        self.pending_operation = None
        self.pending_value = None
        self.current_value = "0"
        self.last_operation = ""

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

    # ----------------------------------------------------

    def initialize(self):
        """Initialize the model (required by BaseModel)."""
        self._reset_state()

    def _reset_state(self):
        """Reset calculator to initial state."""
        self.current_value = "0"
        self.last_operation = ""

    def clear(self):
        """Clear the calculator."""
        self._reset_state()
        self.notify("state", "cleared")

    def clear_entry(self):
        """Clear only the current entry."""
        self.current_value = "0"
        self.clear_on_next = False

    def append_digit(self, digit: str):
        """Append a digit to the current value."""
        if self.clear_on_next:
            self.current_value = "0"
            self.clear_on_next = False

        if digit == "." and "." in self.current_value:
            return  # Already has decimal point

        if self.current_value == "0" and digit != ".":
            self.current_value = digit
        else:
            self.current_value += digit


    def set_operation(self, operation: str):
        """Set the pending operation."""
        # If we have a pending operation, execute it first
        if self.pending_operation and not self.clear_on_next:
            self.execute_operation()

        self.pending_operation = operation
        self.pending_value = float(self.current_value)
        self.clear_on_next = True
        self.last_operation = operation


    def execute_operation(self):
        """Execute the pending operation."""
        if not self.pending_operation or self.pending_value is None:
            return

        try:
            current = float(self.current_value)
            result = self._calculate(
                self.pending_value, current, self.pending_operation)

            # Add to history
            history_entry = f"{self.pending_value} {self.pending_operation} {current} = {result}"
            if not hasattr(self, 'history') or self.history is None:
                self.history = []
            self.history.append(history_entry)

            # Update display
            if self.scientific_notation and abs(result) > 1e6:
                self.current_value = f"{result:.{self.decimal_places}e}"
            else:
                self.current_value = str(round(result, self.decimal_places))

            self.pending_operation = None
            self.pending_value = None
            self.clear_on_next = True


        except Exception:
            self.current_value = "Error"
            self.clear_on_next = True

    def _calculate(self, a: float, b: float, operation: str) -> float:
        """Perform the actual calculation."""
        if operation == "+":
            return a + b
        elif operation == "-":
            return a - b
        elif operation == "*":
            return a * b
        elif operation == "/":
            if b == 0:
                raise ValueError("Division by zero")
            return a / b
        elif operation == "^":
            return a ** b
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def toggle_sign(self):
        """Toggle the sign of the current value."""
        if self.current_value != "0":
            if self.current_value.startswith("-"):
                self.current_value = self.current_value[1:]
            else:
                self.current_value = "-" + self.current_value
            self.notify("current_value", self.current_value)

    def backspace(self):
        """Remove the last digit."""
        if self.clear_on_next:
            return

        if len(self.current_value) > 1:
            self.current_value = self.current_value[:-1]
        else:
            self.current_value = "0"


    def get_history(self) -> List[str]:
        """Get calculation history."""
        return self.history if hasattr(self, 'history') and self.history else []

    def clear_history(self):
        """Clear calculation history."""
        self.history = []
