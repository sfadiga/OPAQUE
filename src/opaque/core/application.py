
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


from typing import Optional, Type, Dict, cast
from abc import abstractmethod
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QApplication, QDialog, QWidget, QMainWindow, QMessageBox
from PySide6.QtGui import QAction, QIcon, QCloseEvent
from PySide6.QtCore import Qt, QByteArray

from opaque.widgets.mdi_window import OpaqueMdiArea
from opaque.widgets.toolbar import OpaqueMainToolbar
from opaque.widgets.dialogs.settings import SettingsDialog
from opaque.managers.theme_manager import ThemeManager
from opaque.managers.single_instance_manager import SingleInstanceManager
from opaque.services import SettingsService, WorkspaceService
from opaque.core.services import ServiceLocator, BaseService
from opaque.core.presenter import BasePresenter

from opaque.core.application_settings.presenter import ApplicationPresenter

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
            app.main_window = self  # type: ignore

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

        # Initialize service locator and services
        self._service_locator: ServiceLocator = ServiceLocator()
        self._init_services()

        q_app = QApplication.instance()
        if not isinstance(q_app, QApplication):
            raise RuntimeError("QApplication not initialized")
        self.theme_manager: ThemeManager = ThemeManager(q_app)

        # app settings
        self.app_settings_presenter = None

        # Initialize application settings
        self._init_application_settings()

        self._setup_file_menu()

        # Restore workspace
        self._restore_workspace()

    def _init_services(self) -> None:
        """Initialize and register core services."""
        settings_service = SettingsService(self.settings_file_path())
        settings_service.initialize()
        self.register_service(settings_service)

        workspace_service = WorkspaceService()
        workspace_service.initialize()
        self.register_service(workspace_service)

    def _init_application_settings(self) -> None:
        """Initialize application settings using the model from application_settings_model()"""
        presenter = self.get_app_settings_presenter()
        # an oversimplification for adding application to the settings dialog
        self._active_presenters[presenter.feature_id] = presenter
        # Register and load saved settings
        settings_service: SettingsService = self._service_locator.get_service("settings")
        if settings_service:
            settings_service.manager.register_model(presenter.feature_id, presenter.model)

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

        # Register the model with the settings manager
        settings_service = cast(SettingsService, self._service_locator.get_service("settings"))
        if settings_service:
            settings_service.manager.register_model(presenter.feature_id, presenter.model)

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

    def get_app_settings_presenter(self) -> ApplicationPresenter:
        """
        Return the application settings presenter class for the application.
        Override this to provide a custom application settings presenter that
        inherits from ApplicationPresenter.

        Example:
            return ApplicationPresenter
        """
        from opaque.core.application_settings.model import ApplicationModel
        from opaque.core.application_settings.view import ApplicationView
        feature_id = "application"
        model = ApplicationModel(feature_id)
        view = ApplicationView(feature_id)
        self.app_settings_presenter = ApplicationPresenter(feature_id, model, view, self)
        return self.app_settings_presenter

    def show_settings_dialog(self) -> None:
        """
        Gathers all features with settings and displays the settings dialog.
        Handles theme application and saving on dialog acceptance.
        """
        settings_service = cast(SettingsService, self._service_locator.get_service("settings"))
        if not settings_service:
            return

        dialog = SettingsDialog(list(self._active_presenters.values()), parent=self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            # On cancel, revert any changes by reloading from disk
            settings_service.manager.load_all_settings()

    def save_workspace(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Workspace"), "", self.tr(
                "Workspace Files (*.wks)")
        )
        if file_path:
            workspace_service = cast(WorkspaceService, self._service_locator.get_service("workspace"))
            if workspace_service:
                workspace_service.manager.export_workspace(Path(file_path))

    def load_workspace(self, file_path: Optional[str] = None) -> None:
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self, self.tr("Load Workspace"), "", self.tr(
                    "Workspace Files (*.wks)")
            )
        if file_path:
            workspace_service = cast(WorkspaceService, self._service_locator.get_service("workspace"))
            if workspace_service:
                workspace_service.manager.import_workspace(Path(file_path))

    def _save_workspace_state(self) -> None:
        """Save the current workspace state."""
        workspace_service = cast(WorkspaceService, self._service_locator.get_service("workspace"))
        if not workspace_service:
            return

        # Save main window state
        workspace_service.manager.save_window_state(
            "main_window",
            self.saveGeometry().toBase64(),
            self.saveState().toBase64()
        )

        # Save open features
        open_features = [p.feature_id for p in self._active_presenters.values()]
        workspace_service.manager.save_open_features(open_features)

        # Save window states
        for presenter in self._active_presenters.values():
            workspace_service.manager.save_window_state(
                presenter.feature_id,
                presenter.view.saveGeometry(),
                QByteArray()
            )

    def _restore_workspace(self) -> None:
        """Restore the workspace state."""
        workspace_service = cast(WorkspaceService, self._service_locator.get_service("workspace"))
        if not workspace_service:
            return

        # Restore main window state
        geometry, state = workspace_service.manager.get_window_state("main_window")
        if geometry:
            self.restoreGeometry(QByteArray.fromBase64(geometry))
        if state:
            self.restoreState(QByteArray.fromBase64(state))

        # Restore open features
        open_features = workspace_service.manager.get_open_features()
        for feature_id in open_features:
            # This assumes presenters are already registered
            presenter = self._registered_presenters.get(feature_id)
            if presenter and feature_id not in self._active_presenters:
                self.register_feature(presenter)

        # Restore window states
        for presenter in self._active_presenters.values():
            geometry, _ = workspace_service.manager.get_window_state(presenter.feature_id)
            if geometry:
                presenter.view.restoreGeometry(geometry)

    def closeEvent(self, event: QCloseEvent):
        """Handle application close event to clean up services"""
        self._save_workspace_state()

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
