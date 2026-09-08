
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


import logging
from typing import Optional, Dict

from PySide6.QtWidgets import QFileDialog, QApplication, QDialog, QWidget, QMainWindow, QMessageBox
from PySide6.QtGui import (
    QAction, QIcon, QCloseEvent, QDragEnterEvent, QDropEvent, QKeySequence,
)
from PySide6.QtCore import Qt

from opaque.view.widgets.mdi_window import OpaqueMdiArea
from opaque.view.widgets.toolbar import OpaqueMainToolbar
from opaque.view.dialogs.settings import SettingsDialog
from opaque.view.dialogs.keyboard_map import KeyboardMapDialog
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

logger = logging.getLogger(__name__)


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
        self.update_application_title(None)

        self.setWindowIcon(QIcon(configuration.get_application_icon()))

        # Set the MDI area as the central widget
        self.mdi_area = OpaqueMdiArea()
        self.setCentralWidget(self.mdi_area)

        # Create and add the toolbar
        self.toolbar: OpaqueMainToolbar = OpaqueMainToolbar(
            self.tr("Features"), self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        self.apply_size_limits(
            self,
            configuration.get_application_min_size(),
            configuration.get_application_max_size(),
        )

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
        
        # Add notification toggle to toolbar
        self.toolbar.add_notification_button(
            self.notification_presenter.toggle_notifications)

        # The wiring must come after the notification button exists, because
        # set_notifications_visible and set_notification_count act on it.
        self._wire_shell_signals()

        # Initialize application settings
        self._init_application_settings()

        self._setup_file_menu()
        self._setup_help_menu()

    def _wire_shell_signals(self) -> None:
        """
        Connect the toolbar to the services that change what it must show.

        Every connection below goes through a lambda on purpose. A signal
        connected straight to a bound method keeps the object it saw at
        connect time, which makes the connection impossible to replace in a
        test and impossible to follow when the toolbar is rebuilt.
        """
        self.theme_service.theme_changed.connect(
            lambda _name: self.toolbar.update_theme())

        dock = self.notification_presenter.get_notification_widget()
        if dock is not None:
            dock.visibilityChanged.connect(
                lambda visible: self.toolbar.set_notifications_visible(visible))

        model = self.notification_presenter.get_notification_model()
        if model is not None:
            model.notification_count_changed.connect(
                lambda count: self.toolbar.set_notification_count(count))

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
        """Build the File menu. Every action carries a keyboard shortcut."""
        menu_bar = self.menuBar()
        self.file_menu = menu_bar.addMenu(self.tr("&File"))

        save_workspace_action = QAction(self.tr("Save Workspace"), self)
        save_workspace_action.setShortcut(QKeySequence.StandardKey.Save)
        save_workspace_action.triggered.connect(self.save_workspace)
        self.file_menu.addAction(save_workspace_action)

        load_workspace_action = QAction(self.tr("Load Workspace"), self)
        load_workspace_action.setShortcut(QKeySequence.StandardKey.Open)
        load_workspace_action.triggered.connect(self.load_workspace)
        self.file_menu.addAction(load_workspace_action)

        self.file_menu.addSeparator()

        settings_action = QAction(self.tr("Settings..."), self)
        settings_action.setShortcut(QKeySequence.StandardKey.Preferences)
        settings_action.triggered.connect(self.show_settings_dialog)
        self.file_menu.addAction(settings_action)

        self.file_menu.addSeparator()

        exit_action = QAction(self.tr("Exit"), self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        self.file_menu.addAction(exit_action)

    def _setup_help_menu(self) -> None:
        """Build the Help menu. F1 opens the keyboard map."""
        self.help_menu = self.menuBar().addMenu(self.tr("&Help"))

        keyboard_map_action = QAction(self.tr("Keyboard Shortcuts"), self)
        keyboard_map_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        keyboard_map_action.triggered.connect(self.show_keyboard_map)
        self.help_menu.addAction(keyboard_map_action)

    def build_keyboard_map_dialog(self) -> KeyboardMapDialog:
        """Build the keyboard map dialog for this window."""
        return KeyboardMapDialog(self, parent=self)

    def show_keyboard_map(self) -> None:
        """Show every keyboard shortcut this application answers to."""
        self.build_keyboard_map_dialog().exec()

    @staticmethod
    def build_window_title(
        title: str,
        version: str,
        workspace: Optional[str],
    ) -> str:
        """
        Build the text of the window title bar.

        Args:
            title: The application title.
            version: The application version.
            workspace: The open workspace name, or None when none is open.

        Returns:
            The title. An empty or missing workspace leaves no bracket pair
            behind, because an empty pair of brackets tells the user nothing.
        """
        base = f"{title} {version}".strip()
        if workspace:
            return f"{base} [{workspace}]"
        return base

    @staticmethod
    def apply_size_limits(window: QWidget, min_size, max_size) -> None:
        """
        Apply the configured size limits to a window.

        Args:
            window: The window to limit.
            min_size: A width and height pair, or None.
            max_size: A width and height pair, or None.
        """
        if min_size and len(min_size) == 2:
            window.setMinimumSize(min_size[0], min_size[1])
        if max_size and len(max_size) == 2:
            window.setMaximumSize(max_size[0], max_size[1])

    def update_application_title(self, workspace: Optional[str]) -> None:
        """Put the application name, the version and the workspace in the title."""
        self.setWindowTitle(self.build_window_title(
            self._configuration.get_application_title(),
            self._configuration.get_application_version(),
            workspace,
        ))

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

        # A feature window that closes is only hidden, so the feature is still
        # there. Removing it from the registry here would take away its
        # Settings page and would stop closeEvent from calling its cleanup().
        # Features are released in closeEvent, never on a window close.

        self.mdi_area.addSubWindow(presenter.view)
        presenter.view.show()

    def _ask_for_workspace_path(self, for_load: bool) -> str:
        """
        Ask the user for a workspace file path.

        Args:
            for_load: True to open an existing file, False to save a new one.

        Returns:
            The chosen path, or an empty string when the user cancelled.
        """
        description = self.tr("Application Workspace")
        extension = self._configuration.get_workspace_file_extension()
        file_filter = f"{description} (*{extension})"

        if for_load:
            path, _ = QFileDialog.getOpenFileName(
                self, self.tr("Load Workspace"), "", file_filter)
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, self.tr("Save Workspace"), "", file_filter)
        return path

    def save_workspace(self, file_path: Optional[str] = None) -> None:
        """
        Save the workspace.

        Args:
            file_path: Where to save. When empty, the user is asked.
        """
        if not file_path:
            file_path = self._ask_for_workspace_path(for_load=False)
        if not file_path:
            return

        try:
            name = self.workspace_service.save_workspace(file_path)
            self.update_application_title(name)
        except Exception:
            logger.exception("Failed to save the workspace file")
            QMessageBox.critical(
                self,
                self.tr("Error Saving Workspace"),
                self.tr("The workspace file could not be saved. "
                        "See the log for details."),
            )

    def load_workspace(self, file_path: Optional[str] = None) -> None:
        """
        Load a workspace.

        Args:
            file_path: The workspace file to load. When empty, the user is
                asked. The old code asked always and then wrote the answer
                over this argument, so a drop or a command line argument
                could never work.
        """
        if not file_path:
            file_path = self._ask_for_workspace_path(for_load=True)
        if not file_path:
            return

        try:
            name = self.workspace_service.load_workspace(file_path)
            self.update_application_title(name)
        except Exception:
            logger.exception("Failed to load the workspace file")
            QMessageBox.critical(
                self,
                self.tr("Error Loading Workspace"),
                self.tr("The workspace file could not be loaded. "
                        "See the log for details."),
            )

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

    @staticmethod
    def workspace_path_from_urls(urls, extension: str) -> Optional[str]:
        """
        Return the single dropped workspace file path, or None.

        Args:
            urls: The QUrl list carried by the drag or the drop event.
            extension: The configured workspace extension, for example ".wks".

        Returns:
            The local file path, when exactly one file is offered and it has
            the configured extension. None in every other case.
        """
        if len(urls) != 1:
            return None

        path = urls[0].toLocalFile()
        if not path:
            return None

        if not path.lower().endswith(extension.lower()):
            return None

        return path

    def _dropped_workspace_path(self, event) -> Optional[str]:
        """Return the workspace file this event carries, or None."""
        if not event.mimeData().hasUrls():
            return None
        return self.workspace_path_from_urls(
            event.mimeData().urls(),
            self._configuration.get_workspace_file_extension(),
        )

    def dragEnterEvent(self, event: QDragEnterEvent):
        """
        Accept a drag that carries one workspace file.

        The extension comes from the configuration. The old code compared
        against a hardcoded extension that no configuration in this
        framework ever uses.
        """
        if self._dropped_workspace_path(event):
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Load the workspace file this drop carries."""
        file_path = self._dropped_workspace_path(event)
        if not file_path:
            event.ignore()
            return

        event.acceptProposedAction()
        self.load_workspace(file_path)
