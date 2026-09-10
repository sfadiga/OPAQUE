"""
Notification Tester View
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QComboBox
)
from PySide6.QtCore import Signal

from opaque.view.theme import TypeScale
from opaque.view.view import BaseView


class NotificationTesterView(BaseView):
    """View for the notification tester feature."""

    # Signals
    send_notification_clicked = Signal()
    send_log_clicked = Signal()
    run_demo_clicked = Signal()
    toggle_panel_clicked = Signal()
    clear_notifications_clicked = Signal()
    level_changed = Signal(str)

    def setup_ui(self) -> None:
        """Set up the test interface"""
        layout = QVBoxLayout()

        # Title
        title = QLabel(self.tr("Notification System Test"))
        title.setFont(TypeScale.h2())
        layout.addWidget(title)

        # Notification level selector
        level_label = QLabel(self.tr("Select Notification Level:"))
        layout.addWidget(level_label)

        self.level_combo = QComboBox()
        self.level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_combo.setCurrentText("INFO")
        self.level_combo.currentTextChanged.connect(self.level_changed.emit)
        layout.addWidget(self.level_combo)

        # Test buttons
        test_notification_btn = QPushButton(self.tr("Send Test Notification"))
        test_notification_btn.clicked.connect(self.send_notification_clicked)
        layout.addWidget(test_notification_btn)

        test_log_btn = QPushButton(self.tr("Send Test Log Message"))
        test_log_btn.clicked.connect(self.send_log_clicked)
        layout.addWidget(test_log_btn)

        demo_sequence_btn = QPushButton(self.tr("Run Demo Sequence"))
        demo_sequence_btn.clicked.connect(self.run_demo_clicked)
        layout.addWidget(demo_sequence_btn)

        toggle_notifications_btn = QPushButton(self.tr("Toggle Notifications Panel"))
        toggle_notifications_btn.clicked.connect(self.toggle_panel_clicked)
        layout.addWidget(toggle_notifications_btn)

        clear_notifications_btn = QPushButton(self.tr("Clear All Notifications"))
        clear_notifications_btn.clicked.connect(self.clear_notifications_clicked)
        layout.addWidget(clear_notifications_btn)

        # Status
        self.status_label = QLabel(self.tr("Ready to test notifications..."))
        self.status_label.setStyleSheet("margin-top: 20px; padding: 10px; background-color: palette(base); border: 1px solid palette(mid);")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        container = QWidget()
        container.setLayout(layout)
        self.setWidget(container)

    def update_status(self, message: str):
        """Update the status label"""
        self.status_label.setText(message)

    def get_selected_level(self) -> str:
        """Get currently selected level"""
        return self.level_combo.currentText()
        
    def set_selected_level(self, level: str):
        """Set selected level"""
        self.level_combo.setCurrentText(level)
