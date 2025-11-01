
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


from typing import Optional, Dict

from PySide6.QtWidgets import QFileDialog, QApplication, QDialog, QWidget, QMainWindow, QMessageBox
from PySide6.QtGui import QAction, QIcon, QCloseEvent, QDragEnterEvent, QDropEvent
from PySide6.QtCore import Qt

from opaque.view.widgets.mdi_window import OpaqueMdiArea
from opaque.view.widgets.toolbar import OpaqueMainToolbar
from opaque.view.dialogs.settings import SettingsDialog
from opaque.presenters.presenter import BasePresenter
from opaque.services.service import ServiceLocator
from opaque.models.configuration import DefaultApplicationConfiguration

from opaque.services.single_instance_service import SingleInstanceService
from opaque.services.workspace_service import WorkspaceService
from opaque.services.theme_service import ThemeService
from opaque.services.settings_service import SettingsService
from opaque.services.notification_service import NotificationService
from opaque.services.logger_service import LoggerService

from opaque.presenters.app_presenter import ApplicationPresenter
from opaque.presenters.notification_presenter import NotificationPresenter
from opaque.models.app_model import ApplicationModel
from opaque.view.app_view import ApplicationView


class BaseApplication(QMainWindow):
    """
    The main application window that manages the MDI area, toolbar, and features.
    It handles feature registration, settings, and workspace persistence.

    Developers must implement:
    - application_name() - Returns the application name for QApplication
    - application_title() - Returns the main window title
    - application_organization() - Returns the organization name for QApplication  
    ...
    """

    def __init__(self, configuration: DefaultApplicationConfiguration, parent: Optional[QWidget] = None) -> None:
        # Set application metadata before initialization
        QApplication.setApplicationName(configuration.get_application_name())
        QApplication.setOrganizationName(
            configuration.get_application_organization())

        super().__init__(parent)

        # Make this window accessible to views via QApplication
        app = QApplication.instance()
        if app:
            app.main_window = self  # type: ignore

        # Application internal configuration, not its settings
        self._configuration = configuration

        # Set up the main window
        self.update_application_title("")

        self.setWindowIcon(QIcon(configuration.get_application_icon()))

        # Set the MDI area as the central widget
        self.mdi_area = OpaqueMdiArea()
        self.setCentralWidget(self.mdi_area)

        # Create and add the toolbar
        self.toolbar: OpaqueMainToolbar = OpaqueMainToolbar(
            self.tr("Features"), self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        # Application minimum size
        min_size = configuration.get_application_min_size()
        if min_size and len(min_size) == 2:
            self.setMinimumSize(min_size[0], min_size[1])

        # Application maximum size
        max_size = configuration.get_application_max_size()
        if max_size and len(max_size) == 2:
            self.setMinimumSize(max_size[0], max_size[1])

        # features to be loaded with application
        self._registered_features: Dict[str, BasePresenter] = {}

        # Initialize single instead service
        self.single_instance_service = SingleInstanceService()
        self.single_instance_service.initialize()
        ServiceLocator.register_service(self.single_instance_service)

        # Initialize workspace service
        self.workspace_service = WorkspaceService()
        self.workspace_service.initialize()
        ServiceLocator.register_service(self.workspace_service)

        # Initialize theme service
        self.theme_service = ThemeService(app)
        self.theme_service.initialize()
        ServiceLocator.register_service(self.theme_service)

        # Initialize settings service
        self.settings_service = SettingsService(
            configuration.get_settings_file_path())
        self.settings_service.initialize()
        ServiceLocator.register_service(self.settings_service)

        # Initialize notification service
        self.notification_service = NotificationService()
        self.notification_service.initialize()
        ServiceLocator.register_service(self.notification_service)

        # Initialize logger service
        self.logger_service = LoggerService(
            application_name=configuration.get_application_name())
        self.logger_service.initialize()
        ServiceLocator.register_service(self.logger_service)

        # Initialize notification presenter (integrates notification system with UI)
        # Store services as instance variables to prevent garbage collection
        self._services_initialized = True
        self.notification_presenter = NotificationPresenter(self)
        self.notification_presenter.initialize()

        # Initialize application settings
        self._init_application_settings()

        self._setup_file_menu()

    def _init_application_settings(self) -> None:
        """Initialize application settings using the model from application_settings_model()"""
        model = ApplicationModel(self)
        view = ApplicationView(self)  # dummy only for settings
        presenter = ApplicationPresenter(model, view, self)
        # add settings presenter directly to registered features so it is not displayed on toolbar
        self._registered_features[presenter.feature_id] = presenter
        settings_service = ServiceLocator.get_service("settings")
        if isinstance(settings_service, SettingsService):
            settings_service.register_model(
                presenter.feature_id, presenter.model)

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

    def update_application_title(self, workspace: Optional[str]):
        self.setWindowTitle(
            f"{self._configuration.get_application_title()} {self._configuration.get_application_version()} [{workspace}]")

    def register_feature(self, presenter: BasePresenter) -> None:
        """
        Registers a feature using the MVP pattern.
        The presenter will be instantiated when the feature is activated.

        Args:
            presenter_class: The presenter class that will manage the feature
        """
        feature_name = presenter.model.feature_name()
        if feature_name in self._registered_features:
            raise ValueError(f"Feature '{feature_name}' is already registered")

        self._registered_features[feature_name] = presenter
        self.workspace_service.register_feature(presenter)
        self.settings_service.register_model(
            presenter.feature_id, presenter.model)

        # Add toolbar button for the feature
        self.toolbar.add_feature(presenter)

        def on_view_closed():
            if feature_name in self._registered_features:
                del self._registered_features[feature_name]
        presenter.view.window_closed.connect(on_view_closed)

        self.mdi_area.addSubWindow(presenter.view)
        presenter.view.show()

    def save_workspace(self) -> None:
        try:
            description = self.tr("Application Workspace")
            extension = self._configuration.get_workspace_file_extension()
            file_path, _ = QFileDialog.getSaveFileName(
                self, self.tr("Save Workspace"), "", self.tr(
                    f"{description} (*{extension})")
            )
            if file_path:
                name = self.workspace_service.save_workspace(file_path)
                self.update_application_title(name)
        except Exception as e:
            print(e)
            QMessageBox.critical(self, self.tr("Error Saving Workspace"), self.tr(
                f"An error happened while saving workspace file. Details {e}"))

    def load_workspace(self, file_path: Optional[str] = None) -> None:
        try:
            description = self.tr("Application Workspace")
            extension = self._configuration.get_workspace_file_extension()

            file_path, _ = QFileDialog.getOpenFileName(
                self, self.tr("Load Workspace"), "", self.tr(
                    f"{description} (*{extension})")
            )
            if file_path:
                name = self.workspace_service.load_workspace(file_path)
                self.update_application_title(name)
        except Exception as e:
            print(e)
            QMessageBox.critical(self, self.tr("Error Loading Workspace"), self.tr(
                f"An error happened while loading workspace file. Details {e}"))

    def show_settings_dialog(self) -> None:
        """
        Gathers all features with settings and displays the settings dialog.
        Handles theme application and saving on dialog acceptance.
        """
        dialog = SettingsDialog(
            list(self._registered_features.values()), parent=self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            # On cancel, revert any changes by reloading from disk
            self.settings_service.load_all_settings()

    def closeEvent(self, event: QCloseEvent):
        """Handle application close event to clean up services"""
        # Clean up all services
        ServiceLocator.cleanup_services()

        # Clean up active presenters
        for presenter in self._registered_features.values():
            presenter.cleanup()

        super().closeEvent(event)

    def try_acquire_lock(self):
        # The application name must be known before creating the QApplication
        # to ensure the single instance check is reliable.
        return self.single_instance_service.try_acquire_lock()

    def show_already_running_message(self):
        """Show a message box informing the user that another instance is already running."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Application Already Running")
        msg.setText(
            f"Another instance of {self._configuration.get_application_name()} is already running.")
        msg.setInformativeText(
            "Please use the existing instance or close it before starting a new one.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setWindowFlags(Qt.WindowType.SplashScreen |
                           Qt.WindowType.WindowStaysOnTopHint)
        msg.exec()

    def dragEnterEvent(self, event: QDragEnterEvent):
        """
        Handle drag enter events to accept .lab files.
        """
        try:
            if event.mimeData().hasUrls():
                urls = event.mimeData().urls()
                if len(urls) == 1:  # Only accept single file
                    file_path = urls[0].toLocalFile()
                    if file_path.lower().endswith('.lab'):
                        event.acceptProposedAction()
                        return
        except Exception as e:
            print(e)
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        """
        Handle drop events to load .lab workspace files.
        """
        try:
            if event.mimeData().hasUrls():
                urls = event.mimeData().urls()
                if len(urls) == 1:  # Only handle single file
                    file_path = urls[0].toLocalFile()
                    if file_path.lower().endswith('.lab'):
                        if self.workspace_service:
                            name = self.workspace_service.load_workspace(
                                file_path)
                            self.update_application_title(name)
                        event.acceptProposedAction()
                        return
        except Exception as e:
            print(e)
        event.ignore()
