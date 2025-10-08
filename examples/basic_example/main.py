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

import sys
import os
# Add the src directory to the path so we can import the framework
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTranslator, QLocale

from opaque import BaseApplication
from features.data_analysis.window import DataAnalysisWindow
from features.logging.window import LoggingWindow

# @brief Example application demonstrating the OPAQUE Framework.
#
# This class extends BaseApplication to create a concrete application
# with specific feature windows for data analysis and logging.


class ExampleApplication(BaseApplication):
    """
    # Main entry point for the OPAQUE Framework example application.
    #
    # This module demonstrates how to use the OPAQUE Framework to create
    # a multi-window MDI application with features like data analysis
    # and logging windows.

    The framework automatically handles:
    - Setting QApplication name and organization
    - Setting the window title
    - Registering features after initialization
    """

    def application_name(self) -> str:
        """Return the application name for settings persistence."""
        return "OPAQUEExample"
    
    def organization_name(self) -> str:
        """Return the organization name for settings persistence."""
        return "MyCompany"
    
    def application_title(self) -> str:
        """Return the main window title."""
        return self.tr("OPAQUE Framework - Example")
    
    def register_features(self) -> None:
        """
        Register all feature windows for this application.
        The framework automatically handles adding them to the UI.
        """
        # --- Data Analysis Feature ---
        data_analysis_window = DataAnalysisWindow(feature_id="data_analysis_1")
        self.register_window(data_analysis_window)

        # --- Logging Feature ---
        logging_window = LoggingWindow(feature_id="logging_1")
        self.register_window(logging_window)


# @brief Main entry point of the application.
#
# Sets up the Qt application, configures internationalization,
# creates the main window, and handles command-line arguments
# for opening workspace files.
if __name__ == "__main__":
    # @brief Qt application instance
    # Note: The framework automatically sets application name and organization
    # from the ExampleApplication.application_name() and organization_name() methods
    app: QApplication = QApplication(sys.argv)

    # --- Internationalization Setup ---
    # 1. Create a translator object
    # @brief Translator for internationalization support
    translator: QTranslator = QTranslator()

    # 2. Determine the system's locale
    # @brief System locale string (e.g., "en_US", "de_DE")
    system_locale: str = QLocale.system().name()

    # 3. Load the translation file
    # This assumes you will have a 'translations' directory next to your 'src' dir.
    # The files should be named e.g., app_de.qm, app_fr.qm
    if translator.load(f"translations/app_{system_locale}.qm"):
        # 4. Install the translator
        app.installTranslator(translator)
    # ----------------------------------

    # @brief Main application window instance
    main_win: ExampleApplication = ExampleApplication()
    main_win.show()

    # --- Handle file open from command line ---
    # Check if a workspace file was provided as command-line argument
    if len(sys.argv) > 1:
        # @brief Path to workspace file from command-line argument
        file_path: str = sys.argv[1]
        if file_path.endswith(".wks"):
            main_win.load_workspace(file_path)
    # ------------------------------------------

    # Start the Qt event loop
    sys.exit(app.exec())
