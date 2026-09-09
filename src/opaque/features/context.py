# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

What a feature is allowed to know about its application.
"""

from typing import Optional, Type, TypeVar

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget

from opaque.models.configuration import DefaultApplicationConfiguration
from opaque.services.service import BaseService, ServiceLocator

ServiceType = TypeVar("ServiceType", bound=BaseService)


class FeatureContext:
    """
    Everything a feature may know about the application it runs in.

    A model, a view and a presenter used to take the whole BaseApplication,
    which is a QMainWindow that also owns the service registry, the feature
    registry, the toolbar and the MDI area. A feature that holds that can
    reach anything, and ApplicationModel did: it read a private attribute
    through it. The context gives three things and nothing else: the
    configuration, a typed service lookup, and one way to put a window on
    screen.

    A service is looked up on every call, never cached, so nothing here can
    hold a service that has been cleaned up.
    """

    def __init__(
            self,
            configuration: DefaultApplicationConfiguration,
            shell: Optional[QWidget] = None,
    ) -> None:
        """
        Build a context.

        Args:
            configuration: The application configuration. Read only as far as
                a feature is concerned.
            shell: The main window, when there is one. A test builds a
                context without it, and show_window then refuses instead of
                failing somewhere deeper.
        """
        self._configuration = configuration
        self._shell = shell

    @property
    def configuration(self) -> DefaultApplicationConfiguration:
        """The application configuration."""
        return self._configuration

    @property
    def shell(self) -> Optional[QWidget]:
        """
        The main window, or None in a test that has no shell.

        Prefer show_window() over reaching through this. It is here so a
        feature that genuinely needs a parent widget, for example a modal
        dialog, has one.
        """
        return self._shell

    def service(self, service_class: Type[ServiceType]) -> ServiceType:
        """
        Return the service of this class, or raise.

        Args:
            service_class: The service class to look up.

        Returns:
            The registered service, typed as the class asked for.

        Raises:
            LookupError: When the service is not registered.
        """
        return ServiceLocator.get(service_class)

    def optional_service(
            self, service_class: Type[ServiceType]) -> Optional[ServiceType]:
        """
        Return the service of this class, or None.

        Use this only where absence is normal, for example the console
        service, which exists only when a console feature was registered.
        """
        return ServiceLocator.get_optional(service_class)

    def application_icon(self) -> QIcon:
        """
        The application icon, as a QIcon.

        The configuration answers with whatever the application declared, a
        path or an icon, and a feature should not have to know which.
        """
        icon = self._configuration.get_application_icon()
        return icon if isinstance(icon, QIcon) else QIcon(icon)

    def show_window(self, view: QWidget) -> None:
        """
        Put one feature window on screen.

        Args:
            view: The view to show.

        Raises:
            RuntimeError: When the context has no shell, which means the
                feature was built outside an application.
        """
        if self._shell is None:
            raise RuntimeError(
                "This FeatureContext has no shell, so it cannot show a "
                "window. A context built by BaseApplication has one; a "
                "context built in a test does not. Pass shell=... if the "
                "test needs to show a window.")

        add_sub_window = getattr(self._shell, "add_feature_window", None)
        if add_sub_window is None:
            raise RuntimeError(
                f"{type(self._shell).__name__} cannot host a feature window: "
                f"it has no add_feature_window(view) method.")
        add_sub_window(view)
