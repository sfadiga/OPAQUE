"""
Example Calculation Service
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from opaque.core.services import BaseService


class CalculationService(BaseService):
    """Service that provides calculation functionality to features."""

    def __init__(self):
        super().__init__("CalculationService")
        self._history: list[str] = []
        self._memory: float | None = None

    def _add_to_history(self, entry: str) -> None:
        """Add an entry to history."""
        self._history.append(entry)
        # Keep only last 100 entries
        if len(self._history) > 100:
            self._history.pop(0)

    # no special need for initialization
    def initialize(self):
        """Initialize the calculation service."""
        super().initialize()

    # no special need for cleanup
    def cleanup(self):
        """Cleanup calculation service"""
        super().cleanup()

    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        result = a + b
        self._add_to_history(f"{a} + {b} = {result}")
        return result

    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a."""
        result = a - b
        self._add_to_history(f"{a} - {b} = {result}")
        return result

    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        result = a * b
        self._add_to_history(f"{a} * {b} = {result}")
        return result

    def divide(self, a: float, b: float) -> float:
        """Divide a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
        self._add_to_history(f"{a} / {b} = {result}")
        return result

    def memory_store(self, a: float) -> float:
        """Store number a in memory"""
        self._memory = a
        self._add_to_history(f"M = {a}")
        return a

    def memory_add(self, a: float) -> float:
        """Add the number a to the number stored in memory"""
        if self._memory:
            return self.add(self._memory, a)
        return 0

    def memory_clear(self) -> None:
        """Clear the memory"""
        self._add_to_history(f"MC = {self._memory}")
        self._memory = None
        return self._memory

    def get_history(self) -> list[str]:
        """Get calculation history."""
        return self._history.copy()

    def clear_history(self) -> None:
        """Clear calculation history."""
        self._history.clear()
