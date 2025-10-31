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

from opaque.view.view import BaseView
from opaque.models.model import BaseModel

if TYPE_CHECKING:
    from opaque.view.application import BaseApplication


class BasePresenter(ABC):
    """
    Base class for MVP presenters.
    Presenters handle the interaction between Model and View,
    containing the presentation logic and coordinating updates.
    """

    def __init__(
            self,
            model: BaseModel,
            view: BaseView,
            app: 'BaseApplication',
            feature_id: Optional[str] = None
    ) -> None:
        """
        Initialize the presenter.
        """

        # Auto-generate feature_id if not provided
        if feature_id is None:
            # Use the presenter class name as the feature_id
            self._feature_id = self.__class__.__name__
        else:
            self._feature_id = feature_id
            
        self._app: 'BaseApplication' = app
        # a presenter must have be associated with a view and a model
        # if there is a need for a presenter without one of those
        # just pass a dummy implementation of the BaseView / BaseModel
        self._model: BaseModel = model
        self._view: BaseView = view

        # Connect to view events
        self._view.window_opened.connect(self.on_view_show)
        self._view.window_closed.connect(self.on_view_close)


        # Set window title from feature interface
        self._view.setWindowTitle(self._model.feature_name())

        # Set window icon from the feature interface
        icon = self._model.feature_icon()
        if icon and not icon.isNull():
            self._view.setWindowIcon(icon)

        # Attach presenter to model as observer
        self._model.attach(self)

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
    def app(self) -> 'BaseApplication':
        """Get the application instance."""
        return self._app

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

    @abstractmethod
    def update(self, field_name: str, new_value: Any, old_value: Any = None, model: Any = None) -> None:
        """
        Called when a model field changes.
        Override this to update the view based on model field changes.

        Args:
            field_name: Name of the changed field
            new_value: New value of the field
            old_value: Previous value of the field (optional for backward compatibility)
            model: The model instance that changed (optional for backward compatibility)
        """
        pass

    @abstractmethod
    def on_view_show(self) -> None:
        """
        Called when the view is shown.
        Override this to perform actions when view becomes visible.
        """
        pass

    @abstractmethod
    def on_view_close(self) -> None:
        """
        Called when the view is closed.
        Override this to perform cleanup or save state.
        """
        print("presenter cleanup")
        self.cleanup()

    def save_workspace(self, workspace_object: dict) -> None:
        """
        Save the current worskpace state.
        Override this to implement state persistence.
        """
        state = self.view.get_geometry_state()
        workspace_object[self.__class__.__name__] = {"window_state": state}
        fields = type(self.model).get_fields()
        for name, field in fields.items():
            if field.is_workspace:
                workspace_object[self.__class__.__name__][name] = getattr(self.model, name)

    def load_workspace(self, workspace_object: dict) -> None:
        """
        Restore a previously workspace saved state.
        Override this to implement state restoration.
        """
        if self.__class__.__name__ in workspace_object:
            if "window_state" in workspace_object[self.__class__.__name__]:
                state = workspace_object[self.__class__.__name__]["window_state"]
                self.view.set_geometry_state(state)
            if workspace_object[self.__class__.__name__]:
                for key, value in workspace_object[self.__class__.__name__].items():
                    if hasattr(self.model, key):
                        setattr(self.model, key, value)
                        self.update(key, value)

    def cleanup(self) -> None:
        """
        Clean up presenter resources.
        """
        # Detach from model
        self._model.detach(self)

        # Disconnect from view events
        try:
            self._view.window_closed.disconnect(self.on_view_close)
            self._view.window_opened.disconnect(self.on_view_show)
        except RuntimeError:
            # Already disconnected
            pass

        # Clean up model
        self._model.cleanup()
