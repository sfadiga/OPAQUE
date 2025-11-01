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
from typing import Optional

from PySide6.QtCore import QObject, Signal


class BaseService(QObject):
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
        super().__init__()  # Initialize QObject properly
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
    This is a singleton that provides static methods for service management.
    """
    _services: dict[str, BaseService] = {}

    @classmethod
    def get_service(cls, name: str) -> Optional[BaseService]:
        """
        Get a registered service by name.

        Args:
            name: Service identifier

        Returns:
            Service instance or None if not found
        """
        return cls._services.get(name)

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
        if service.name in cls._services:
            raise ValueError(f"Service '{service.name}' is already registered")

        if not service.is_initialized:
            raise ValueError(
                f"Service '{service.name}' must be initialized before being registered"
            )

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
        for service in cls._services.values():
            service.cleanup()
        cls._services.clear()
