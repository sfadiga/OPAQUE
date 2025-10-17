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
from typing import Any, Optional, TYPE_CHECKING

from opaque.core.view import BaseView
from opaque.core.model import BaseModel
from opaque.core.exceptions import ModelNotDefinedError, ViewNotDefinedError

if TYPE_CHECKING:
    from opaque.core.application import BaseApplication


class BasePresenter(ABC):
    """
    Base class for MVP presenters.
    Presenters handle the interaction between Model and View,
    containing the presentation logic and coordinating updates.
    """

    def __init__(
            self,
            feature_id: str,
            model: BaseModel,
            view: BaseView,
            app: 'BaseApplication'
    ) -> None:
        """
        Initialize the presenter.
        """

        # unique id for each feature of the project
        self._feature_id = feature_id
        self._app_ref: 'BaseApplication' = app

        # a presenter must have be associated with a view and a model
        # if there is a need for a presenter without one of those
        # just pass a dummy implementation of the BaseView / BaseModel
        if not model:
            raise ModelNotDefinedError(feature_id=feature_id)
        self._model = model
        self._model.set_application(app)

        if not view:
            raise ViewNotDefinedError(feature_id=feature_id)
        self._view = view
        self._view.set_application(app)

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

    def __hash__(self) -> int:
        """Prensenter feature_id will be used to identify a prensenter"""
        return hash(self.feature_id)

    @property
    def feature_id(self) -> str:
        """Get the feature id"""
        return self._feature_id

    @property
    def model(self) -> BaseModel:
        """Get the model"""
        return self._model

    @property
    def view(self) -> BaseView:
        """Get the view"""
        return self._view

    @property
    def app(self) -> Optional['BaseApplication']:
        """Get the application instance."""
        return self._app_ref() if self._app_ref else None

    @abstractmethod
    def bind_events(self) -> None:
        """
        Bind view events to presenter methods.
        Override this to connect UI events to handlers.
        """
        pass

    def apply_settings(self) -> None:
        """
        Apply any pending settings changes.
        This method is called after settings have been saved, allowing the
        presenter to react to changes that require immediate action, such as
        re-rendering a view or updating a service.
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
