"""
OPAQUE Framework MVP Example
This example demonstrates the new MVP (Model-View-Presenter) pattern
along with the annotation system for settings and workspace persistence.
It also shows how to configure custom paths for settings and workspace files.
"""
from opaque.core.application import BaseApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'src'))


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
        return QIcon.fromTheme("drive-optical")

    def settings_file_path(self) -> Path:
        """
        Override to use a custom settings path.
        This example stores settings in a 'mvp_example' subfolder.
        """
        return Path.home() / ".opaque" / "mvp_example" / "settings.json"

    def __init__(self):
        super().__init__()
        self.register_features()

    def register_features(self):
        """Register MVP features and services."""

        # Register services first
        from services.calculation_service import CalculationService
        from services.logging_service import LoggingService
        from services.data_service import DataService
        logging_service = LoggingService()
        logging_service.initialize()
        self.register_service(logging_service)
        data_service = DataService()
        data_service.initialize()
        self.register_service(data_service)
        calc_service = CalculationService()
        calc_service.initialize()
        self.register_service(calc_service)

        # Register MVP features
        from features.calculator.model import CalculatorModel
        from features.calculator.view import CalculatorView
        from features.calculator.presenter import CalculatorPresenter
        calc_feature_id = "calculator"
        calc_model = CalculatorModel(calc_feature_id)
        calc_view = CalculatorView(calc_feature_id)
        calc_presenter = CalculatorPresenter(
            calc_feature_id, calc_model, calc_view, self)
        self.register_feature(calc_presenter)

        from features.logging.model import LoggingModel
        from features.logging.view import LoggingView
        from features.logging.presenter import LoggingPresenter
        log_feature_id = "logging"
        log_model = LoggingModel(log_feature_id)
        log_view = LoggingView(log_feature_id)
        log_presenter = LoggingPresenter(log_feature_id, log_model, log_view, self)
        self.register_feature(log_presenter)

        from features.data_viewer.model import DataViewerModel
        from features.data_viewer.view import DataViewerView
        from features.data_viewer.presenter import DataViewerPresenter
        data_feature_id = "data"
        data_model = DataViewerModel(data_feature_id)
        data_view = DataViewerView(data_feature_id)
        data_presenter = DataViewerPresenter(data_feature_id, data_model, data_view, self)
        self.register_feature(data_presenter)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    try:
        main_window = MVPExampleApplication()
        if not main_window.try_acquire_lock():
            main_window.show_already_running_message()
            sys.exit(1)
        main_window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
