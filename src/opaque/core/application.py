
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


from typing import List, Optional, Type, Dict, Union
from abc import abstractmethod
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QApplication, QDialog, QWidget, QMainWindow
from PySide6.QtGui import QAction, QIcon, QCloseEvent
from PySide6.QtCore import Qt

from opaque.widgets.mdi_window import OpaqueMdiArea
from opaque.core.view import BaseView
from opaque.widgets.toolbar import OpaqueMainToolbar
from opaque.widgets.dialogs.settings import SettingsDialog
from opaque.managers.workspace_manager import WorkspaceManager
from opaque.managers.settings_manager import SettingsManager
from opaque.managers.theme_manager import ThemeManager
from opaque.models.model import AbstractModel
from opaque.core.services import ServiceLocator, BaseService
from opaque.core.presenter import BasePresenter


class BaseApplication(QMainWindow):
    """
    The main application window that manages the MDI area, toolbar, and features.
    It handles feature registration, settings, and workspace persistence.

    Developers must implement:
    - application_name() - Returns the application name for QApplication
    - organization_name() - Returns the organization name for QApplication  
    - application_title() - Returns the main window title
    - register_features() - Registers all feature windows
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        # Set application metadata before initialization
        QApplication.setApplicationName(self.application_name())
        QApplication.setOrganizationName(self.organization_name())

        super().__init__(parent)

        # Make this window accessible to views via QApplication
        app = QApplication.instance()
        if app:
            app.main_window = self

        # Set up the main window
        self.setWindowTitle(self.application_title())
        #self.setMinimumSize(1280, 720)

        # Set the MDI area as the central widget
        self.mdi_area = OpaqueMdiArea()
        self.setCentralWidget(self.mdi_area)

        # Create and add the toolbar
        self.toolbar: OpaqueMainToolbar = OpaqueMainToolbar(self.tr("Features"), self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        self._registered_presenters: Dict[str, BasePresenter] = {}
        self._active_presenters: Dict[str, BasePresenter] = {}

        # Initialize managers with custom paths from abstract methods
        self._workspace_manager: WorkspaceManager = WorkspaceManager()
        self._settings_manager: SettingsManager = SettingsManager(self.settings_file_path())

        # Initialize service locator
        self._service_locator: ServiceLocator = ServiceLocator()

        # Initialize global settings
        self._init_global_settings()

        # --- Theme Management ---
        self.theme_manager: ThemeManager = ThemeManager(QApplication.instance())
        # Dynamically populate the theme choices
        if hasattr(self.global_settings, 'theme'):
            self.global_settings.__class__.theme.choices = self.theme_manager.list_themes()
        # Apply theme on startup
        if hasattr(self.global_settings, 'theme'):
            self.theme_manager.apply_theme(self.global_settings.theme)
            # Update toolbar highlighting to match theme
            if hasattr(self, 'toolbar'):
                self.toolbar.update_theme()
        # ----------------------

        self._setup_file_menu()

        #self.mdi_area.subWindowActivated.connect(self._on_sub_window_activated)

    #def _on_sub_window_activated(self, window: Optional[BaseView]) -> None:
    #    """
    #    Handles the activation of a subwindow to update the toolbar.
    #    """
    #    if window:
    #        feature_name = window.feature_name()
    #        self.toolbar.set_active_feature(feature_name)
    #    else:
    #        self.toolbar.clear_active_feature()

    def _init_global_settings(self) -> None:
        """Initialize global settings using the model from global_settings_model()"""
        settings_model_class = self.global_settings_model()
        if settings_model_class:
            self.global_settings = settings_model_class(feature_id='global')
            # Register and load saved settings
            self._settings_manager.register_feature_settings(
                'global', self.global_settings)

    def _setup_file_menu(self) -> None:
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu(self.tr("&File"))

        save_workspace_action = QAction(self.tr("Save Workspace"), self)
        save_workspace_action.triggered.connect(self.save_workspace)
        file_menu.addAction(save_workspace_action)

        load_workspace_action = QAction(self.tr("Load Workspace"), self)
        load_workspace_action.triggered.connect(self.load_workspace)
        file_menu.addAction(load_workspace_action)

        file_menu.addSeparator()

        settings_action = QAction(self.tr("Settings..."), self)
        settings_action.triggered.connect(self.show_settings_dialog)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        exit_action = QAction(self.tr("Exit"), self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def register_feature(self, presenter: BasePresenter) -> None:
        """
        Registers a feature using the MVP pattern.
        The presenter will be instantiated when the feature is activated.

        Args:
            presenter_class: The presenter class that will manage the feature
        """
        feature_name = presenter.model.feature_name()
        if feature_name in self._registered_presenters:
            raise ValueError(f"Feature '{feature_name}' is already registered")

        self._registered_presenters[feature_name] = presenter

        # Add toolbar button for the feature
        self.toolbar.add_feature(presenter)

        self._active_presenters[feature_name] = presenter

        self.mdi_area.addSubWindow(presenter.view)
        presenter.show_view()

        def on_view_closed():
            if feature_name in self._active_presenters:
                del self._active_presenters[feature_name]

        presenter.view.view_closed.connect(on_view_closed)

    def register_service(self, service: BaseService) -> None:
        """
        Register a service with the application's service locator.

        Args:
            name: Service identifier
            service: Service instance
        """
        self._service_locator.register_service(service)

    def get_service(self, name: str) -> Optional[BaseService]:
        """
        Get a service from the service locator.

        Args:
            name: Service identifier

        Returns:
            Service instance or None if not found
        """
        return self._service_locator.get_service(name)

    def global_settings_model(self) -> Optional[Type[AbstractModel]]:
        """
        Return the global settings model class for the application.
        Override this to provide custom global settings.

        By default, returns the framework's GlobalSettings which includes:
        - theme: Application theme selection
        - language: UI language (future)

        Example:
            return MyGlobalSettings  # Your custom global settings model
        """
        # Import here to avoid circular dependency
        from opaque.models.app_settings_model import ApplicationSettings
        return ApplicationSettings

    def show_settings_dialog(self) -> None:
        """
        Gathers all features with settings and displays the settings dialog.
        Handles theme application and saving on dialog acceptance.
        """
        # Collect settings from both legacy windows and MVP presenters
        windows_with_settings = []

        # MVP presenters - collect settings from their models
        for feature_name, presenter in self._active_presenters.items():
            if hasattr(presenter, 'model') and presenter.model:
                # Check if model has annotated settings fields
                from src.opaque.models.annotations import get_settings_fields
                settings_fields = get_settings_fields(presenter.model)
                if settings_fields:
                    # Create a wrapper for MVP model settings
                    model_wrapper = QWidget()
                    model_wrapper.setWindowTitle(feature_name)
                    setattr(model_wrapper, 'feature_id', feature_name)
                    setattr(model_wrapper, 'settings', presenter.model)
                    setattr(model_wrapper, '_is_mvp_model', True)
                    windows_with_settings.append(model_wrapper)

        # Add global settings if they exist
        dialog_list = []
        if hasattr(self, 'global_settings') and self.global_settings:
            # Create a wrapper for global settings to work with the dialog
            global_wrapper = QWidget()
            global_wrapper.setWindowTitle(self.tr('Global Settings'))
            setattr(global_wrapper, 'feature_id', 'global')
            setattr(global_wrapper, 'settings', self.global_settings)
            dialog_list.append(global_wrapper)

        # Add feature windows with settings
        dialog_list.extend(windows_with_settings)

        if not dialog_list:
            return  # No settings to show

        dialog = SettingsDialog(dialog_list, self.theme_manager, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Save global settings
            if hasattr(self, 'global_settings') and self.global_settings:
                # Only collect actual field values, not methods or Field descriptors
                settings_dict = {}
                for k in dir(self.global_settings):
                    if not k.startswith('_'):
                        value = getattr(self.global_settings, k)
                        # Skip methods and complex objects
                        if not callable(value) and not hasattr(value, '__dict__'):
                            settings_dict[k] = value
                self._settings_manager.update_feature_settings(
                    'global', settings_dict)
            # Save feature settings
            for window in windows_with_settings:
                if window.settings:
                    feature_id = getattr(
                        window, 'feature_id', window.windowTitle())
                    # Only collect actual field values, not methods or Field descriptors
                    settings_dict = {}
                    for k in dir(window.settings):
                        if not k.startswith('_'):
                            value = getattr(window.settings, k)
                            # Skip methods and complex objects
                            if not callable(value) and not hasattr(value, '__dict__'):
                                settings_dict[k] = value
                    self._settings_manager.update_feature_settings(
                        feature_id, settings_dict)
            # Apply theme if it exists in global settings
            if hasattr(self, 'global_settings') and hasattr(self.global_settings, 'theme'):
                self.theme_manager.apply_theme(self.global_settings.theme)
                # Update toolbar highlighting to match new theme
                if hasattr(self, 'toolbar'):
                    self.toolbar.update_theme()
        else:
            # On cancel, revert any changes by reloading from disk
            self._settings_manager.load_settings()
            if hasattr(self, 'global_settings') and self.global_settings:
                settings = self._settings_manager.get_feature_settings(
                    'global')
                for key, value in settings.items():
                    if hasattr(self.global_settings, key):
                        setattr(self.global_settings, key, value)
            for window in windows_with_settings:
                if window.settings:
                    feature_id = getattr(
                        window, 'feature_id', window.windowTitle())
                    settings = self._settings_manager.get_feature_settings(
                        feature_id)
                    for key, value in settings.items():
                        if hasattr(window.settings, key):
                            setattr(window.settings, key, value)

    def save_workspace(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Workspace"), "", self.tr(
                "Workspace Files (*.wks)")
        )
        if file_path:
            from pathlib import Path
            self._workspace_manager.export_workspace(Path(file_path))

    def load_workspace(self, file_path: Optional[str] = None) -> None:
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self, self.tr("Load Workspace"), "", self.tr(
                    "Workspace Files (*.wks)")
            )
        if file_path:
            from pathlib import Path
            self._workspace_manager.import_workspace(Path(file_path))

    def closeEvent(self, event: QCloseEvent):
        """Handle application close event to clean up services"""
        # Clean up all services
        self._service_locator.cleanup_all()

        # Clean up active presenters
        for presenter in self._active_presenters.values():
            presenter.cleanup()

        super().closeEvent(event)

    # --- APPLICATION API (Must be implemented by subclasses) ---

    def settings_file_path(self) -> Optional[Path]:
        """
        Return the path for the settings file.
        Override this to customize the settings file location.

        Default implementation uses: ~/.{app_name}/settings.json

        Returns:
            Path to settings file or None to use default location

        Example:
            return Path.home() / ".myapp" / "config" / "settings.json"
        """
        app_name = self.application_name().lower().replace(' ', '_')
        return Path.home() / f".{app_name}" / "settings.json"

    @abstractmethod
    def application_name(self) -> str:
        """
        Return the application name for QApplication.setApplicationName().
        This is used for settings persistence paths.

        Example: return "MyApplication"
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement application_name()")

    @abstractmethod
    def application_title(self) -> str:
        """
        Return the main window title.

        Example: return "My Application v1.0"
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement application_title()")

    @abstractmethod
    def application_description(self) -> str:
        """
        Return the main window title.

        Example: return "My Application does this and that..."
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement application_description()")

    @abstractmethod
    def application_icon(self) -> QIcon:
        """
        Return the main window Icon.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement application_icon()")

    @abstractmethod
    def organization_name(self) -> str:
        """
        Return the organization name for QApplication.setOrganizationName().
        This is used for settings persistence paths.

        Example: return "MyCompany"
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement organization_name()")
