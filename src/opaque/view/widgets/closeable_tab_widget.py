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

from typing import Optional, Dict, Any, Callable, Type
from PySide6.QtWidgets import (
    QWidget, QTabWidget, QVBoxLayout,
    QInputDialog, QMessageBox, QLabel, QTabBar
)
from PySide6.QtCore import Signal


class CloseableTabWidget(QWidget):
    """
    A generic closeable tab widget that can manage multiple widget instances.
    Each tab can contain any type of QWidget and can be independently managed.

    Features:
    - Closeable tabs with confirmation
    - Renameable tabs (double-click to rename)
    - "+" tab for adding new tabs
    - Movable tabs
    - Minimum tab requirement (at least one tab must remain)
    - Workspace save/load support
    """

    # Signals
    currentTabChanged = Signal(int)  # Emitted when current tab changes
    tabAdded = Signal(int, str)      # Emitted when tab is added (index, name)
    # Emitted when tab is removed (index, name)
    tabRemoved = Signal(int, str)
    # Emitted when tab is renamed (index, old_name, new_name)
    tabRenamed = Signal(int, str, str)

    def __init__(
        self,
        widget_factory: Optional[Callable[[], QWidget]] = None,
        widget_type: Optional[Type[QWidget]] = None,
        default_tab_name: str = "Tab",
        minimum_tabs: int = 1,
        show_plus_tab: bool = True,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize the closeable tab widget.

        Args:
            widget_factory: Function that creates new widget instances for tabs
            widget_type: Type of widget to create (alternative to widget_factory)
            default_tab_name: Default name for new tabs
            minimum_tabs: Minimum number of tabs that must remain open
            show_plus_tab: Whether to show the "+" tab for adding new tabs
            parent: Parent widget
        """
        super().__init__(parent=parent)

        self._widget_factory = widget_factory
        self._widget_type = widget_type
        self._default_tab_name = default_tab_name
        self._minimum_tabs = max(1, minimum_tabs)
        self._show_plus_tab = show_plus_tab
        self._tab_counter = 0
        self._current_widget = None
        self._removing_tab = False  # Flag to prevent dialog during tab removal

        # Validate factory/type parameters
        if not widget_factory and not widget_type:
            raise ValueError(
                "Either widget_factory or widget_type must be provided")

        # Create factory function if only type is provided
        if not widget_factory and widget_type:
            self._widget_factory = lambda: widget_type()

        self._setup_ui()
        self._setup_connections()

        # Create initial tab(s)
        if self._minimum_tabs > 0:
            for i in range(self._minimum_tabs):
                self.add_tab(f"{self._default_tab_name} {i + 1}")

    def _setup_ui(self):
        """Set up the user interface."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        main_layout.addWidget(self.tab_widget)

        # Add plus tab if enabled
        if self._show_plus_tab:
            self._add_plus_tab()

    def _setup_connections(self):
        """Set up signal connections."""
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.tab_widget.tabCloseRequested.connect(self.remove_tab)
        self.tab_widget.tabBar().tabBarDoubleClicked.connect(self._on_tab_double_clicked)

    def _create_widget(self) -> QWidget:
        """Create a new widget instance using the factory function."""
        try:
            if self._widget_factory is not None:
                return self._widget_factory()
            else:
                # Fallback to empty widget if no factory
                widget = QWidget()
                layout = QVBoxLayout(widget)
                layout.addWidget(QLabel("No widget factory provided"))
                return widget
        except Exception as e:
            # Fallback to empty widget if factory fails
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.addWidget(QLabel(f"Error creating widget: {str(e)}"))
            return widget

    def add_tab(self, name: Optional[str] = None, widget: Optional[QWidget] = None) -> int:
        """
        Add a new tab with a widget instance.

        Args:
            name: Name for the new tab. If None, a default name will be generated.
            widget: Widget to add. If None, will use the factory to create one.

        Returns:
            Index of the newly created tab
        """
        # Create widget if not provided
        if widget is None:
            widget = self._create_widget()

        # Generate name if not provided
        self._tab_counter += 1
        if name is None:
            name = f"{self._default_tab_name} {self._tab_counter}"

        # Find plus tab index and insert before it
        plus_tab_index = -1
        if self._show_plus_tab:
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == "+":
                    plus_tab_index = i
                    break

        # Insert tab before plus tab, or add at end if no plus tab
        if plus_tab_index >= 0:
            index = self.tab_widget.insertTab(plus_tab_index, widget, name)
        else:
            index = self.tab_widget.addTab(widget, name)

        # Set as current tab
        self.tab_widget.setCurrentIndex(index)
        self._current_widget = widget

        # Emit signal
        self.tabAdded.emit(index, name)

        return index

    def remove_tab(self, index: int) -> bool:
        """
        Remove a tab at the specified index.

        Args:
            index: Index of the tab to remove

        Returns:
            True if tab was removed, False otherwise
        """
        # Don't allow removing the plus tab
        if index >= 0 and self._show_plus_tab and self.tab_widget.tabText(index) == "+":
            return False

        # Count real tabs (excluding plus tab)
        real_tab_count = self._get_real_tab_count()

        if real_tab_count <= self._minimum_tabs:
            QMessageBox.warning(
                self,
                "Cannot Remove Tab",
                f"At least {self._minimum_tabs} tab(s) must remain open."
            )
            return False

        # Set flag to prevent dialog during tab removal
        self._removing_tab = True

        try:
            # Get tab name before removal
            tab_name = self.tab_widget.tabText(index)

            # Get the widget and clean up
            widget = self.tab_widget.widget(index)
            if widget:
                widget.deleteLater()

            # Remove the tab
            self.tab_widget.removeTab(index)

            # Update current widget reference
            self._update_current_widget()

            # Emit signal
            self.tabRemoved.emit(index, tab_name)

            return True

        finally:
            # Clear the flag
            self._removing_tab = False

    def rename_tab(self, index: int, new_name: str) -> bool:
        """
        Rename a tab at the specified index.

        Args:
            index: Index of the tab to rename
            new_name: New name for the tab

        Returns:
            True if tab was renamed, False otherwise
        """
        if not (0 <= index < self.tab_widget.count()):
            return False

        current_name = self.tab_widget.tabText(index)

        # Don't allow renaming the plus tab
        if self._show_plus_tab and current_name == "+":
            return False

        new_name = new_name.strip()
        if not new_name:
            return False

        if not self._is_tab_name_unique(new_name, exclude_index=index):
            QMessageBox.warning(
                self,
                "Duplicate Name",
                f"A tab with the name '{new_name}' already exists. Please choose a different name."
            )
            return False

        self.tab_widget.setTabText(index, new_name)
        self.tabRenamed.emit(index, current_name, new_name)
        return True

    def _get_real_tab_count(self) -> int:
        """Get the number of real tabs (excluding plus tab)."""
        count = self.tab_widget.count()
        if self._show_plus_tab:
            for i in range(count):
                if self.tab_widget.tabText(i) == "+":
                    count -= 1
                    break
        return count

    def _is_tab_name_unique(self, name: str, exclude_index: int = -1) -> bool:
        """Check if a tab name is unique."""
        name = name.strip()
        if not name or (self._show_plus_tab and name == "+"):
            return False

        for i in range(self.tab_widget.count()):
            if i != exclude_index and self.tab_widget.tabText(i) == name:
                return False
        return True

    def _add_plus_tab(self):
        """Add the '+' tab for creating new tabs."""
        if not self._show_plus_tab:
            return

        # Create an empty widget for the plus tab
        plus_widget = QWidget()
        plus_layout = QVBoxLayout(plus_widget)
        plus_layout.addWidget(QLabel("Click the '+' tab to add a new tab"))

        # Add the plus tab
        self.tab_widget.addTab(plus_widget, "+")

        # Make the plus tab non-closable by removing the close button
        plus_index = self.tab_widget.count() - 1
        self.tab_widget.tabBar().setTabButton(
            plus_index, QTabBar.ButtonPosition.RightSide, None)

    def _update_current_widget(self):
        """Update the current widget reference after tab changes."""
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            self._current_widget = self.tab_widget.widget(current_index)
            # If current tab is plus tab, switch to last real tab
            if self._show_plus_tab and self.tab_widget.tabText(current_index) == "+":
                for i in range(self.tab_widget.count() - 1, -1, -1):
                    if self.tab_widget.tabText(i) != "+":
                        self.tab_widget.setCurrentIndex(i)
                        self._current_widget = self.tab_widget.widget(i)
                        break
        else:
            self._current_widget = None

    def _on_tab_changed(self, index: int):
        """Handle tab change events."""
        # Check if plus tab was clicked
        if (index >= 0 and self._show_plus_tab and
                self.tab_widget.tabText(index) == "+" and not self._removing_tab):
            self._show_add_tab_dialog()
            return

        self._update_current_widget()
        self.currentTabChanged.emit(index)

    def _on_tab_double_clicked(self, index: int):
        """Handle double-click on tab to rename it."""
        if index < 0:
            return

        current_name = self.tab_widget.tabText(index)

        # Don't allow renaming the plus tab
        if self._show_plus_tab and current_name == "+":
            return

        while True:
            name, ok = QInputDialog.getText(
                self,
                'Rename Tab',
                'Enter new tab name:',
                text=current_name
            )

            if not ok:
                return

            if self.rename_tab(index, name):
                break

    def _show_add_tab_dialog(self):
        """Show dialog to add a new tab with custom name."""
        name, ok = QInputDialog.getText(
            self,
            'Add New Tab',
            'Enter tab name:',
            text=f"{self._default_tab_name} {self._tab_counter + 1}"
        )

        if not ok:
            # Switch back to previous tab
            self._update_current_widget()
            return

        name = name.strip()
        if not name:
            QMessageBox.warning(
                self,
                "Invalid Name",
                "Tab name cannot be empty."
            )
            self._update_current_widget()
            return

        if not self._is_tab_name_unique(name):
            QMessageBox.warning(
                self,
                "Duplicate Name",
                f"A tab with the name '{name}' already exists. Please choose a different name."
            )
            self._update_current_widget()
            return

        self.add_tab(name)

    # Public API methods

    def get_current_widget(self) -> Optional[QWidget]:
        """Get the currently active widget."""
        if (self._current_widget and
            self._show_plus_tab and
            isinstance(self._current_widget.parent(), QWidget) and
                self.tab_widget.tabText(self.tab_widget.currentIndex()) == "+"):
            return None
        return self._current_widget

    def get_widget_at_index(self, index: int) -> Optional[QWidget]:
        """Get the widget at the specified tab index."""
        if 0 <= index < self.tab_widget.count():
            widget = self.tab_widget.widget(index)
            # Don't return plus tab widget
            if self._show_plus_tab and self.tab_widget.tabText(index) == "+":
                return None
            return widget
        return None

    def get_tab_count(self) -> int:
        """Get the number of real tabs (excluding plus tab)."""
        return self._get_real_tab_count()

    def set_current_tab(self, index: int) -> bool:
        """Set the current tab by index."""
        if 0 <= index < self.tab_widget.count():
            # Don't allow selecting plus tab directly
            if self._show_plus_tab and self.tab_widget.tabText(index) == "+":
                return False
            self.tab_widget.setCurrentIndex(index)
            return True
        return False

    def get_tab_name(self, index: int) -> Optional[str]:
        """Get the name of the tab at the specified index."""
        if 0 <= index < self.tab_widget.count():
            name = self.tab_widget.tabText(index)
            if self._show_plus_tab and name == "+":
                return None
            return name
        return None

    def set_tab_name(self, index: int, name: str) -> bool:
        """Set the name of the tab at the specified index."""
        return self.rename_tab(index, name)

    # Workspace management

    def get_workspace_data(self) -> Dict[str, Any]:
        """Get workspace data for saving."""
        tabs_data = []
        for i in range(self.tab_widget.count()):
            tab_name = self.tab_widget.tabText(i)
            # Skip plus tab
            if self._show_plus_tab and tab_name == "+":
                continue

            widget = self.tab_widget.widget(i)
            tab_data: Dict[str, Any] = {
                'name': tab_name,
                'widget_type': widget.__class__.__name__ if widget else None
            }

            # If widget has workspace methods, call them
            if widget and hasattr(widget, 'get_workspace_data'):
                try:
                    workspace_method = getattr(widget, 'get_workspace_data')
                    if callable(workspace_method):
                        tab_data['widget_data'] = workspace_method()
                except Exception as e:
                    print(f"Error getting workspace data from widget: {e}")

            tabs_data.append(tab_data)

        return {
            'tabs': tabs_data,
            'current_tab': self.tab_widget.currentIndex(),
            'tab_counter': self._tab_counter
        }

    def load_workspace_data(self, data: Dict[str, Any]) -> bool:
        """Load workspace data."""
        if not data or 'tabs' not in data:
            return False

        try:
            # Clear existing tabs except plus tab
            while self._get_real_tab_count() > 0:
                for i in range(self.tab_widget.count()):
                    if not (self._show_plus_tab and self.tab_widget.tabText(i) == "+"):
                        widget = self.tab_widget.widget(i)
                        if widget:
                            widget.deleteLater()
                        self.tab_widget.removeTab(i)
                        break

            # Restore tab counter
            if 'tab_counter' in data:
                self._tab_counter = data['tab_counter']

            # Restore tabs
            for tab_data in data['tabs']:
                tab_name = tab_data.get(
                    'name', f"{self._default_tab_name} {self._tab_counter + 1}")

                # Create widget
                widget = self._create_widget()

                # Load widget data if available
                if hasattr(widget, 'load_workspace_data') and 'widget_data' in tab_data:
                    try:
                        load_method = getattr(widget, 'load_workspace_data')
                        if callable(load_method):
                            load_method(tab_data['widget_data'])
                    except Exception as e:
                        print(f"Error loading workspace data to widget: {e}")

                # Add tab
                self.add_tab(tab_name, widget)

            # Restore current tab
            if 'current_tab' in data:
                current_tab = data['current_tab']
                if 0 <= current_tab < self.tab_widget.count():
                    self.set_current_tab(current_tab)

            return True

        except Exception as e:
            print(f"Error loading workspace data: {e}")
            # Ensure at least minimum tabs exist
            while self._get_real_tab_count() < self._minimum_tabs:
                self.add_tab()
            return False
