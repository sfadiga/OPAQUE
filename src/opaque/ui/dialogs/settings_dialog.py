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


from typing import List, Dict, Optional, Set

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QSplitter,
    QListWidget, QListWidgetItem, QScrollArea, QWidget, QDialogButtonBox, QFormLayout,
    QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox, QPushButton, QMessageBox, QHBoxLayout, QLabel
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..core.base_feature_window import BaseFeatureWindow
from ...managers.theme_manager import ThemeManager


class SettingsDialog(QDialog):
    def __init__(self, windows_with_settings: List[BaseFeatureWindow], theme_manager: ThemeManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Settings"))
        self.setMinimumSize(800, 600)
        self.windows: Dict[str, BaseFeatureWindow] = {
            w.feature_id: w for w in windows_with_settings}
        self.theme_manager: ThemeManager = theme_manager
        # To hold a reference to the combo box
        self.theme_combo_box: Optional[QComboBox] = None

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

        # Dialog buttons (OK, Cancel)
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Set initial splitter sizes
        splitter.setSizes([150, 450])

        self._populate_groups_list()
        if self.groups_list.count() > 0:
            self.groups_list.setCurrentRow(0)

    def _build_settings_cache(self) -> None:
        """Build a cache of all settings field labels for searching."""
        for feature_id, window in self.windows.items():
            if window.settings:
                fields = window.settings.get_fields()
                labels = []
                for name, field in fields.items():
                    label = field.description or name
                    labels.append(label.lower())
                self._settings_cache[feature_id] = labels

    def _populate_groups_list(self) -> None:
        """Populates the list using window titles for display."""
        for feature_id, window in self.windows.items():
            item = QListWidgetItem(window.windowTitle())
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

        if not window or not window.settings:
            return

        target_model = window.settings

        # Clear previous form widgets tracking
        self._current_form_widgets.clear()

        # Create a new container widget and form layout
        container = QWidget()
        layout = QFormLayout(container)

        # Dynamically generate widgets based on field type
        fields = target_model.get_fields()
        for name, field in fields.items():
            current_value = getattr(target_model, name)
            field_type = field.__class__.__name__

            label_text = self.tr(field.description) or name

            # Create a QLabel for the field (for search highlighting)
            label_widget = QLabel(label_text)
            self._current_form_widgets[label_text.lower()] = label_widget

            if field_type == 'BoolField':
                widget = QCheckBox()
                widget.setChecked(current_value)
                widget.stateChanged.connect(
                    lambda state, model=target_model, name=name: setattr(
                        model, name, state == Qt.Checked)
                )
                layout.addRow(label_widget, widget)

            elif field_type == 'StringField':
                widget = QLineEdit(str(current_value))
                widget.textChanged.connect(
                    lambda text, model=target_model, name=name: setattr(
                        model, name, text)
                )
                layout.addRow(label_widget, widget)

            elif field_type == 'IntField':
                widget = QSpinBox()
                if field.min_value is not None:
                    widget.setMinimum(field.min_value)
                if field.max_value is not None:
                    widget.setMaximum(field.max_value)
                widget.setValue(current_value)
                widget.valueChanged.connect(
                    lambda value, model=target_model, name=name: setattr(
                        model, name, value)
                )
                layout.addRow(label_widget, widget)

            elif field_type == 'FloatField':
                widget = QDoubleSpinBox()
                if field.min_value is not None:
                    widget.setMinimum(field.min_value)
                if field.max_value is not None:
                    widget.setMaximum(field.max_value)
                widget.setValue(current_value)
                widget.valueChanged.connect(
                    lambda value, model=target_model, name=name: setattr(
                        model, name, value)
                )
                layout.addRow(label_widget, widget)

            elif field_type == 'ChoiceField':
                combo_box = QComboBox()
                if field.choices:
                    combo_box.addItems(field.choices)
                combo_box.setCurrentText(str(current_value))

                # For global settings, don't connect directly - wait for Apply
                if feature_id == 'global':
                    # Store reference for Apply button
                    if name == 'theme':
                        self.theme_combo_box = combo_box
                    elif name == 'language':
                        self.language_combo_box = combo_box
                    layout.addRow(label_widget, combo_box)
                else:
                    # For feature settings, connect directly
                    combo_box.currentTextChanged.connect(
                        lambda text, model=target_model, name=name: setattr(
                            model, name, text)
                    )
                    layout.addRow(label_widget, combo_box)

        # Add Apply button for global settings
        if feature_id == 'global':
            apply_button = QPushButton(self.tr("Apply Global Settings"))
            apply_button.clicked.connect(self._on_apply_global_settings)
            layout.addRow("", apply_button)

        self.scroll_area.setWidget(container)

    def _on_apply_global_settings(self) -> None:
        """Applies global settings for preview and asks for confirmation."""
        global_window = self.windows.get('global')
        if not global_window or not global_window.settings:
            return

        # Store original values
        original_theme = global_window.settings.theme if hasattr(
            global_window.settings, 'theme') else None
        original_language = global_window.settings.language if hasattr(
            global_window.settings, 'language') else None

        # Apply new values temporarily
        if hasattr(self, 'theme_combo_box') and self.theme_combo_box:
            new_theme = self.theme_combo_box.currentText()
            if original_theme and new_theme != original_theme:
                self.theme_manager.apply_theme(new_theme)
                # Update toolbar highlighting to match new theme
                if self.parent() and hasattr(self.parent(), 'toolbar'):
                    self.parent().toolbar.update_theme()

        if hasattr(self, 'language_combo_box') and self.language_combo_box:
            new_language = self.language_combo_box.currentText()
            # Language change would be applied here in the future

        # Ask for confirmation
        reply = QMessageBox.question(
            self,
            self.tr('Apply Global Settings'),
            self.tr('Do you want to keep these global settings?'),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Update the model so changes persist
            if hasattr(self, 'theme_combo_box') and self.theme_combo_box:
                global_window.settings.theme = self.theme_combo_box.currentText()
            if hasattr(self, 'language_combo_box') and self.language_combo_box:
                global_window.settings.language = self.language_combo_box.currentText()
        else:
            # Revert changes
            if original_theme and hasattr(self, 'theme_combo_box') and self.theme_combo_box:
                self.theme_manager.apply_theme(original_theme)
                self.theme_combo_box.setCurrentText(original_theme)
                # Update toolbar highlighting to match reverted theme
                if self.parent() and hasattr(self.parent(), 'toolbar'):
                    self.parent().toolbar.update_theme()
            if original_language and hasattr(self, 'language_combo_box') and self.language_combo_box:
                self.language_combo_box.setCurrentText(original_language)
