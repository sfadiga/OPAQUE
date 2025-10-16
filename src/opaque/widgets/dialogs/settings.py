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


from typing import List, Dict, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QSplitter,
    QListWidget, QListWidgetItem, QScrollArea, QWidget, QDialogButtonBox, QFormLayout,
    QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox, QMessageBox, QLabel
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from opaque.core.view import BaseView
from opaque.managers.settings_manager import SettingsManager
from opaque.managers.theme_manager import ThemeManager
from opaque.widgets.color_picker import ColorPicker


class SettingsDialog(QDialog):
    def __init__(self, windows_with_settings: List[BaseView], settings_manager: SettingsManager, theme_manager: ThemeManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Settings"))
        self.setMinimumSize(800, 600)
        self.windows: Dict[str, BaseView] = {
            w.feature_id: w for w in windows_with_settings}
        self.settings_manager = settings_manager
        self.theme_manager: ThemeManager = theme_manager
        # To hold a reference to the combo box
        self.theme_combo_box: Optional[QComboBox] = None
        self.language_combo_box: Optional[QComboBox] = None

        # Cache for settings field labels for searching
        self._settings_cache: Dict[str, List[str]] = {}
        self._build_settings_cache()

        # Store all form widgets for highlighting search results
        self._current_form_widgets: Dict[str, QWidget] = {}

        # Main layout
        layout = QVBoxLayout(self)

        # Search bar
        self.search_bar: QLineEdit = QLineEdit()
        self.search_bar.setPlaceholderText(self.tr("Search settings..."))
        self.search_bar.textChanged.connect(self._filter_groups)
        layout.addWidget(self.search_bar)

        # Splitter for the main area
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # Left panel: List of settings groups
        self.groups_list: QListWidget = QListWidget()
        self.groups_list.itemSelectionChanged.connect(self._on_group_selected)
        splitter.addWidget(self.groups_list)

        # Right panel: Scroll area for the settings widgets
        self.scroll_area: QScrollArea = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        # Container for the dynamic form
        self.settings_widget_container: QWidget = QWidget()
        self.scroll_area.setWidget(self.settings_widget_container)
        splitter.addWidget(self.scroll_area)

        # Dialog buttons (OK, Cancel, Apply)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.Apply).clicked.connect(
            self._apply_settings)
        layout.addWidget(self.button_box)

        # Set initial splitter sizes
        splitter.setSizes([150, 450])

        self._populate_groups_list()
        if self.groups_list.count() > 0:
            self.groups_list.setCurrentRow(0)

    def accept(self) -> None:
        """Apply settings and accept the dialog."""
        self._apply_settings(show_success_message=False)
        super().accept()

    def _apply_settings(self, show_success_message: bool = True) -> None:
        """Saves all current settings."""
        for feature_id, window in self.windows.items():
            if hasattr(window, 'model') and window.model:
                self.settings_manager.save_feature_settings(
                    feature_id, window.model
                )

        # Special handling for application theme
        app_settings_window = self.windows.get('application')
        if app_settings_window and hasattr(app_settings_window, 'model') and hasattr(app_settings_window.model, 'theme'):
            self.theme_manager.apply_theme(
                str(app_settings_window.model.theme))

        if show_success_message:
            # Inform user of success
            msg_box = QMessageBox(self)
            msg_box.setText(self.tr("Settings applied successfully."))
            msg_box.setIcon(QMessageBox.Information)
            msg_box.exec()

    def _build_settings_cache(self) -> None:
        """Build a cache of all settings field labels for searching."""
        for feature_id, window in self.windows.items():
            if hasattr(window, 'model') and window.model:
                target_model = window.model
                if hasattr(target_model, 'get_fields'):
                    fields = target_model.get_fields()
                    labels = []
                    for name, field in fields.items():
                        if hasattr(field, 'is_setting') and field.is_setting:
                            label = field.description or name
                            labels.append(label.lower())
                    if labels:
                        self._settings_cache[feature_id] = labels

    def _populate_groups_list(self) -> None:
        """Populates the list using window titles for display."""
        for feature_id, window in self.windows.items():
            if feature_id in self._settings_cache:
                # Get feature name from model if available, otherwise use a default
                if hasattr(window, 'model') and window.model and hasattr(window.model, 'feature_name'):
                    name = window.model.feature_name()
                else:
                    name = feature_id.replace("_", " ").title()

                item = QListWidgetItem(name)
                item.setData(Qt.UserRole, feature_id)  # Store the unique ID
                self.groups_list.addItem(item)

    def _filter_groups(self, text: str) -> None:
        """
        Filters the settings groups based on the search text.
        Searches both group names and individual setting labels.
        """
        search_text = text.lower().strip()

        if not search_text:
            # Show all items if search is empty
            for i in range(self.groups_list.count()):
                self.groups_list.item(i).setHidden(False)
            # Also clear any highlighting in the current form
            self._clear_search_highlighting()
            return

        first_match_index = -1
        current_selection_matches = False

        # Check each group
        for i in range(self.groups_list.count()):
            item = self.groups_list.item(i)
            feature_id = item.data(Qt.UserRole)

            # Check if search text matches group name
            group_match = search_text in item.text().lower()

            # Check if search text matches any setting label in this group
            settings_match = False
            if feature_id in self._settings_cache:
                for label in self._settings_cache[feature_id]:
                    if search_text in label:
                        settings_match = True
                        break

            # Show item if either group name or any setting matches
            matches = group_match or settings_match
            item.setHidden(not matches)

            # Track first visible match
            if matches and first_match_index == -1:
                first_match_index = i

            # Check if current selection matches
            if item.isSelected() and matches:
                current_selection_matches = True

        # If current selection doesn't match but we have matches, select the first match
        if not current_selection_matches and first_match_index >= 0:
            self.groups_list.setCurrentRow(first_match_index)

        # Highlight matching fields in the current form
        self._highlight_matching_fields(search_text)

    def _clear_search_highlighting(self) -> None:
        """Clear any search result highlighting in the current form."""
        for label_widget in self._current_form_widgets.values():
            if isinstance(label_widget, QLabel):
                # Reset to normal font
                font = label_widget.font()
                font.setBold(False)
                label_widget.setFont(font)
                label_widget.setStyleSheet("")

    def _highlight_matching_fields(self, search_text: str) -> None:
        """Highlight fields in the current form that match the search text."""
        for field_name, label_widget in self._current_form_widgets.items():
            if isinstance(label_widget, QLabel):
                if search_text in field_name.lower():
                    # Highlight matching labels
                    font = label_widget.font()
                    font.setBold(True)
                    label_widget.setFont(font)
                    label_widget.setStyleSheet("color: palette(highlight);")
                else:
                    # Reset non-matching labels
                    font = label_widget.font()
                    font.setBold(False)
                    label_widget.setFont(font)
                    label_widget.setStyleSheet("")

    def _on_group_selected(self) -> None:
        """Called when a group is selected in the list. Generates the form."""
        selected_items = self.groups_list.selectedItems()
        if not selected_items:
            self.scroll_area.setWidget(QWidget())
            return

        feature_id = selected_items[0].data(Qt.UserRole)
        window = self.windows.get(feature_id)

        if not window or not hasattr(window, 'model') or not window.model:
            return

        target_model = window.model

        # Clear previous form widgets tracking
        self._current_form_widgets.clear()

        # Create a new container widget and form layout
        container = QWidget()
        layout = QFormLayout()
        container.setLayout(layout)

        # Dynamically generate widgets based on field annotations
        if hasattr(target_model, 'get_fields'):
            fields = target_model.get_fields()
            for name, field in fields.items():
                if not hasattr(field, 'is_setting') or not field.is_setting:
                    continue

                current_value = getattr(target_model, name)
                label_text = self.tr(field.description) or name
                label_widget = QLabel(label_text)
                self._current_form_widgets[label_text.lower()] = label_widget

                widget = None
                if hasattr(field, 'ui_type') and field.ui_type == "checkbox":
                    widget = QCheckBox()
                    widget.setChecked(bool(current_value))
                    widget.stateChanged.connect(
                        lambda state, model=target_model, name=name: setattr(
                            model, name, bool(state == Qt.Checked))
                    )
                elif hasattr(field, 'ui_type') and field.ui_type == "spinbox":
                    widget = QSpinBox()
                    if hasattr(field, 'min_value') and field.min_value is not None:
                        widget.setMinimum(field.min_value)
                    if hasattr(field, 'max_value') and field.max_value is not None:
                        widget.setMaximum(field.max_value)
                    widget.setValue(int(current_value))
                    widget.valueChanged.connect(
                        lambda value, model=target_model, name=name: setattr(
                            model, name, value)
                    )
                elif hasattr(field, 'ui_type') and field.ui_type == "doublespinbox":
                    widget = QDoubleSpinBox()
                    if hasattr(field, 'min_value') and field.min_value is not None:
                        widget.setMinimum(field.min_value)
                    if hasattr(field, 'max_value') and field.max_value is not None:
                        widget.setMaximum(field.max_value)
                    widget.setValue(float(current_value))
                    widget.valueChanged.connect(
                        lambda value, model=target_model, name=name: setattr(
                            model, name, value)
                    )
                elif (hasattr(field, 'ui_type') and field.ui_type == "combobox") or (hasattr(field, 'choices') and field.choices):
                    widget = QComboBox()
                    if hasattr(field, 'choices') and field.choices:
                        widget.addItems([str(c) for c in field.choices])
                    widget.setCurrentText(str(current_value))
                    widget.currentTextChanged.connect(
                        lambda text, model=target_model, name=name: setattr(
                            model, name, text)
                    )
                elif hasattr(field, 'ui_type') and field.ui_type == "color_picker":
                    widget = ColorPicker(initial_color=str(current_value))
                    widget.colorChanged.connect(
                        lambda color, model=target_model, name=name: setattr(
                            model, name, color)
                    )
                else:  # Default to QLineEdit for "text"
                    widget = QLineEdit(str(current_value))
                    widget.textChanged.connect(
                        lambda text, model=target_model, name=name: setattr(
                            model, name, text)
                    )

                if widget:
                    layout.addRow(label_widget, widget)

        self.scroll_area.setWidget(container)
