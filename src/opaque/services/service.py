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
from typing import Optional, Type, TypeVar
import threading

from PySide6.QtCore import QObject, Signal


class BaseService(QObject):
    """
    Abstract base class for all services in the application.
    Services encapsulate business logic and can be accessed via the service locator.

    A subclass declares SERVICE_NAME, and that one string is both the name it
    registers under and the key ServiceLocator.get() looks up. The name used
    to be a literal inside each constructor call and another literal at each
    call site, with nothing connecting the two.
    """

    # The registry key of this service. A subclass must declare it. Empty on
    # the base class, which is never registered.
    SERVICE_NAME: str = ""

    def __init__(self, name: Optional[str] = None):
        """
        Initialize the service.

        Args:
            name: Service name for identification. Defaults to SERVICE_NAME,
                which is what every service in the framework uses. Pass a
                name only to register two instances of one class, which the
                framework never does.

        Raises:
            ValueError: When neither a name nor a SERVICE_NAME is given.
        """
        super().__init__()  # Initialize QObject properly
        resolved = name or self.SERVICE_NAME
        if not resolved:
            raise ValueError(
                f"{type(self).__name__} must declare SERVICE_NAME, for "
                f"example:\n"
                f"    class {type(self).__name__}(BaseService):\n"
                f"        SERVICE_NAME = 'my_service'\n"
                f"It is the key ServiceLocator uses.")
        self._name = resolved
        self._initialized = False

    @property
    def name(self) -> str:
        """Get the service name"""
        return self._name

    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized"""
        return self._initialized

    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the service with any required configuration.
        Override this method to perform service-specific initialization.
        """
        self._initialized = True

    @abstractmethod
    def cleanup(self) -> None:
        """
        Clean up service resources.
        Override this method to perform service-specific cleanup.
        """
        self._initialized = False


# Bound to BaseService so ServiceLocator.get() can only be asked for a real
# service class, and so the answer keeps the type the caller asked for.
ServiceType = TypeVar("ServiceType", bound="BaseService")


class ServiceLocator:
    """
    Service locator pattern implementation for managing application services.
    This is a singleton that provides static methods for service management.
    """
    _services: dict[str, BaseService] = {}
    _lock = threading.RLock()

    @classmethod
    def get(cls, service_class: Type[ServiceType]) -> ServiceType:
        """
        Return the registered service of this class.

        Use this when the application cannot work without the service, which
        is the normal case. It raises instead of answering None, because a
        None that is never checked is how a misspelled service name stayed
        in the code base for months without one failing test.

        Args:
            service_class: The service class to look up. Its SERVICE_NAME is
                the registry key.

        Returns:
            The registered instance, typed as the class that was asked for.

        Raises:
            LookupError: When no service is registered under that name.
            TypeError: When another class is registered under that name.
        """
        with cls._lock:
            found = cls._services.get(service_class.SERVICE_NAME)
            registered = sorted(cls._services)

        if found is None:
            raise LookupError(
                f"No {service_class.__name__} is registered under the name "
                f"'{service_class.SERVICE_NAME}'. Registered services: "
                f"{registered}. A service must be initialized and registered "
                f"before a feature asks for it; BaseApplication.__init__ does "
                f"that for the framework services.")

        if not isinstance(found, service_class):
            raise TypeError(
                f"The name '{service_class.SERVICE_NAME}' is registered by "
                f"{type(found).__name__}, not by {service_class.__name__}.")

        return found

    @classmethod
    def get_optional(
            cls, service_class: Type[ServiceType]) -> Optional[ServiceType]:
        """
        Return the registered service of this class, or None.

        Use this only where absence is normal. The console service is the one
        such case in the framework: it exists only when a console feature has
        been registered.

        Args:
            service_class: The service class to look up.

        Returns:
            The registered instance, or None when it is not registered or
            another class holds the name.
        """
        with cls._lock:
            found = cls._services.get(service_class.SERVICE_NAME)

        if found is None or not isinstance(found, service_class):
            return None

        return found

    @classmethod
    def register_service(cls, service: BaseService) -> None:
        """
        Register a service with the locator.

        Args:
            service: Service instance to register

        Raises:
            ValueError: If a service with the same name already exists
                        or if the service is not initialized.
        """
        with cls._lock:
            if service.name in cls._services:
                raise ValueError(f"Service '{service.name}' is already registered")

            if not service.is_initialized:
                raise ValueError(
                    f"Service '{service.name}' must be initialized before being registered"
                )

            expected = type(service).SERVICE_NAME
            if expected and service.name != expected:
                raise ValueError(
                    f"{type(service).__name__} declares SERVICE_NAME "
                    f"'{expected}' but is registering as '{service.name}'. "
                    f"ServiceLocator.get() looks up the declared name, so a "
                    f"service registered under any other name cannot be "
                    f"found.")

            # Don't call initialize() again - service should already be initialized
            cls._services[service.name] = service

    @classmethod
    def unregister_service(cls, name: str) -> bool:
        """
        Remove a service from the locator.

        Args:
            name: Service identifier

        Returns:
            True if the service was removed, False if not found
        """
        with cls._lock:
            if name in cls._services:
                service = cls._services[name]
                service.cleanup()
                del cls._services[name]
                return True
            return False

    @classmethod
    def cleanup_services(cls) -> None:
        """
        Clean up all registered services.
        """
        with cls._lock:
            for service in cls._services.values():
                service.cleanup()
            cls._services.clear()
