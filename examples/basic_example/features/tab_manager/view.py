# This Python file uses the following encoding: utf-8
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QSpinBox, QPushButton, QListWidget
)
from opaque.view.view import BaseView
from opaque.view.application import BaseApplication
from opaque.view.widgets import CloseableTabWidget


class TextWidget(QWidget):
    """A simple text editor widget for demonstration."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel("Text Editor Tab")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText("Type here...")
        layout.addWidget(self.text_edit)

    def get_workspace_data(self):
        return {'text_content': self.text_edit.toPlainText()}

    def load_workspace_data(self, data):
        if 'text_content' in data:
            self.text_edit.setPlainText(data['text_content'])


class CounterWidget(QWidget):
    """A simple counter widget."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel("Counter Tab")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        controls = QHBoxLayout()
        self.spin_box = QSpinBox()
        self.spin_box.setRange(-1000, 1000)
        controls.addWidget(QLabel("Value:"))
        controls.addWidget(self.spin_box)
        
        btn_inc = QPushButton("+1")
        btn_inc.clicked.connect(lambda: self.spin_box.setValue(self.spin_box.value() + 1))
        controls.addWidget(btn_inc)
        
        btn_dec = QPushButton("-1")
        btn_dec.clicked.connect(lambda: self.spin_box.setValue(self.spin_box.value() - 1))
        controls.addWidget(btn_dec)
        
        layout.addLayout(controls)
        layout.addStretch()

    def get_workspace_data(self):
        return {'counter_value': self.spin_box.value()}

    def load_workspace_data(self, data):
        if 'counter_value' in data:
            self.spin_box.setValue(data['counter_value'])


class ListWidget(QWidget):
    """A simple list widget."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel("List Tab")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        self.list_widget = QListWidget()
        self.list_widget.addItems(["Item 1", "Item 2"])
        layout.addWidget(self.list_widget)
        
        controls = QHBoxLayout()
        btn_add = QPushButton("Add")
        btn_add.clicked.connect(self._add_item)
        controls.addWidget(btn_add)
        
        btn_del = QPushButton("Remove")
        btn_del.clicked.connect(self._remove_item)
        controls.addWidget(btn_del)
        layout.addLayout(controls)

    def _add_item(self):
        self.list_widget.addItem(f"Item {self.list_widget.count() + 1}")

    def _remove_item(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            self.list_widget.takeItem(row)

    def get_workspace_data(self):
        items = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
        return {'list_items': items}

    def load_workspace_data(self, data):
        if 'list_items' in data:
            self.list_widget.clear()
            self.list_widget.addItems(data['list_items'])


class TabManagerView(BaseView):
    def __init__(self, app: BaseApplication, parent=None):
        super().__init__(app, parent)
        
        layout = QVBoxLayout()
        
        # Info label
        info = QLabel("Use the 'Features > Tab Manager' menu or buttons below.")
        info.setStyleSheet("padding: 5px; color: gray;")
        layout.addWidget(info)
        
        # Closeable Tab Widget
        self.tab_widget = CloseableTabWidget(
            widget_type=TextWidget,
            default_tab_name="Text Editor",
            minimum_tabs=0,
            show_plus_tab=True
        )
        layout.addWidget(self.tab_widget)
        
        self.setWidget(QWidget())
        self.widget().setLayout(layout)
