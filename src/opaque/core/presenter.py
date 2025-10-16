# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Type

from opaque.core.view import BaseView
from opaque.core.model import BaseModel


class BasePresenter(ABC):
    """
    Base class for MVP presenters.
    Presenters handle the interaction between Model and View,
    containing the presentation logic and coordinating updates.
    """

    def __init__(self):
        """
        Initialize the presenter.
        """

        # Extending class must initialize its model and view
        self._model: BaseModel = None
        self._view: BaseView = None

        # Attach presenter to model as observer
        self._model.attach(self)

        # Connect to view events
        self._view.view_shown.connect(self.on_view_show)
        self._view.view_closed.connect(self.on_view_close)

        # Set window title from feature interface
        self._view.setWindowTitle(self._model.feature_name())

        # Set window icon from the feature interface
        icon = self._model.feature_icon()
        if icon and not icon.isNull():
            self._view.setWindowIcon(icon)

        # Bind events
        self.bind_events()

    @property
    def model(self) -> BaseModel:
        """Get the model"""
        return self._model

    @property
    def view(self) -> BaseView:
        """Get the view"""
        return self._view

    @abstractmethod
    def bind_events(self) -> None:
        """
        Bind view events to presenter methods.
        Override this to connect UI events to handlers.
        """
        pass

    def update(self, property_name: str, value: Any) -> None:
        """
        Called when a model property changes.
        Override this to update the view based on model changes.

        Args:
            property_name: Name of the changed property
            value: New value of the property
        """
        pass

    def on_view_show(self) -> None:
        """
        Called when the view is shown.
        Override this to perform actions when view becomes visible.
        """
        pass

    def on_view_close(self) -> None:
        """
        Called when the view is closed.
        Override this to perform cleanup or save state.
        """
        self.save_state()
        self.cleanup()

    def save_state(self) -> None:
        """
        Save the current state.
        Override this to implement state persistence.
        """
        pass

    def restore_state(self) -> None:
        """
        Restore a previously saved state.
        Override this to implement state restoration.
        """
        pass

    def cleanup(self) -> None:
        """
        Clean up presenter resources.
        """
        # Detach from model
        self._model.detach(self)

        # Disconnect from view events
        try:
            self._view.view_shown.disconnect(self.on_view_show)
            self._view.view_closed.disconnect(self.on_view_close)
        except RuntimeError:
            # Already disconnected
            pass

        # Clean up model
        self._model.cleanup()

    def show_view(self) -> None:
        """Show the view"""
        self._view.show()

    def hide_view(self) -> None:
        """Hide the view"""
        self._view.hide()

    def close_view(self) -> None:
        """Close the view"""
        self._view.close()
