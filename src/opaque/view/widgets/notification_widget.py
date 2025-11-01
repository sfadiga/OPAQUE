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

from typing import Optional, List, Dict, Any
from datetime import datetime

from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QComboBox, QFrame,
    QSizePolicy, QScrollArea, QApplication, QMenu, QHeaderView
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QRect, QEasingCurve
from PySide6.QtGui import QIcon, QFont, QPalette, QAction

from opaque.services.service import ServiceLocator
from opaque.services.notification_service import NotificationService, Notification, NotificationLevel


class NotificationItemWidget(QFrame):
    """Individual notification item widget with rich display"""

    item_clicked = Signal(str)  # notification_id
    item_removed = Signal(str)  # notification_id

    def __init__(self, notification: Notification, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.notification = notification
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        """Set up the notification item UI"""
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(1)
        self.setContentsMargins(8, 8, 8, 8)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        # Header with title, time, and close button
        header_layout = QHBoxLayout()

        # Unread indicator
        if not self.notification.read:
            self.unread_indicator = QLabel("●")
            self.unread_indicator.setFont(
                QFont("Arial", 12, QFont.Weight.Bold))
            self.unread_indicator.setStyleSheet(
                "color: #007bff; padding: 0px 4px;")
            self.unread_indicator.setToolTip("Unread notification")
            header_layout.addWidget(self.unread_indicator)

        # Level indicator
        self.level_label = QLabel(self.notification.level.value.upper())
        self.level_label.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        self.level_label.setFixedWidth(60)
        header_layout.addWidget(self.level_label)

        # Title
        self.title_label = QLabel(self.notification.title)
        font = QFont(
            "Arial", 9, QFont.Weight.Bold if not self.notification.read else QFont.Weight.Normal)
        self.title_label.setFont(font)
        self.title_label.setWordWrap(True)
        header_layout.addWidget(self.title_label, 1)

        # NEW indicator for unread notifications
        if not self.notification.read:
            self.new_indicator = QLabel("NEW")
            self.new_indicator.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            self.new_indicator.setStyleSheet("""
                QLabel {
                    color: white;
                    background-color: #007bff;
                    padding: 2px 6px;
                    border-radius: 8px;
                    margin: 0px 4px;
                }
            """)
            self.new_indicator.setToolTip(
                "New notification - click to mark as read")
            header_layout.addWidget(self.new_indicator)

        # Time
        time_str = self.notification.timestamp.strftime("%H:%M:%S")
        self.time_label = QLabel(time_str)
        self.time_label.setFont(QFont("Arial", 8))
        self.time_label.setStyleSheet("color: gray;")
        header_layout.addWidget(self.time_label)

        # Close button
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.clicked.connect(
            lambda: self.item_removed.emit(self.notification.id))
        header_layout.addWidget(self.close_btn)

        layout.addLayout(header_layout)

        # Message
        if self.notification.message:
            self.message_label = QLabel(self.notification.message)
            self.message_label.setWordWrap(True)
            self.message_label.setFont(QFont("Arial", 8))
            layout.addWidget(self.message_label)

        # Footer with source
        footer_layout = QHBoxLayout()
        source_label = QLabel(f"Source: {self.notification.source}")
        source_label.setFont(QFont("Arial", 7))
        source_label.setStyleSheet("color: gray;")
        footer_layout.addWidget(source_label)

        if self.notification.persistent:
            persistent_label = QLabel("📌")
            persistent_label.setToolTip("Persistent notification")
            footer_layout.addWidget(persistent_label)

        footer_layout.addStretch()
        layout.addLayout(footer_layout)

    def _apply_style(self) -> None:
        """Apply level-specific styling using current application theme"""
        # Get current palette colors
        app = QApplication.instance()
        if app:
            palette = app.palette()
        else:
            palette = QPalette()

        # Get theme-aware colors
        base_color = palette.color(QPalette.ColorRole.Base).name()
        text_color = palette.color(QPalette.ColorRole.Text).name()
        window_color = palette.color(QPalette.ColorRole.Window).name()
        highlight_color = palette.color(QPalette.ColorRole.Highlight).name()

        level_colors = {
            NotificationLevel.DEBUG: "#6c757d",      # Gray
            NotificationLevel.INFO: "#0dcaf0",       # Cyan
            NotificationLevel.WARNING: "#ffc107",    # Yellow
            NotificationLevel.ERROR: "#dc3545",      # Red
            NotificationLevel.CRITICAL: "#6f42c1"    # Purple
        }

        level_color = level_colors.get(self.notification.level, "#6c757d")

        # Create better contrast hover color
        # Use button color for hover which typically provides good contrast
        try:
            button_color = palette.color(QPalette.ColorRole.Button).name()
            hover_color = button_color
        except:
            # Fallback: slightly darker/lighter than base
            if base_color.lower() in ['#ffffff', '#f0f0f0']:
                hover_color = "#e0e0e0"  # Slightly darker for light themes
            else:
                hover_color = "#404040"  # Slightly lighter for dark themes

        # Apply border color based on level with theme-aware background
        self.setStyleSheet(f"""
            NotificationItemWidget {{
                border-left: 4px solid {level_color};
                background-color: {base_color};
                color: {text_color};
                border-radius: 4px;
                margin: 2px 0px;
            }}
            NotificationItemWidget:hover {{
                background-color: {hover_color};
                border: 1px solid {level_color};
                border-left: 4px solid {level_color};
            }}
        """)

        # Style level label with theme colors
        self.level_label.setStyleSheet(f"""
            QLabel {{
                color: {level_color};
                background-color: transparent;
                padding: 2px 4px;
                border-radius: 2px;
            }}
        """)

        # Style other labels with theme colors
        self.title_label.setStyleSheet(f"color: {text_color};")
        if hasattr(self, 'message_label'):
            self.message_label.setStyleSheet(f"color: {text_color};")

        # Mark as read styling
        if self.notification.read:
            self.setStyleSheet(self.styleSheet() + """
                NotificationItemWidget {
                    opacity: 0.7;
                }
            """)

    def mousePressEvent(self, event) -> None:
        """Handle click events"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.item_clicked.emit(self.notification.id)
        super().mousePressEvent(event)


class NotificationWidget(QDockWidget):
    """
    Dockable notification widget that displays system notifications.
    Can be collapsed/expanded and provides filtering and management capabilities.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Notifications", parent)

        # Widget state
        self._is_expanded = True
        self._unread_count = 0

        # Services
        self._notification_service: Optional[NotificationService] = None

        # UI Components
        self._main_widget: Optional[QWidget] = None
        self._notification_items: Dict[str, NotificationItemWidget] = {}

        # Setup
        self._setup_ui()
        self._connect_to_notification_service()
        self._setup_update_timer()

    def _setup_ui(self) -> None:
        """Set up the notification widget UI"""
        # Configure dock widget - allow docking on all sides
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea |
                             Qt.DockWidgetArea.RightDockWidgetArea |
                             Qt.DockWidgetArea.TopDockWidgetArea |
                             Qt.DockWidgetArea.BottomDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable |
                         QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                         QDockWidget.DockWidgetFeature.DockWidgetClosable)

        # Main widget
        self._main_widget = QWidget()
        self.setWidget(self._main_widget)

        # Main layout
        main_layout = QVBoxLayout(self._main_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(4, 4, 4, 4)

        # Header with controls
        self._setup_header(main_layout)

        # Filter controls
        self._setup_filter_controls(main_layout)

        # Notification list
        self._setup_notification_list(main_layout)

        # Footer with action buttons
        self._setup_footer(main_layout)

        # Initial update
        self._update_notifications()

    def _setup_header(self, parent_layout: QVBoxLayout) -> None:
        """Set up the header with title and collapse button"""
        header_layout = QHBoxLayout()

        # Title label
        self.title_label = QLabel("Notifications")
        font = self.title_label.font()
        font.setBold(True)
        font.setPointSize(10)
        self.title_label.setFont(font)
        header_layout.addWidget(self.title_label)

        # Unread count badge
        self.count_label = QLabel("0")
        self.count_label.setStyleSheet("""
            QLabel {
                background-color: #dc3545;
                color: white;
                border-radius: 8px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: bold;
            }
        """)
        self.count_label.setFixedHeight(16)
        header_layout.addWidget(self.count_label)

        header_layout.addStretch()

        # Collapse/expand button
        self.collapse_btn = QPushButton("▼")
        self.collapse_btn.setFixedSize(20, 20)
        self.collapse_btn.clicked.connect(self._toggle_expanded)
        header_layout.addWidget(self.collapse_btn)

        parent_layout.addLayout(header_layout)

    def _setup_filter_controls(self, parent_layout: QVBoxLayout) -> None:
        """Set up filtering controls"""
        filter_layout = QHBoxLayout()

        # Level filter
        filter_label = QLabel("Filter:")
        filter_layout.addWidget(filter_label)

        self.level_filter = QComboBox()
        self.level_filter.addItems(
            ["All", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_filter.currentTextChanged.connect(
            self._update_notifications)
        filter_layout.addWidget(self.level_filter)

        # Unread only checkbox
        self.unread_btn = QPushButton("Unread Only")
        self.unread_btn.setCheckable(True)
        self.unread_btn.toggled.connect(self._update_notifications)
        filter_layout.addWidget(self.unread_btn)

        filter_layout.addStretch()

        parent_layout.addLayout(filter_layout)

    def _setup_notification_list(self, parent_layout: QVBoxLayout) -> None:
        """Set up the scrollable notification list"""
        # Create scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Container widget for notifications
        self.notifications_container = QWidget()
        self.notifications_layout = QVBoxLayout(self.notifications_container)
        self.notifications_layout.setSpacing(2)
        self.notifications_layout.addStretch()  # Push items to top

        self.scroll_area.setWidget(self.notifications_container)
        parent_layout.addWidget(self.scroll_area, 1)  # Expand to fill space

    def _setup_footer(self, parent_layout: QVBoxLayout) -> None:
        """Set up footer with action buttons"""
        footer_layout = QHBoxLayout()

        # Mark all read button
        self.mark_read_btn = QPushButton("Mark All Read")
        self.mark_read_btn.clicked.connect(self._mark_all_read)
        footer_layout.addWidget(self.mark_read_btn)

        # Clear button with dropdown menu
        self.clear_btn = QPushButton("Clear")
        self.clear_menu = QMenu(self.clear_btn)

        clear_all_action = QAction("Clear All", self)
        clear_all_action.triggered.connect(lambda: self._clear_notifications())
        self.clear_menu.addAction(clear_all_action)

        self.clear_menu.addSeparator()

        for level in NotificationLevel:
            action = QAction(f"Clear {level.value.title()}", self)
            action.triggered.connect(
                lambda checked, l=level: self._clear_notifications(l))
            self.clear_menu.addAction(action)

        self.clear_btn.setMenu(self.clear_menu)
        footer_layout.addWidget(self.clear_btn)

        footer_layout.addStretch()

        parent_layout.addLayout(footer_layout)

    def _connect_to_notification_service(self) -> None:
        """Connect to the notification service"""
        self._notification_service = ServiceLocator.get_service("notification")
        if self._notification_service and hasattr(self._notification_service, 'notification_added'):
            self._notification_service.notification_added.connect(
                self._on_notification_added)
            self._notification_service.notification_updated.connect(
                self._on_notification_updated)
            self._notification_service.notification_removed.connect(
                self._on_notification_removed)
            self._notification_service.notifications_cleared.connect(
                self._on_notifications_cleared)

    def _setup_update_timer(self) -> None:
        """Set up timer for periodic updates"""
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_time_displays)
        self._update_timer.start(60000)  # Update every minute

    def _toggle_expanded(self) -> None:
        """Toggle between expanded and collapsed state"""
        self._is_expanded = not self._is_expanded

        # Update button text
        self.collapse_btn.setText("▼" if self._is_expanded else "▶")

        # Get the specific widgets to toggle (not their parents)
        widgets_to_toggle = [
            self.level_filter,
            self.unread_btn,
            self.scroll_area,
            self.mark_read_btn,
            self.clear_btn
        ]

        # Also toggle the filter label
        filter_label = None
        if hasattr(self, 'level_filter') and self.level_filter.parent():
            parent_layout = self.level_filter.parent().layout()
            if parent_layout and parent_layout.count() > 0:
                filter_label = parent_layout.itemAt(0).widget()

        if filter_label and hasattr(filter_label, 'text') and filter_label.text() == "Filter:":
            widgets_to_toggle.append(filter_label)

        # Show/hide content widgets
        for widget in widgets_to_toggle:
            if widget:
                widget.setVisible(self._is_expanded)

        # Update the widget geometry more gently
        if self._main_widget:
            # Don't force specific heights, just let the layout adjust naturally
            if not self._is_expanded:
                # Set a reasonable minimum height when collapsed
                self._main_widget.setMinimumHeight(40)
                self._main_widget.setMaximumHeight(60)
            else:
                # Reset to allow normal expansion
                self._main_widget.setMinimumHeight(150)
                self._main_widget.setMaximumHeight(16777215)

            # Update geometry
            self._main_widget.updateGeometry()
            self.updateGeometry()

    def _update_notifications(self) -> None:
        """Update the notification display"""
        if not self._notification_service:
            return

        # Get filter settings
        level_filter = None
        if self.level_filter.currentText() != "All":
            level_filter = NotificationLevel(
                self.level_filter.currentText().lower())

        unread_only = self.unread_btn.isChecked()

        # Get notifications from service
        from typing import cast
        service = cast(NotificationService, self._notification_service)
        notifications = service.get_notifications(
            level_filter=level_filter,
            unread_only=unread_only,
            limit=100  # Limit display for performance
        )

        # Clear existing items
        self._clear_notification_items()

        # Add notification items
        for notification in notifications:
            self._add_notification_item(notification)

        # Update counts
        self._update_counts()

    def _add_notification_item(self, notification: Notification) -> None:
        """Add a notification item to the display"""
        if notification.id in self._notification_items:
            return

        item_widget = NotificationItemWidget(notification)
        item_widget.item_clicked.connect(self._on_notification_clicked)
        item_widget.item_removed.connect(
            self._on_notification_remove_requested)

        # Insert at the beginning (most recent first)
        self.notifications_layout.insertWidget(0, item_widget)
        self._notification_items[notification.id] = item_widget

    def _clear_notification_items(self) -> None:
        """Clear all notification item widgets"""
        for item_widget in self._notification_items.values():
            item_widget.setParent(None)
            item_widget.deleteLater()
        self._notification_items.clear()

    def _update_counts(self) -> None:
        """Update unread count display"""
        if not self._notification_service:
            return

        from typing import cast
        service = cast(NotificationService, self._notification_service)
        unread_count = service.get_notification_count(unread_only=True)

        self._unread_count = unread_count
        self.count_label.setText(str(unread_count))
        self.count_label.setVisible(unread_count > 0)

    def _update_time_displays(self) -> None:
        """Update time displays for all notification items"""
        current_time = datetime.now()
        for item_widget in self._notification_items.values():
            # Update relative time display
            time_diff = current_time - item_widget.notification.timestamp
            if time_diff.days > 0:
                time_str = f"{time_diff.days}d ago"
            elif time_diff.seconds > 3600:
                hours = time_diff.seconds // 3600
                time_str = f"{hours}h ago"
            elif time_diff.seconds > 60:
                minutes = time_diff.seconds // 60
                time_str = f"{minutes}m ago"
            else:
                time_str = "now"

            item_widget.time_label.setText(time_str)

    # Slot methods for notification service events
    def _on_notification_added(self, notification: Notification) -> None:
        """Handle new notification added"""
        self._update_notifications()

    def _on_notification_updated(self, notification: Notification) -> None:
        """Handle notification updated"""
        # For read status changes, we need to recreate the widget to remove/add the NEW indicator
        if notification.id in self._notification_items:
            # Remove the old widget
            old_widget = self._notification_items[notification.id]
            old_widget.setParent(None)
            old_widget.deleteLater()
            del self._notification_items[notification.id]

            # Add the updated widget
            self._add_notification_item(notification)

        self._update_counts()

    def _on_notification_removed(self, notification_id: str) -> None:
        """Handle notification removed"""
        if notification_id in self._notification_items:
            item_widget = self._notification_items[notification_id]
            item_widget.setParent(None)
            item_widget.deleteLater()
            del self._notification_items[notification_id]
        self._update_counts()

    def _on_notifications_cleared(self, level_filter: Optional[NotificationLevel]) -> None:
        """Handle notifications cleared"""
        self._update_notifications()

    # UI event handlers
    def _on_notification_clicked(self, notification_id: str) -> None:
        """Handle notification item clicked"""
        if self._notification_service:
            from typing import cast
            service = cast(NotificationService, self._notification_service)
            service.mark_as_read(notification_id)

    def _on_notification_remove_requested(self, notification_id: str) -> None:
        """Handle notification removal request"""
        if self._notification_service:
            from typing import cast
            service = cast(NotificationService, self._notification_service)
            service.remove_notification(notification_id)

    def _mark_all_read(self) -> None:
        """Mark all visible notifications as read"""
        if self._notification_service:
            from typing import cast
            service = cast(NotificationService, self._notification_service)

            level_filter = None
            if self.level_filter.currentText() != "All":
                level_filter = NotificationLevel(
                    self.level_filter.currentText().lower())

            service.mark_all_as_read(level_filter)

    def _clear_notifications(self, level_filter: Optional[NotificationLevel] = None) -> None:
        """Clear notifications with optional level filter"""
        if self._notification_service:
            from typing import cast
            service = cast(NotificationService, self._notification_service)
            service.clear_notifications(level_filter)
