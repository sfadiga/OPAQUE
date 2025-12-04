# This Python file uses the following encoding: utf-8
from typing import Any
from opaque.view.application import BaseApplication
from opaque.presenters.presenter import BasePresenter
from .model import TabManagerModel
from .view import TabManagerView, TextWidget, CounterWidget, ListWidget


class TabManagerPresenter(BasePresenter):
    def __init__(self, model: TabManagerModel, view: TabManagerView, app: BaseApplication):
        super().__init__(model, view, app)
        
        # Connect signals
        self.view.tab_widget.tabAdded.connect(self._on_tab_added)
        self.view.tab_widget.tabRemoved.connect(self._on_tab_removed)
        self.view.tab_widget.currentTabChanged.connect(self._on_tab_changed)

    def bind_events(self) -> None:
        pass

    def update(self, field_name: str, new_value: Any, old_value: Any = None, model: Any = None) -> None:
        pass

    def on_view_show(self) -> None:
        self.app.notification_presenter.notify_info(
            "Tab Manager", "Feature active.", "TabManager"
        )

    def on_view_close(self) -> None:
        pass

    # Public methods to add tabs
    def add_text_tab(self):
        self.view.tab_widget.add_tab("Text Editor", TextWidget())
        self.app.notification_presenter.log_info("Added Text Tab", "TabManager")

    def add_counter_tab(self):
        self.view.tab_widget.add_tab("Counter", CounterWidget())
        self.app.notification_presenter.log_info("Added Counter Tab", "TabManager")

    def add_list_tab(self):
        self.view.tab_widget.add_tab("List", ListWidget())
        self.app.notification_presenter.log_info("Added List Tab", "TabManager")

    # Signal handlers
    def _on_tab_added(self, index, name):
        self.app.notification_presenter.log_debug(f"Tab added: {name} at {index}", "TabManager")

    def _on_tab_removed(self, index, name):
        self.app.notification_presenter.log_info(f"Tab closed: {name}", "TabManager")

    def _on_tab_changed(self, index):
        name = self.view.tab_widget.get_tab_name(index)
        if name:
            self.app.notification_presenter.log_debug(f"Switched to tab: {name}", "TabManager")

    # Workspace Persistence
    def save_workspace(self, workspace_object: dict) -> None:
        super().save_workspace(workspace_object)
        workspace_object[self.feature_id]["tab_data"] = self.view.tab_widget.get_workspace_data()

    def load_workspace(self, workspace_object: dict) -> None:
        super().load_workspace(workspace_object)
        if self.feature_id in workspace_object and "tab_data" in workspace_object[self.feature_id]:
            data = workspace_object[self.feature_id]["tab_data"]
            self.view.tab_widget.load_workspace_data(data)
