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

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

from opaque.features.context import FeatureContext
from opaque.models.model import BaseModel

if TYPE_CHECKING:
    # BaseView is only used as a type annotation in this file. Importing it
    # at module level closes a cycle: view.py -> widgets -> toolbar.py ->
    # presenter.py, which then re-imports view.py before BaseView exists.
    from opaque.view.view import BaseView

logger = logging.getLogger(__name__)


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
            context: FeatureContext,
    ) -> None:
        """
        Initialize the presenter.

        The identity comes from the model and from nowhere else. It used to be
        an optional argument that fell back to the presenter class name, so
        renaming a class lost the saved settings and the saved workspace.

        The context is what the feature is allowed to know about the
        application.
        """
        self._feature_id: str = model.feature_id()

        self._context: FeatureContext = context
        # a presenter must have be associated with a view and a model
        # if there is a need for a presenter without one of those
        # just pass a dummy implementation of the BaseView / BaseModel
        self._model: BaseModel = model
        self._view: BaseView = view

        # True after the close sequence has run once. A sub-window can emit
        # window_closed more than once, and cleanup must not run twice.
        self._closed: bool = False

        # True after cleanup() has run. The shell calls cleanup() for every
        # feature at closeEvent, and a presenter whose view already closed
        # has run it once by then. Disconnecting twice does not raise (the
        # RuntimeError is caught below) but libpyside emits a RuntimeWarning
        # that no except clause can silence, so the second call must not
        # reach the disconnect at all.
        self._cleaned: bool = False

        # Connect to view events
        self._view.window_opened.connect(self.on_view_show)
        self._view.window_closed.connect(self._handle_view_closed)

        # Set window title from feature interface
        self._view.setWindowTitle(self._model.feature_name())

        # Set window icon from the feature interface
        icon = self._model.feature_icon()
        if icon and not icon.isNull():
            self._view.setWindowIcon(icon)

        # Attach presenter to model as observer
        self._model.attach(self)

        # Bind events. This is the last step of __init__ on purpose: the
        # model and the view are both ready by now. It also means the
        # subclass cannot bind an attribute it creates after its own
        # super().__init__(...) call, so translate that failure into a
        # message that says so.
        try:
            self.bind_events()
        except AttributeError as error:
            raise AttributeError(
                f"{type(self).__name__}.bind_events() used an attribute that "
                f"does not exist yet: {error}. BasePresenter.__init__ calls "
                f"bind_events() as its last step, so anything your __init__ "
                f"creates after super().__init__(...) is not there yet. "
                f"Create it before the super() call, or move the connection "
                f"into on_view_show()."
            ) from error

    def __hash__(self) -> int:
        """Presenter feature_id will be used to identify a presenter"""
        return hash(self.feature_id)

    @property
    def feature_id(self) -> str:
        """
        The identity of this feature, declared by the model as FEATURE_ID.

        It keys the feature registry, the settings block and the workspace
        block. All three are the same key.
        """
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
    def context(self) -> FeatureContext:
        """The context this feature was built with."""
        return self._context

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

    def _handle_view_closed(self) -> None:
        """
        Run the subclass hook, then release the presenter.

        The framework owns this order on purpose. on_view_close() used to be
        abstract and to carry the cleanup in its own body, so a subclass that
        overrode it without calling super() stayed attached to its model and
        stayed connected to its view for the rest of the process. A subclass
        cannot forget an order it does not own.
        """
        if self._closed:
            return
        self._closed = True
        # DEBUG, not WARNING. Closing a window is normal work. The previous
        # version logged a WARNING on every close.
        logger.debug("closing the presenter %s", self.feature_id)
        self.on_view_close()
        self.cleanup()

    def on_view_close(self) -> None:
        """
        Called when the view is closed. Override to save state.

        Do not call cleanup() here and do not call super(). The framework
        calls cleanup() straight after this method returns.

        The hook runs when the sub-window itself closes. At application
        exit the shell calls cleanup() directly, so a window that is still
        open at that moment does not run this hook.
        """

    def save_workspace(self, workspace_object: dict) -> None:
        """
        Save the current workspace state.

        The block is keyed on feature_id, the same key the settings file uses.
        It used to be keyed on the presenter class name, so renaming a class
        lost every saved workspace.

        Override this to add more state.
        """
        block: dict = {"window_state": self.view.get_geometry_state()}
        for name, field in type(self.model).get_fields().items():
            if field.is_workspace:
                block[name] = getattr(self.model, name)
        workspace_object[self.feature_id] = block

    def load_workspace(self, workspace_object: dict) -> None:
        """
        Restore a previously saved workspace state.

        Override this to restore more state.
        """
        block = workspace_object.get(self.feature_id)
        if not block:
            return

        if "window_state" in block:
            self.view.set_geometry_state(block["window_state"])

        fields = type(self.model).get_fields()
        for key, value in block.items():
            if key == "window_state" or key not in fields:
                continue
            # One stale or rejected value must not abort the rest of the
            # restore: a file saved before a validator was added can hold
            # a value the model now refuses. The settings path skips a bad
            # stored value per field the same way.
            try:
                coerced = fields[key].coerce(value)
                setattr(self.model, key, coerced)
            except (TypeError, ValueError) as error:
                logger.warning(
                    "workspace value %r for %s.%s was rejected: %s",
                    value, self.feature_id, key, error)
                continue
            self.update(key, coerced)

    def cleanup(self) -> None:
        """
        Clean up presenter resources. Safe to call twice: the second call
        returns without touching the model or the view.
        """
        if self._cleaned:
            return
        self._cleaned = True

        # Detach from model
        self._model.detach(self)

        # Disconnect from view events
        try:
            self._view.window_closed.disconnect(self._handle_view_closed)
            self._view.window_opened.disconnect(self.on_view_show)
        except RuntimeError:
            # Already disconnected
            pass

        # Clean up model
        self._model.cleanup()
