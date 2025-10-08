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


from typing import List, Optional, Type
from abc import abstractmethod

from PySide6.QtWidgets import QFileDialog, QApplication, QDialog, QWidget, QMainWindow, QMdiArea
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

from .base_feature_window import BaseFeatureWindow
from .main_toolbar import MainToolbar
from ..dialogs.settings_dialog import SettingsDialog
from ...persistence.managers.workspace_manager import WorkspaceManager
from ...persistence.managers.settings_manager import SettingsManager
from ...managers.theme_manager import ThemeManager
from ...models.base.base_model import BaseModel


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

        # Set up the main window
        self.setWindowTitle(self.application_title())
        self.setMinimumSize(1280, 720)

        # Set the MDI area as the central widget
        self.mdi_area: QMdiArea = QMdiArea()
        self.setCentralWidget(self.mdi_area)

        # Create and add the toolbar
        self.toolbar: MainToolbar = MainToolbar(self.tr("Features"), self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        self._registered_windows: List[BaseFeatureWindow] = []
        self._workspace_manager: WorkspaceManager = WorkspaceManager(self)

        # Initialize global settings
        self._init_global_settings()

        # --- Theme Management ---
        self.theme_manager: ThemeManager = ThemeManager(
            QApplication.instance())
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

        # Register features after initialization
        self.register_features()

    def _init_global_settings(self) -> None:
        """Initialize global settings using the model from global_settings_model()"""
        settings_model_class = self.global_settings_model()
        if settings_model_class:
            self.global_settings = settings_model_class(feature_id='global')
            # Load saved settings
            SettingsManager.instance().load_settings(self.global_settings)

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

    def register_window(self, window: BaseFeatureWindow) -> None:
        """
        Registers a feature window with the application.
        This adds it to the MDI area and creates a corresponding toolbar button.
        """
        if not window:  # isinstance(window, BaseFeatureWindow):
            raise TypeError("Window must be a subclass of BaseFeatureWindow.")

        if window in self._registered_windows:
            return

        self._registered_windows.append(window)
        self.mdi_area.addSubWindow(window)
        self.toolbar.add_feature(window)

        # Check for DEFAULT_VISIBILITY attribute or use feature_visibility method
        default_visibility = getattr(
            window, 'DEFAULT_VISIBILITY', window.feature_visibility())
        if default_visibility:
            window.show()

    def get_registered_windows(self) -> List[BaseFeatureWindow]:
        return self._registered_windows

    # --- APPLICATION API (Must be implemented by subclasses) ---

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
    def organization_name(self) -> str:
        """
        Return the organization name for QApplication.setOrganizationName().
        This is used for settings persistence paths.

        Example: return "MyCompany"
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement organization_name()")

    @abstractmethod
    def application_title(self) -> str:
        """
        Return the main window title.

        Example: return "My Application v1.0"
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement application_title()")

    @abstractmethod
    def register_features(self) -> None:
        """
        Register all feature windows for this application.
        Call self.register_window() for each feature.

        Example:
            feature1 = MyFeatureWindow(feature_id="feature1")
            self.register_window(feature1)
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement register_features()")

    def global_settings_model(self) -> Optional[Type[BaseModel]]:
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
        from ...settings.global_settings import GlobalSettings
        return GlobalSettings

    def show_settings_dialog(self) -> None:
        """
        Gathers all features with settings and displays the settings dialog.
        Handles theme application and saving on dialog acceptance.
        """
        windows_with_settings = [
            w for w in self._registered_windows if w.settings]

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
                SettingsManager.instance().save_settings(self.global_settings)
            # Save feature settings
            for window in windows_with_settings:
                if window.settings:
                    SettingsManager.instance().save_settings(window.settings)
            # Apply theme if it exists in global settings
            if hasattr(self, 'global_settings') and hasattr(self.global_settings, 'theme'):
                self.theme_manager.apply_theme(self.global_settings.theme)
                # Update toolbar highlighting to match new theme
                if hasattr(self, 'toolbar'):
                    self.toolbar.update_theme()
        else:
            # On cancel, revert any changes by reloading from disk
            if hasattr(self, 'global_settings') and self.global_settings:
                SettingsManager.instance().load_settings(self.global_settings)
            for window in windows_with_settings:
                if window.settings:
                    SettingsManager.instance().load_settings(window.settings)

    def save_workspace(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Workspace"), "", self.tr(
                "Workspace Files (*.wks)")
        )
        if file_path:
            self._workspace_manager.save_workspace(file_path)

    def load_workspace(self, file_path: Optional[str] = None) -> None:
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self, self.tr("Load Workspace"), "", self.tr(
                    "Workspace Files (*.wks)")
            )
        if file_path:
            self._workspace_manager.load_workspace(file_path)
