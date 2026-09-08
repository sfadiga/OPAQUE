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


from typing import Callable, List, Optional

from PySide6.QtWidgets import QToolBar, QToolButton, QWidget
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon

from opaque.presenters.presenter import BasePresenter


class OpaqueMainToolbar(QToolBar):
    """
    A toolbar that automatically populates with buttons for registered features.
    Manages the interaction logic, including toggling windows and highlighting.
    Button highlighting adapts to the current theme's highlight color.
    """

    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(title, parent)

        self.setMovable(True)
        self.setFloatable(True)

        # Every feature button, in the order it was added. The checked state is
        # exclusive across this list.
        self._feature_buttons: List[QToolButton] = []
        # The notification toggle. None until add_notification_button runs.
        self._notification_button: Optional[QToolButton] = None
        self._notification_count: int = 0

        self._setup_default_buttons()

    def add_feature(self, presenter: BasePresenter) -> QToolButton:
        """
        Adds a feature to the toolbar, creating a button and connecting signals.

        Args:
            feature_window: The feature window instance to add.
        """
        feature_name = presenter.model.feature_name()
        button = QToolButton()
        # These two strings belong to the feature, not to the toolbar. Only
        # the code that writes the literal can call tr() on it, because
        # lupdate reads the source text and not the value at run time.
        button.setText(feature_name)
        button.setToolTip(presenter.model.feature_description())
        button.setIcon(presenter.model.feature_icon())
        button.setIconSize(QSize(24, 24))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setMinimumSize(70, 0)
        # Qt draws the checked state itself, in every platform style and in
        # every third-party theme. The visual includes a frame change as well
        # as a colour change, so the state is not carried by colour alone.
        button.setCheckable(True)
        self._feature_buttons.append(button)

        self.addWidget(button)
        # --- Connect signals and slots ---
        self.connect_slot_to_button_click(presenter.view.open_close, button)
        # 2. Window is shown -> Highlight button
        self.connect_signal_to_set_active(presenter.view.window_opened.connect, button)
        # 3. Window is focused -> Highlight button
        self.connect_signal_to_set_active(presenter.view.window_focused.connect, button)
        # 4. Window is unfocused -> Highlight button
        # self.connect_signal_to_set_inactive(presenter.view.window_unfocused.connect, button)
        # 5. Window is closed -> Un-highlight button
        self.connect_signal_to_set_inactive(presenter.view.window_closed.connect, button)

        # button is returned as a reference so signals/slots can be associated with
        return button

    def add_separator(self):
        "wrapper to be used in when a peparator is required"
        self.addSeparator()

    def connect_slot_to_button_click(self, open_close_slot: Callable, button: QToolButton):
        button.clicked.connect(open_close_slot)

    def connect_signal_to_set_active(self, activate_signal: Callable, button: QToolButton):
        activate_signal(lambda: self._set_active(button))

    def connect_signal_to_set_inactive(self, deactivate_signal: Callable, button: QToolButton):
        deactivate_signal(lambda: self._set_inactive(button))

    def add_notification_button(self, callback: Callable) -> QToolButton:
        """
        Add the notification panel toggle.

        The button is checkable so it reports whether the panel is open. Call
        set_notifications_visible to keep it in step with the dock, and
        set_notification_count to show the unread count.
        """
        notif_button = QToolButton()
        notif_button.setText(self.tr("Notifications"))
        notif_button.setToolTip(self.tr("Toggle Notifications Panel"))
        notif_button.setIcon(QIcon.fromTheme("dialog-information"))
        notif_button.setIconSize(QSize(24, 24))
        notif_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        notif_button.setMinimumSize(70, 0)
        notif_button.setCheckable(True)
        notif_button.setAccessibleName(self.tr("Notifications"))
        notif_button.clicked.connect(callback)

        self._notification_button = notif_button

        # Group the toggle with Cascade and Tiled, which sit before the
        # separator that _setup_default_buttons adds.
        actions = self.actions()
        if actions and actions[-1].isSeparator():
            self.insertWidget(actions[-1], notif_button)
        else:
            self.addWidget(notif_button)

        return notif_button

    # The highest count shown as a number. Above this the label reads "99+",
    # because an exact count stops being useful and starts widening the button.
    NOTIFICATION_COUNT_LIMIT: int = 99

    def set_notifications_visible(self, visible: bool) -> None:
        """Keep the notification toggle in step with the panel."""
        if self._notification_button is None:
            return
        self._notification_button.setChecked(visible)

    def set_notification_count(self, count: int) -> None:
        """
        Show the unread notification count on the toggle.

        The count is text, not a coloured dot, so it stays readable for a user
        with a colour vision deficiency and it reaches a screen reader.
        """
        self._notification_count = max(0, count)
        if self._notification_button is None:
            return

        label = self.tr("Notifications")
        if self._notification_count == 0:
            self._notification_button.setText(label)
            self._notification_button.setAccessibleName(label)
            self._notification_button.setToolTip(
                self.tr("Toggle Notifications Panel"))
            return

        if self._notification_count > self.NOTIFICATION_COUNT_LIMIT:
            shown = f"{self.NOTIFICATION_COUNT_LIMIT}+"
        else:
            shown = str(self._notification_count)

        self._notification_button.setText(f"{label} ({shown})")
        self._notification_button.setAccessibleName(f"{label} ({shown})")
        self._notification_button.setToolTip(
            self.tr("Toggle Notifications Panel. Unread: ") + shown)

    def update_theme(self) -> None:
        """
        Repaint the toolbar after the application theme changed.

        The toolbar writes no colours of its own. A style sheet theme changes
        the button appearance, but Qt does not always repolish a widget that
        was created before the style sheet was installed, so ask for it here.

        Connect this to ThemeService.theme_changed.
        """
        style = self.style()
        for button in self._feature_buttons:
            style.unpolish(button)
            style.polish(button)
        style.unpolish(self)
        style.polish(self)
        self.update()

    def _setup_default_buttons(self) -> None:
        """Adds the default Cascade and Tiled buttons."""
        cascade_button = QToolButton()
        cascade_button.setText(self.tr("Cascade"))
        cascade_button.setToolTip(self.tr("Cascade windows"))
        cascade_button.setIcon(QIcon.fromTheme("edit-copy"))
        cascade_button.setIconSize(QSize(24, 24))
        cascade_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        cascade_button.setMinimumSize(70, 0)
        cascade_button.clicked.connect(self._cascade_windows)
        self.addWidget(cascade_button)

        tiled_button = QToolButton()
        tiled_button.setText(self.tr("Tiled"))
        tiled_button.setToolTip(self.tr("Tile windows"))
        tiled_button.setIcon(QIcon.fromTheme("edit-select-all"))
        tiled_button.setIconSize(QSize(24, 24))
        tiled_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        tiled_button.setMinimumSize(70, 0)
        tiled_button.clicked.connect(self._tile_windows)
        self.addWidget(tiled_button)

        self.addSeparator()

    def _cascade_windows(self) -> None:
        """Tell the MDI area to cascade the windows."""
        self.parent().mdi_area.cascadeSubWindows()

    def _tile_windows(self) -> None:
        """Tell the MDI area to tile the windows."""
        self.parent().mdi_area.tileSubWindows()

    def _set_active(self, button_to_activate: QToolButton) -> None:
        """
        Check one feature button and clear every other one.

        The checked state is exclusive because only one MDI sub window can hold
        the focus at a time.
        """
        for button in self._feature_buttons:
            button.setChecked(button is button_to_activate)

    def _set_inactive(self, button_to_deactivate: QToolButton) -> None:
        """Clear the checked state of one feature button."""
        button_to_deactivate.setChecked(False)
