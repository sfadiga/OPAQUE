
# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

The application shell.

BaseApplication is a QMainWindow, but it is not a view of a feature: it owns
the service registry, the feature registry, the toolbar, the MDI area, the
settings dialog and the workspace file. It used to live in opaque/view/, which
told every reader the opposite. A feature's own view is opaque.view.view.
"""


import logging
import os
from typing import Optional, Dict, List, Type, cast

from PySide6.QtWidgets import QFileDialog, QApplication, QDialog, QWidget, QMainWindow, QMessageBox
from PySide6.QtGui import (
    QAction, QIcon, QCloseEvent, QDragEnterEvent, QDropEvent, QKeySequence,
    QShowEvent,
)
from PySide6.QtCore import QLocale, Qt

from opaque.view.widgets.mdi_window import OpaqueMdiArea
from opaque.view.widgets.toolbar import OpaqueMainToolbar
from opaque.view.dialogs.settings import SettingsDialog, SettingsPage
from opaque.view.dialogs.keyboard_map import KeyboardMapDialog
from opaque.view.self_check import log_interface_problems
from opaque.features.context import FeatureContext
from opaque.models.model import BaseModel
from opaque.presenters.presenter import BasePresenter
from opaque.view.view import BaseView
from opaque.services.service import ServiceLocator
from opaque.localisation import apply_layout_direction, install_translator
from opaque.models.configuration import DefaultApplicationConfiguration

from opaque.services.single_instance_service import SingleInstanceService
from opaque.services.workspace_service import WorkspaceService
from opaque.services.theme_service import ThemeService
from opaque.services.settings_service import SettingsService, stored_language
from opaque.services.notification_service import NotificationService
from opaque.services.logger_service import LoggerService
from opaque.services.version_service import VersionManager

from opaque.presenters.app_presenter import ApplicationPresenter
from opaque.presenters.notification_presenter import (
    NOTIFICATION_SETTINGS_ID,
    NotificationPresenter,
)
from opaque.models.app_model import ApplicationModel

logger = logging.getLogger(__name__)


class BaseApplication(QMainWindow):
    """
    The main application window: the MDI area, the toolbar, the service
    registry and the feature registry.

    A subclass writes one `__init__` that calls
    `super().__init__(configuration)` and then registers its features. It
    implements nothing else; the five application accessors
    (`get_application_name`, `get_application_title`,
    `get_application_description`, `get_application_organization`,
    `get_application_icon`) are abstract on
    `DefaultApplicationConfiguration`, not on this class.

    See `examples/quickstart/main.py` for the smallest complete subclass.
    """

    def __init__(
            self,
            configuration: DefaultApplicationConfiguration,
            parent: Optional[QWidget] = None,
    ) -> None:
        # Set application metadata before initialization
        QApplication.setApplicationName(configuration.get_application_name())
        QApplication.setOrganizationName(
            configuration.get_application_organization())

        super().__init__(parent)

        # The stored language decides the locale, and it is read from the file
        # because the settings service does not exist yet.
        self._language_at_start: str = stored_language(
            configuration.get_settings_file_path())
        locale = (QLocale(self._language_at_start)
                  if self._language_at_start else QLocale.system())

        app = QApplication.instance()
        # QApplication.instance() is typed to return the base
        # QCoreApplication. This framework never runs without a real
        # QApplication, but check rather than assume it.
        if isinstance(app, QApplication):
            # The translator must be installed before any widget is built.
            # A widget reads its strings once, when it is created.
            install_translator(app, locale=locale)
            apply_layout_direction(app, locale=locale)

        # Application internal configuration, not its settings
        self._configuration = configuration

        # The one context every feature of this application receives. It is
        # built as early as possible, because the application settings
        # feature below needs it.
        self._context = FeatureContext(
            configuration=configuration, shell=self)

        # Initialize version service. This must be registered before the
        # first update_application_title() call below, because the title
        # reads the application version through this service.
        self.version_service = VersionManager()
        self.version_service.initialize()
        ServiceLocator.register_service(self.version_service)

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

        # The accessibility self check runs once, on the first show, and
        # only when OPAQUE_SELF_CHECK is set. It is a debug aid, not a
        # runtime cost every application pays.
        self._self_check_done: bool = False

        # Initialize the single instance service
        self.single_instance_service = SingleInstanceService()
        self.single_instance_service.initialize()
        ServiceLocator.register_service(self.single_instance_service)

        # Initialize workspace service
        self.workspace_service = WorkspaceService()
        self.workspace_service.initialize()
        ServiceLocator.register_service(self.workspace_service)

        # Initialize theme service. A QApplication must already exist by the
        # time BaseApplication is built (every example creates one first),
        # so this is the same instance narrowed above, not a new assumption.
        self.theme_service = ThemeService(cast(QApplication, app))
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

        # Initialize logger service. The log directory is a stored setting,
        # and the service takes it at construction, so it is read here from
        # the settings service that was created just above.
        stored_notification_settings = self.settings_service.get_all_settings(
        ).get(NOTIFICATION_SETTINGS_ID, {})
        self.logger_service = LoggerService(
            application_name=configuration.get_application_name(),
            log_directory=stored_notification_settings.get(
                "log_directory") or None)
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
        self._setup_view_menu()
        self._setup_help_menu()

    def _wire_shell_signals(self) -> None:
        """
        Connect the toolbar to the services that change what it must show.

        Every connection below goes through a lambda on purpose. A signal
        connected straight to a bound method keeps the object it saw at
        connect time, which makes the connection impossible to replace in a
        test and impossible to follow when the toolbar is rebuilt.

        These connections are made once and are never taken apart. That is a
        decision, not an oversight: features never unload at run time, and
        the shell lives as long as the process, so there is nothing to
        disconnect from and nothing to leak. `tests/test_signal_policy.py`
        keeps that assumption honest. If a way to unload a feature is ever
        added, this method needs a matching teardown, and a lambda that
        captures `self` has to be replaced first.

        A presenter is different: it connects to its own view, and its view
        can go away, so `BasePresenter.cleanup()` does disconnect.
        """
        self.theme_service.theme_changed.connect(
            lambda _name: self._repaint_after_theme_change())

        dock = self.notification_presenter.get_notification_widget()
        if dock is not None:
            # Every connection here goes through a lambda by policy (see the
            # docstring above), not because this one needs to transform its
            # argument.
            dock.visibilityChanged.connect(
                # pylint: disable-next=unnecessary-lambda
                lambda visible: self.toolbar.set_notifications_visible(visible))

        model = self.notification_presenter.get_notification_model()
        if model is not None:
            # The presenter decides what the number is, because the
            # show_notification_count setting belongs to it.
            model.notification_count_changed.connect(
                lambda count: self.toolbar.set_notification_count(
                    self.notification_presenter.displayed_count(count)))

        self.settings_service.settings_changed.connect(
            lambda feature_id, _values: self._on_settings_changed(feature_id))

    def _on_settings_changed(self, feature_id: str) -> None:
        """
        Tell one presenter that its settings changed outside the dialog.

        The settings dialog calls apply_settings() itself. This path covers
        every other writer: update_feature_settings(), reset_feature_settings()
        and import_settings(). Until now they wrote the file and the model and
        left the interface showing the old values.

        """
        if feature_id == NOTIFICATION_SETTINGS_ID:
            self.notification_presenter.apply_settings()
            return

        # One key now: the registry, the settings block and the workspace
        # block all use FEATURE_ID, so this is a lookup and not a search.
        presenter = self._registered_features.get(feature_id)
        if presenter is not None:
            presenter.apply_settings()

    def _repaint_after_theme_change(self) -> None:
        """
        Give every widget in the shell a chance to repaint after a theme change.

        A token is a string, not a live binding, so a widget that reads
        surface() in its constructor keeps that colour for ever. Such a widget
        declares apply_theme() with no arguments, and this walk calls it. The
        walk also repolishes the tree, because Qt does not always repolish a
        widget that was created before a style sheet was installed.

        One walk in the shell means a new widget needs no signal wiring of its
        own, which is what stops the next widget from being left behind.
        """
        self.toolbar.update_theme()

        style = self.style()
        for widget in self.findChildren(QWidget):
            repaint = getattr(widget, "apply_theme", None)
            if callable(repaint):
                repaint()
            style.unpolish(widget)
            style.polish(widget)

        style.unpolish(self)
        style.polish(self)
        self.update()

    def _init_application_settings(self) -> None:
        """Initialize application settings using the model from application_settings_model()"""
        model = ApplicationModel(self._context)
        # The application settings have no window of their own. They need a
        # view only because BasePresenter takes one, so this is a plain
        # BaseView that is never shown. ApplicationView was a subclass that
        # added nothing and annotated its one parameter as a string.
        view = BaseView(self._context)
        presenter = ApplicationPresenter(model, view, self._context)
        # add settings presenter directly to registered features so it is not displayed on toolbar
        self._registered_features[presenter.feature_id] = presenter
        ServiceLocator.get(SettingsService).register_model(
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
        # Not QKeySequence.StandardKey.Preferences. Qt has no standard
        # Preferences shortcut on Windows. Before Qt 6.11 it answered with
        # the multimedia key name "Settings", and from 6.11 with an empty
        # sequence, so the user never got a shortcut either way. Qt maps
        # Ctrl to Command on macOS, so this string is native everywhere.
        settings_action.setShortcut(QKeySequence(self.tr("Ctrl+,")))
        settings_action.triggered.connect(self.show_settings_dialog)
        self.file_menu.addAction(settings_action)

        self.file_menu.addSeparator()

        exit_action = QAction(self.tr("Exit"), self)
        # Not QKeySequence.StandardKey.Quit, for the same reason as Settings
        # above. Before Qt 6.11 this was the multimedia key "Exit".
        exit_action.setShortcut(QKeySequence(self.tr("Ctrl+Q")))
        exit_action.triggered.connect(self.close)
        self.file_menu.addAction(exit_action)

    def _setup_view_menu(self) -> None:
        """Build the View menu. It carries the MDI view mode."""
        self.view_menu = self.menuBar().addMenu(self.tr("&View"))

        self.tabbed_action = QAction(self.tr("Tabbed Windows"), self)
        self.tabbed_action.setCheckable(True)
        self.tabbed_action.setChecked(False)
        self.tabbed_action.setToolTip(
            self.tr("Show the feature windows as tabs"))
        self.tabbed_action.toggled.connect(self.mdi_area.set_tabbed)
        self.tabbed_action.toggled.connect(self.toolbar.set_tabbed_mode_active)
        self.view_menu.addAction(self.tabbed_action)

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

    @property
    def context(self) -> FeatureContext:
        """
        The context every feature of this application receives.

        A feature holds this instead of the whole application. See
        FeatureContext for what it offers and why.
        """
        return self._context

    def add_feature_window(self, view: QWidget) -> None:
        """
        Put one feature window into the MDI area and show it.

        FeatureContext.show_window() calls this. It is the only way a feature
        reaches the MDI area, which is why the MDI area is not on the
        context.
        """
        self.mdi_area.addSubWindow(view)
        view.show()

    def register(
            self,
            model_class: Type[BaseModel],
            view_class: Type[BaseView],
            presenter_class: Type[BasePresenter],
    ) -> BasePresenter:
        """
        Build one feature from its three classes and register it.

        This is the recipe. The three parts have to be built in this order,
        because a presenter takes a model and a view that already exist, and
        BasePresenter.__init__ reads both. Doing it by hand in the wrong
        order raised a bare AttributeError, so the framework does it.

        Args:
            model_class: The model class of the feature.
            view_class: The view class of the feature.
            presenter_class: The presenter class of the feature.

        Returns:
            The presenter that was built and registered. Keep it if the
            application needs to reach the feature later; it is also in the
            feature registry under the model's FEATURE_ID.

        Raises:
            ValueError: When the FEATURE_ID is already registered.
        """
        model = self._build_part("model", model_class, self._context)
        view = self._build_part("view", view_class, self._context)
        presenter = self._build_presenter(presenter_class, model, view)
        self.register_feature(presenter)
        return presenter

    def _build_part(self, role: str, part_class: type, context: FeatureContext):
        """
        Build a model or a view, and explain a wrong constructor.

        Args:
            role: "model" or "view", used in the message.
            part_class: The class to build.
            context: The context every part receives.
        """
        try:
            return part_class(context)
        except TypeError as error:
            raise TypeError(
                f"{part_class.__name__} cannot be built as the {role} of a "
                f"feature: {error}. A {role} takes one argument, a "
                f"FeatureContext. Write:\n"
                f"    def __init__(self, context: FeatureContext) -> None:\n"
                f"        super().__init__(context)") from error

    def _build_presenter(
            self,
            presenter_class: Type[BasePresenter],
            model: BaseModel,
            view: BaseView,
    ) -> BasePresenter:
        """Build the presenter, and explain a wrong constructor."""
        try:
            return presenter_class(model, view, self._context)
        except TypeError as error:
            raise TypeError(
                f"{presenter_class.__name__} cannot be built as the "
                f"presenter of a feature: {error}. A presenter takes three "
                f"arguments, model, view, context. Write:\n"
                f"    def __init__(self, model, view, context) -> None:\n"
                f"        super().__init__(model, view, context)") from error

    def register_feature(self, presenter: BasePresenter) -> None:
        """
        Register one built MVP triple and show its window.

        The caller builds the triple, in this order: model, then view, then
        presenter. Nothing is lazy: the presenter passed here is already
        constructed and its `bind_events()` has already run.

        Registration does four things: it adds the feature to the registry,
        registers it with the workspace service and the settings service,
        adds its toolbar button, and adds its view to the MDI area.

        Args:
            presenter: The presenter of the feature to register.

        Raises:
            ValueError: When another feature is already registered under the
                same name.
        """
        if not isinstance(presenter, BasePresenter):
            raise TypeError(
                f"register_feature takes a BasePresenter, not a "
                f"{type(presenter).__name__}. Build the feature with "
                f"self.register(ModelClass, ViewClass, PresenterClass), or "
                f"pass a presenter that extends BasePresenter.")

        feature_id = presenter.model.feature_id()
        if feature_id in self._registered_features:
            other = self._registered_features[feature_id]
            raise ValueError(
                f"The feature id '{feature_id}' is already registered by "
                f"{type(other.model).__name__}. Two features cannot share "
                f"one FEATURE_ID: it keys the registry, settings.json and "
                f"the workspace file. Give {type(presenter.model).__name__} "
                f"its own FEATURE_ID.")

        self._registered_features[feature_id] = presenter
        self.workspace_service.register_feature(presenter)
        self.settings_service.register_model(
            presenter.feature_id, presenter.model)

        # Add toolbar button for the feature
        self.toolbar.add_feature(presenter)

        # A feature window that closes is only hidden, so the feature is still
        # there. Removing it from the registry here would take away its
        # Settings page and would stop closeEvent from running its close
        # sequence via release_features(). Features are released in
        # closeEvent, never on a window close.

        self.add_feature_window(presenter.view)

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
        except Exception:  # pylint: disable=broad-exception-caught
            # An unexpected error here must not crash the shell; report it
            # and let the user try again instead.
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
        except Exception:  # pylint: disable=broad-exception-caught
            # An unexpected error here must not crash the shell; report it
            # and let the user try again instead.
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
        pages: List[SettingsPage] = list(self._registered_features.values())

        # The notification settings have a model but no BasePresenter, so the
        # presenter hands over a small adapter that carries the three members
        # the dialog reads.
        notification_page = self.notification_presenter.settings_page()
        if notification_page is not None:
            pages.append(notification_page)

        dialog = SettingsDialog(pages, parent=self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            # On cancel, revert any changes by reloading from disk
            self.settings_service.load_all_settings()

    def run_self_check(self) -> int:
        """
        Walk the widget tree and log every accessibility problem found.

        Runs only when the OPAQUE_SELF_CHECK environment variable is set to
        a non-empty value. Returns the number of problems, or -1 when the
        check is disabled.
        """
        if not os.environ.get("OPAQUE_SELF_CHECK"):
            return -1
        return log_interface_problems(self)

    def showEvent(self, event: QShowEvent) -> None:
        """Run the accessibility self check once, the first time the shell shows."""
        super().showEvent(event)
        if not self._self_check_done:
            self._self_check_done = True
            self.run_self_check()

    def release_features(self) -> None:
        """
        Run every feature's close sequence: on_view_close(), then cleanup().

        An MDI sub-window receives no closeEvent of its own when the main
        window closes, so without this call a window still open at exit
        skipped its on_view_close() hook and silently lost the state the
        hook saves. One presenter that raises must not stop the others,
        so each one is guarded.

        A hook may still talk to the shell, for example show a window; the
        window simply dies with the application.
        """
        for feature_id, presenter in list(self._registered_features.items()):
            try:
                presenter.shutdown()
            except Exception:  # pylint: disable=broad-except
                logger.exception(
                    "The feature %s failed to shut down", feature_id)

    def closeEvent(self, event: QCloseEvent):
        """
        Release the features first, then the services.

        The order matters. A presenter saves its state on the way down, and it
        asks the settings service or the workspace service to do it. Cleaning
        the services up first handed every presenter a service that had
        already released everything, so the last thing the user did was the
        most likely thing to be lost.

        One presenter that raises must not stop the others, and must not stop
        the services from being released, so each one is guarded inside
        release_features().
        """
        self.release_features()
        ServiceLocator.cleanup_services()

        super().closeEvent(event)

    def try_acquire_lock(self):
        """
        Try to acquire the single instance lock.

        The application name must be known before creating the QApplication,
        to ensure the single instance check is reliable.
        """
        return self.single_instance_service.try_acquire_lock()

    def show_already_running_message(self):
        """Show a message box informing the user that another instance is already running."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(self.tr("Application Already Running"))
        # The name goes in through a placeholder, because lupdate cannot read
        # an f-string and a translator needs to move the name in the sentence.
        msg.setText(
            self.tr("Another instance of %1 is already running.").replace(
                "%1", self._configuration.get_application_name()))
        msg.setInformativeText(
            self.tr("Use the instance that is open, or close it before you "
                    "start a new one."))
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
