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


from typing import Optional, Callable

from PySide6.QtWidgets import QToolBar, QToolButton, QWidget, QApplication
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPalette

from opaque.presenters.presenter import BasePresenter


class OpaqueMainToolbar(QToolBar):
    """
    A toolbar that automatically populates with buttons for registered features.
    Manages the interaction logic, including toggling windows and highlighting.
    Button highlighting adapts to the current theme's highlight color.
    """

    # Default fallback color if theme doesn't provide one
    DEFAULT_HIGHLIGHT_COLOR = "rgb(85, 170, 0)"

    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(title, parent)

        self.setMovable(True)
        self.setFloatable(True)

        self._active_button: Optional[QToolButton] = None
        self._current_highlight_style: str = ""

        self._setup_default_buttons()
        self._update_highlight_style()

    def add_feature(self, presenter: BasePresenter) -> QToolButton:
        """
        Adds a feature to the toolbar, creating a button and connecting signals.

        Args:
            feature_window: The feature window instance to add.
        """
        feature_name = presenter.model.feature_name()
        button = QToolButton()
        button.setText(self.tr(feature_name))
        button.setToolTip(self.tr(presenter.model.feature_description()))
        button.setIcon(presenter.model.feature_icon())
        button.setIconSize(QSize(24, 24))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setMinimumSize(70, 0)

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
        deactivate_signal(lambda: self._set_active(button))

    def add_notification_button(self, callback: Callable) -> QToolButton:
        """Adds a notification toggle button to the toolbar."""
        notif_button = QToolButton()
        notif_button.setText(self.tr("Notifications"))
        notif_button.setToolTip(self.tr("Toggle Notifications Panel"))
        # Use a generic icon or theme icon if available
        # "dialog-information" is a standard icon name often available
        notif_button.setIcon(QIcon.fromTheme("dialog-information"))
        notif_button.setIconSize(QSize(24, 24))
        notif_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        notif_button.setMinimumSize(70, 0)
        notif_button.clicked.connect(callback)
        
        # Insert before the last separator (which is added in _setup_default_buttons)
        # However, _setup_default_buttons adds cascade, tiled, then separator.
        # So we probably want it next to them.
        # Since we are calling this after initialization, simply addWidget will append to end.
        # If we want it "near" tile/cascade, appending is fine as tile/cascade are default buttons.
        # But features are added via add_feature which also uses addWidget.
        # If we want it specifically grouped with cascade/tile, we might need to insert it.
        # Cascade and Tile are added in __init__. Features are added later.
        # If we append now, it will be after Cascade/Tile and before features (if features added after).
        # Actually features are added in register_feature.
        # Let's just append it. It will be near the start.
        
        # But wait, _setup_default_buttons adds a separator at the end.
        # So if we addWidget now, it will be after the separator.
        # To be "near" them (group with window management), maybe we want it before the separator?
        # QToolBar doesn't have insertWidget easily without an action reference.
        # But we can get actions() list.
        
        actions = self.actions()
        if actions and actions[-1].isSeparator():
             self.insertWidget(actions[-1], notif_button)
        else:
             self.addWidget(notif_button)
             
        return notif_button

    def update_theme(self) -> None:
        """
        Public method to update the toolbar when theme changes.
        Called by the main application when a new theme is applied.
        """
        self._update_highlight_style()

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

    def _get_theme_highlight_color(self) -> str:
        """
        Extracts the highlight color from the current theme's palette.
        Returns a CSS rgb string.
        """
        try:
            # Get the current application palette
            palette = QApplication.palette()

            # Try to get the highlight color from the palette
            highlight_color = palette.color(QPalette.ColorRole.Highlight)

            # Check if we got a valid color (not black/default)
            if highlight_color.isValid() and highlight_color.name() != "#000000":
                # Return as rgb string for CSS
                return f"rgb({highlight_color.red()}, {highlight_color.green()}, {highlight_color.blue()})"

            # Try alternative palette colors
            accent_color = palette.color(QPalette.ColorRole.Accent) if hasattr(
                QPalette.ColorRole, 'Accent') else None
            if accent_color and accent_color.isValid() and accent_color.name() != "#000000":
                return f"rgb({accent_color.red()}, {accent_color.green()}, {accent_color.blue()})"

        except Exception:
            pass

        # Return default color as fallback
        return self.DEFAULT_HIGHLIGHT_COLOR

    def _update_highlight_style(self) -> None:
        """
        Updates the highlight style sheet based on the current theme.
        Should be called when the theme changes.
        """
        highlight_color = self._get_theme_highlight_color()
        self._current_highlight_style = f"""
            QToolButton {{
                background-color: {highlight_color};
                border: 1px solid {highlight_color};
                border-radius: 3px;
            }}
            QToolButton:hover {{
                background-color: {highlight_color};
                opacity: 0.8;
            }}
        """

        # Update the active button if there is one
        if self._active_button:
            self._active_button.setStyleSheet(self._current_highlight_style)

    def _set_active(self, button_to_activate: QToolButton) -> None:
        """
        Sets the given button as the single active/highlighted button.
        Uses the current theme's highlight color.
        """
        if self._active_button == button_to_activate:
            return

        # Deactivate the previously active button
        if self._active_button is not None:
            self._active_button.setStyleSheet("")

        # Activate the new one with theme-aware style
        button_to_activate.setStyleSheet(self._current_highlight_style)
        self._active_button = button_to_activate

    def _set_inactive(self, button_to_deactivate: QToolButton) -> None:
        if self._active_button and self._active_button == button_to_deactivate:
            self._active_button.setStyleSheet("")
            self._active_button = None
