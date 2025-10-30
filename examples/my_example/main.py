"""
OPAQUE Framework MVP Example
This example demonstrates the new MVP (Model-View-Presenter) pattern
along with the annotation system for settings and workspace persistence.
It also shows how to configure custom paths for settings and workspace files.
"""
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from opaque.models.annotations import StringField, IntField
from opaque.view.application import BaseApplication
from opaque.models.configuration import DefaultApplicationConfiguration


class MyApplicationConfiguration(DefaultApplicationConfiguration):

    def __init__(self) -> None:
        super().__init__()

    def get_application_name(self) -> str:
        return "MyExampleApplication"

    def get_application_title(self) -> str:
        return "My Example Application"

    def get_application_description(self) -> str:
        return "My Example Application Description"

    def get_application_icon(self) -> QIcon:
        return QIcon.fromTheme(QIcon.ThemeIcon.AddressBookNew)

    def get_application_organization(self) -> str:
        return "My Company"

    def get_application_version(self) -> str:
        return "0.0.1"

class MyExampleApplication(BaseApplication):
    """Example application demonstrating MVP pattern features with custom paths."""

    def __init__(self):

        self._configuration = MyApplicationConfiguration()
        super().__init__(self._configuration)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    try:
        main_window = MyExampleApplication()

        # Register MVP features
        from features.todo_list.model import TodoListModel
        from features.todo_list.view import TodoListView
        from features.todo_list.presenter import TodoListPresenter

        # Simplified constructor calls - no need for manual feature_id management
        todo_model = TodoListModel(main_window)
        todo_view = TodoListView(main_window)
        todo_presenter = TodoListPresenter(todo_model, todo_view, main_window)
        main_window.register_feature(todo_presenter)

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
