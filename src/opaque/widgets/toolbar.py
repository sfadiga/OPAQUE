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


from typing import Dict, Optional

from PySide6.QtWidgets import QToolBar, QToolButton, QWidget, QApplication
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPalette

from opaque.core.presenter import BasePresenter


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
        self.setObjectName("main_toolbar")
        self.setMovable(True)
        self.setFloatable(True)

        self._button_map: Dict[BasePresenter, QToolButton] = {}
        self._window_map: Dict[QToolButton, BasePresenter] = {}
        self._active_button: Optional[QToolButton] = None
        self._current_highlight_style: str = ""

        self._setup_default_buttons()
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

    def add_feature(self, feature: BasePresenter) -> None:
        """
        Adds a feature to the toolbar, creating a button and connecting signals.

        Args:
            feature_window (BaseFeatureWindow): The feature window instance to add.
        """
        button = QToolButton()
        button.setText(self.tr(feature.model.feature_name()))
        button.setToolTip(self.tr(feature.model.feature_description()))
        button.setIcon(feature.model.feature_icon())
        button.setIconSize(QSize(24, 24))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setMinimumSize(70, 0)

        self.addWidget(button)

        self._button_map[feature] = button
        self._window_map[button] = feature

        # --- Connect signals and slots ---

        # 1. Click button -> Toggle window visibility
        button.clicked.connect(feature.view.openClose)

        # 2. Window is shown -> Highlight button
        feature.view.windowOpen.connect(lambda: self._set_active(button))

        # 3. Window is focused -> Highlight button
        feature.view.windowFocused.connect(lambda: self._set_active(button))

        # 4. Window is unfocused -> Highlight button
        # feature_window.windowUnfocused.connect(lambda: self._set_inactive(button))

        # 5. Window is closed -> Un-highlight button
        feature.view.windowClosed.connect(lambda: self._set_inactive(button))

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

    def update_theme(self) -> None:
        """
        Public method to update the toolbar when theme changes.
        Called by the main application when a new theme is applied.
        """
        self._update_highlight_style()

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
