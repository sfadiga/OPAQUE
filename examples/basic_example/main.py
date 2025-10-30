"""
OPAQUE Framework MVP Example
This example demonstrates the new MVP (Model-View-Presenter) pattern
along with the annotation system for settings and workspace persistence.
It also shows how to configure custom paths for settings and workspace files.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox
import sys
from pathlib import Path


from opaque.models.annotations import StringField, IntField
from opaque.view.application import BaseApplication
from opaque.models.configuration import DefaultApplicationConfiguration


class MyApplicationConfiguration(DefaultApplicationConfiguration):
    # Define fields at class level
    application_name = StringField(default="MyExampleApplication")
    application_title = StringField(default="My Example Application")
    application_description = StringField(default="My Example Application Description")
    application_icon_path = StringField(default="")
    application_version = StringField(default="0.0.1", description="Application Version")
    application_organization = StringField(default="My Company", description="Application Owner")
    application_min_width = IntField(default=1280, description="Application min width")
    application_max_width = IntField(default=1980, description="Application max width")
    application_min_height = IntField(default=720, description="Application min height")
    application_max_height = IntField(default=720, description="Application max height")
    settings_file_path = StringField(default="")  # Will be set in __init__
    workspace_file_extension = StringField(default=".wks")

    def __init__(self) -> None:
        super().__init__()

    def get_application_name(self) -> str:
        return str(self.application_name)

    def get_application_title(self) -> str:
        return str(self.application_title)

    def get_application_description(self) -> str:
        return str(self.application_description)

    def get_application_icon(self) -> QIcon:
        if self.application_icon_path:
            return QIcon(str(self.application_icon_path))
        return QIcon()

    def get_application_version(self) -> str:
        return str(self.application_version)

    def get_application_organization(self) -> str:
        return str(self.application_organization)


class MyExampleApplication(BaseApplication):
    """Example application demonstrating MVP pattern features with custom paths."""

    def __init__(self):
        self._configuration = MyApplicationConfiguration()
        super().__init__(self._configuration)
        self.register_features()

    def register_features(self):
        """Register MVP features and services."""

        # Register calculator feature using the simplified approach
        from features.calculator.model import CalculatorModel
        from features.calculator.view import CalculatorView
        from features.calculator.presenter import CalculatorPresenter
        
        # Create model and view with simplified constructors
        calc_model = CalculatorModel(self)
        calc_view = CalculatorView(self)
        calc_presenter = CalculatorPresenter(calc_model, calc_view, self)
        self.register_feature(calc_presenter)

        # Register data viewer feature
        from features.data_viewer.model import DataViewerModel
        from features.data_viewer.view import DataViewerView
        from features.data_viewer.presenter import DataViewerPresenter
        
        data_model = DataViewerModel(self)
        data_view = DataViewerView(self)
        data_presenter = DataViewerPresenter(data_model, data_view, self)
        self.register_feature(data_presenter)

        # Register logging feature
        from features.logging.model import LoggingModel
        from features.logging.view import LoggingView
        from features.logging.presenter import LoggingPresenter
        
        log_model = LoggingModel(self)
        log_view = LoggingView(self)
        log_presenter = LoggingPresenter(log_model, log_view, self)
        self.register_feature(log_presenter)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    try:
        main_window = MyExampleApplication()
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
