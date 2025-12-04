#!/usr/bin/env python3
# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework - Notification System Example
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path to import opaque modules
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QComboBox
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon

from opaque.view.application import BaseApplication
from opaque.models.configuration import DefaultApplicationConfiguration
from opaque.services.notification_service import NotificationLevel
from opaque.services.service import ServiceLocator
from opaque.services.notification_service import NotificationService
from opaque.services.logger_service import LoggerService


class NotificationTestConfiguration(DefaultApplicationConfiguration):
    """Configuration for the notification test application"""
    
    def get_application_name(self) -> str:
        return "NotificationTest"
    
    def get_application_title(self) -> str:
        return "Notification System Test"
    
    def get_application_organization(self) -> str:
        return "OPAQUE Framework"
    
    def get_application_version(self) -> str:
        return "1.0.0"
    
    def get_application_description(self) -> str:
        return "Test application for OPAQUE notification system"
    
    def get_application_icon(self) -> QIcon:
        return QIcon()  # Empty icon for this test app


class NotificationTestWidget(QWidget):
    """A test widget to demonstrate notification functionality"""
    
    def __init__(self, main_window: BaseApplication):
        super().__init__()
        self.main_window = main_window
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the test interface"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Notification System Test")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Notification level selector
        level_label = QLabel("Select Notification Level:")
        layout.addWidget(level_label)
        
        self.level_combo = QComboBox()
        self.level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_combo.setCurrentText("INFO")
        layout.addWidget(self.level_combo)
        
        # Test buttons
        test_notification_btn = QPushButton("Send Test Notification")
        test_notification_btn.clicked.connect(self.send_test_notification)
        layout.addWidget(test_notification_btn)
        
        test_log_btn = QPushButton("Send Test Log Message")
        test_log_btn.clicked.connect(self.send_test_log)
        layout.addWidget(test_log_btn)
        
        demo_sequence_btn = QPushButton("Run Demo Sequence")
        demo_sequence_btn.clicked.connect(self.run_demo_sequence)
        layout.addWidget(demo_sequence_btn)
        
        toggle_notifications_btn = QPushButton("Toggle Notifications Panel")
        toggle_notifications_btn.clicked.connect(self.toggle_notifications)
        layout.addWidget(toggle_notifications_btn)
        
        clear_notifications_btn = QPushButton("Clear All Notifications")
        clear_notifications_btn.clicked.connect(self.clear_notifications)
        layout.addWidget(clear_notifications_btn)
        
        # Status
        self.status_label = QLabel("Ready to test notifications...")
        self.status_label.setStyleSheet("margin-top: 20px; padding: 10px; background-color: #f0f0f0;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        self.setWindowTitle("Notification Test Controls")
        
    def send_test_notification(self):
        """Send a test notification"""
        try:
            level_text = self.level_combo.currentText()
            level = getattr(NotificationLevel, level_text)
            
            notification_id = self.main_window.notification_presenter.add_notification(
                level=level,
                title=f"Test {level_text} Notification",
                message=f"This is a test {level_text.lower()} notification message.",
                source="TestWidget",
                persistent=(level_text in ["ERROR", "CRITICAL"])
            )
            
            self.status_label.setText(f"Sent {level_text} notification (ID: {notification_id})")
            
        except Exception as e:
            self.status_label.setText(f"Error sending notification: {e}")
    
    def send_test_log(self):
        """Send a test log message"""
        try:
            level_text = self.level_combo.currentText().lower()
            message = f"Test {level_text} log message from TestWidget"
            
            # Call the appropriate log method
            log_method = getattr(self.main_window.notification_presenter, f"log_{level_text}")
            log_method(message, "TestWidget", notify=(level_text in ["warning", "error", "critical"]))
            
            self.status_label.setText(f"Logged {level_text} message")
            
        except Exception as e:
            self.status_label.setText(f"Error logging message: {e}")
    
    def run_demo_sequence(self):
        """Run a demonstration sequence of notifications"""
        try:
            # Create a timer to send notifications in sequence
            self.demo_timer = QTimer()
            self.demo_step = 0
            self.demo_timer.timeout.connect(self.demo_next_step)
            self.demo_timer.start(2000)  # 2 second intervals
            
            self.status_label.setText("Running demo sequence...")
            
        except Exception as e:
            self.status_label.setText(f"Error running demo: {e}")
    
    def demo_next_step(self):
        """Execute the next step in the demo sequence"""
        try:
            if self.demo_step == 0:
                self.main_window.notification_presenter.notify_info(
                    "Demo Started", "Beginning notification system demonstration", "Demo"
                )
            elif self.demo_step == 1:
                self.main_window.notification_presenter.log_info(
                    "Demo step 1: Info logging", "Demo"
                )
            elif self.demo_step == 2:
                self.main_window.notification_presenter.notify_warning(
                    "Demo Warning", "This is a warning notification", "Demo"
                )
            elif self.demo_step == 3:
                self.main_window.notification_presenter.log_error(
                    "Demo error log (this will create a notification)", "Demo", notify=True
                )
            elif self.demo_step == 4:
                self.main_window.notification_presenter.notify_info(
                    "Demo Complete", "Notification system demonstration finished", "Demo"
                )
                self.demo_timer.stop()
                self.status_label.setText("Demo sequence completed!")
                return
            
            self.demo_step += 1
            
        except Exception as e:
            self.demo_timer.stop()
            self.status_label.setText(f"Demo error: {e}")
    
    def toggle_notifications(self):
        """Toggle the notifications panel visibility"""
        try:
            self.main_window.notification_presenter.toggle_notifications()
            self.status_label.setText("Toggled notifications panel")
        except Exception as e:
            self.status_label.setText(f"Error toggling notifications: {e}")
    
    def clear_notifications(self):
        """Clear all notifications"""
        try:
            self.main_window.notification_presenter.clear_notifications()
            self.status_label.setText("Cleared all notifications")
        except Exception as e:
            self.status_label.setText(f"Error clearing notifications: {e}")


class NotificationTestApplication(BaseApplication):
    """Main application for testing notifications"""
    
    def __init__(self):
        config = NotificationTestConfiguration()
        super().__init__(config)
        
        # Create and add the test widget to the MDI area instead of showing separately
        self.test_widget = NotificationTestWidget(self)
        
        # Add the test widget as a subwindow in the MDI area
        sub_window = self.mdi_area.addSubWindow(self.test_widget)
        sub_window.setWindowTitle("Notification Test Controls")
        sub_window.show()
        
        # Ensure the main window is visible
        self.resize(800, 600)
        
        # Send a welcome notification
        QTimer.singleShot(1000, self.send_welcome_notification)
    
    def send_welcome_notification(self):
        """Send a welcome notification after the app starts"""
        try:
            self.notification_presenter.notify_info(
                "Welcome!",
                "Notification system test application is ready. Use the controls to test different notification types. Check the notification panel at the bottom.",
                "System"
            )
        except Exception as e:
            print(f"Error sending welcome notification: {e}")


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    # Create and show the main application
    main_window = NotificationTestApplication()
    
    # Check single instance
    if not main_window.try_acquire_lock():
        main_window.show_already_running_message()
        sys.exit(1)
    
    main_window.show()
    
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
