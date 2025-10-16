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
from typing import Any, Optional


class BaseService(ABC):
    """
    Abstract base class for all services in the application.
    Services encapsulate business logic and can be accessed via the service locator.
    """

    def __init__(self, name: str):
        """
        Initialize the service.
        Args:
            name: service name for identification
        """
        self._name = name
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


class ServiceLocator:
    """
    Service locator pattern implementation for managing application services.
    """

    def __init__(self):
        """Initialize the service locator"""
        self._services: dict[str, BaseService] = {}

    def register_service(self, service: BaseService) -> None:
        """
        Register a service with the locator.

        Args:
            name: Service identifier
            service: Service instance

        Raises:
            ValueError: If service with same name already exists
        """
        if service.name in self._services:
            raise ValueError(f"Service '{service.name}' is already registered")

        # A service must be initialized before registered
        if not service.is_initialized:
            raise ValueError(f"Service '{service.name}' must be initialized before registered")

        self._services[service.name] = service

    def get_service(self, name: str) -> Optional[BaseService]:
        """
        Get a registered service by name.

        Args:
            name: Service identifier

        Returns:
            Service instance or None if not found
        """
        return self._services.get(name)

    def remove_service(self, name: str) -> bool:
        """
        Remove a service from the locator.

        Args:
            name: Service identifier

        Returns:
            True if service was removed, False if not found
        """
        if name in self._services:
            service = self._services[name]
            service.cleanup()
            del self._services[name]
            return True
        return False

    def cleanup_all(self) -> None:
        """
        Clean up all registered services.
        """
        for service in self._services.values():
            service.cleanup()
        self._services.clear()
