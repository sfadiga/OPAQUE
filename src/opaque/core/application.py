
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


from typing import Optional, Type, Dict
from abc import abstractmethod
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QApplication, QDialog, QWidget, QMainWindow, QMessageBox
from PySide6.QtGui import QAction, QIcon, QCloseEvent
from PySide6.QtCore import Qt

from opaque.widgets.mdi_window import OpaqueMdiArea
from opaque.core.view import BaseView
from opaque.widgets.toolbar import OpaqueMainToolbar
from opaque.widgets.dialogs.settings import SettingsDialog
from opaque.managers.workspace_manager import WorkspaceManager
from opaque.managers.settings_manager import SettingsManager
from opaque.managers.theme_manager import ThemeManager
from opaque.managers.single_instance_manager import SingleInstanceManager
from opaque.models.application_model import ApplicationModel
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
        self.setWindowIcon(self.application_icon())
        # self.setMinimumSize(1280, 720) # TODO make this an application settigns ?

        # Set the MDI area as the central widget
        self.mdi_area = OpaqueMdiArea()
        self.setCentralWidget(self.mdi_area)

        # Create and add the toolbar
        self.toolbar: OpaqueMainToolbar = OpaqueMainToolbar(
            self.tr("Features"), self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        self._registered_presenters: Dict[str, BasePresenter] = {}
        self._active_presenters: Dict[str, BasePresenter] = {}

        # Initialize managers with custom paths from abstract methods
        self._workspace_manager: WorkspaceManager = WorkspaceManager()
        self._settings_manager: SettingsManager = SettingsManager(
            self.settings_file_path())

        # Initialize service locator
        self._service_locator: ServiceLocator = ServiceLocator()

        # Initialize application settings
        self._init_application_settings()

        # --- Theme Management ---
        self.theme_manager: ThemeManager = ThemeManager(QApplication.instance())
        # Dynamically populate the theme choices
        if hasattr(self.application_settings, 'theme'):
            theme_field = self.application_settings.get_fields().get('theme')
            if theme_field:
                theme_field.choices = self.theme_manager.list_themes()
        # Apply theme on startup
        if hasattr(self.application_settings, 'theme'):
            self.theme_manager.apply_theme(
                str(self.application_settings.theme))
            # Update toolbar highlighting to match theme
            if hasattr(self, 'toolbar'):
                self.toolbar.update_theme()
        # ----------------------

        self._setup_file_menu()

    def _init_application_settings(self) -> None:
        """Initialize application settings using the model from application_settings_model()"""
        settings_model_class = self.application_settings_model()
        if settings_model_class:
            self.application_settings = settings_model_class()
            # Register and load saved settings
            self._settings_manager.register_model(
                'application', self.application_settings)

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

    def application_settings_model(self) -> Type[ApplicationModel]:
        """
        Return the application settings model class for the application.
        Override this to provide a custom application settings model that
        inherits from ApplicationModel.

        Example:
            return MyAppSettingsModel
        """
        return ApplicationModel

    def show_settings_dialog(self) -> None:
        """
        Gathers all features with settings and displays the settings dialog.
        Handles theme application and saving on dialog acceptance.
        """
        # Collect all active presenters' views
        views_with_settings = [
            presenter.view for presenter in self._active_presenters.values()
        ]

        # Add application settings if they exist
        if hasattr(self, 'application_settings') and self.application_settings:
            # Create a dummy view for application settings
            class AppSettingsView(BaseView):
                def set_model(self, model):
                    self._model = model
            app_settings_view = AppSettingsView("application")
            app_settings_view.set_model(self.application_settings)
            views_with_settings.insert(0, app_settings_view)

        if not views_with_settings:
            return  # No settings to show

        dialog = SettingsDialog(
            views_with_settings, self._settings_manager, self.theme_manager, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Apply theme if it exists in application settings
            if hasattr(self, 'application_settings') and hasattr(self.application_settings, 'theme'):
                self.theme_manager.apply_theme(
                    str(self.application_settings.theme))
                if hasattr(self, 'toolbar'):
                    self.toolbar.update_theme()
        else:
            # On cancel, revert any changes by reloading from disk
            self._settings_manager.load_all_settings()

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


    def try_acquire_lock(self):
        # The application name must be known before creating the QApplication
        # to ensure the single instance check is reliable.
        instance_manager = SingleInstanceManager(app_name=self.application_name(), port=49153)
        return instance_manager.try_acquire_lock()

    def show_already_running_message(self):
        """Show a message box informing the user that another instance is already running."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Application Already Running")
        msg.setText(f"Another instance of {self.application_name()} is already running.")
        msg.setInformativeText("Please use the existing instance or close it before starting a new one.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.WindowStaysOnTopHint)
        msg.exec()
