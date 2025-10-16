"""
OPAQUE Framework MVP Example
This example demonstrates the new MVP (Model-View-Presenter) pattern
along with the annotation system for settings and workspace persistence.
It also shows how to configure custom paths for settings and workspace files.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon


from services.calculation_service import CalculationService
#from services.logging_service import LoggingService
#from features.data_viewer.presenter import DataViewerPresenter
from features.calculator.presenter import CalculatorPresenter
from features.calculator.model import CalculatorModel
from features.calculator.view import CalculatorView

from opaque.core.application import BaseApplication


# Import our MVP feature components

# Import example services


class MVPExampleApplication(BaseApplication):
    """Example application demonstrating MVP pattern features with custom paths."""

    def application_name(self) -> str:
        return "MVPExample"

    def organization_name(self) -> str:
        return "OPAQUEFramework"

    def application_title(self) -> str:
        return "OPAQUE MVP Pattern Example"

    def application_description(self) -> str:
        return "An example application demonstrating the MVP pattern."

    def application_icon(self) -> QIcon:
        return QIcon.fromTheme("document")

    def settings_file_path(self) -> Path:
        """
        Override to use a custom settings path.
        This example stores settings in a 'mvp_example' subfolder.
        """
        return Path.home() / ".opaque" / "mvp_example" / "settings.json"

    def register_features(self):
        """Register MVP features and services."""

        # Register services first
        #self.register_service("logging", LoggingService())
        service = CalculationService()
        service.initialize()
        self.register_service(service)

        # Register MVP features
        model = CalculatorModel()
        view = CalculatorView()
        presenter = CalculatorPresenter(model, view)
        self.register_feature(presenter)
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        main_window = MVPExampleApplication()
        main_window.register_features()
        main_window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
