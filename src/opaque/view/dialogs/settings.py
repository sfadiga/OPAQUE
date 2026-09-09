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


from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QSplitter,
    QListWidget, QListWidgetItem, QScrollArea, QWidget, QDialogButtonBox, QFormLayout,
    QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox, QLabel
)
from PySide6.QtCore import Qt

from opaque.presenters.presenter import BasePresenter
from opaque.services.service import ServiceLocator
from opaque.services.settings_service import SettingsService

from opaque.view.widgets.color_picker import ColorPicker
from opaque.models.annotations import Field, UIType


class SettingsDialog(QDialog):
    def __init__(self, presenters: List[BasePresenter], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setWindowTitle(self.tr("Settings"))
        self.setMinimumSize(800, 600)

        self.features: Dict[str, BasePresenter] = {
            p.feature_id: p for p in presenters}

        self.settings_service: SettingsService = ServiceLocator.get_service("settings")
        if not self.settings_service:
            raise RuntimeError("SettingsService not found.")

        # Cache for settings field labels for searching
        self._settings_cache: Dict[str, List[str]] = {}
        self._build_settings_cache()

        # Store all form widgets for highlighting search results
        self._current_form_widgets: Dict[str, QWidget] = {}

        # Edits live here until the user presses OK or Apply. Writing straight
        # into the model made Cancel unreliable, because a value that came
        # from a field default was never on disk to reload.
        # Shape: {feature_id: {field_name: new_value}}
        self._pending_values: Dict[str, Dict[str, Any]] = {}

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
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply |
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(
            self._apply_settings)
        self.button_box.button(
            QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(
                self._restore_defaults)

        # A quiet status line. Applying settings is a routine action, so it
        # gets a line of text and not a modal box.
        self.status_label: QLabel = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        layout.addWidget(self.button_box)

        # Set initial splitter sizes
        splitter.setSizes([150, 450])

        self._populate_groups_list()
        if self.groups_list.count() > 0:
            self.groups_list.setCurrentRow(0)

    def _record_pending(self, feature_id: str, field_name: str, value: Any) -> None:
        """
        Store one edited value. Nothing reaches the model until Apply.

        The value is converted by the field first. A widget hands back
        whatever type it likes, and a combo box always hands back text, so
        without this step a float arrived as an int and a typed choice
        arrived as a string that the model setter then rejected.
        """
        field = self._field_for(feature_id, field_name)
        if field is not None:
            try:
                value = field.coerce(value)
            except (TypeError, ValueError):
                self.status_label.setText(
                    self.tr("Value not accepted for: ") + field_name)
                return

        self._pending_values.setdefault(feature_id, {})[field_name] = value

    def _field_for(self, feature_id: str, field_name: str) -> Optional[Field]:
        """Return one Field declaration, or None when the name is unknown."""
        presenter = self.features.get(feature_id)
        if presenter is None:
            return None
        return type(presenter.model).get_fields().get(field_name)

    def pending_value(self, feature_id: str, field_name: str) -> Any:
        """Return one pending value, or None when the field was not edited."""
        return self._pending_values.get(feature_id, {}).get(field_name)

    def _effective_value(
            self, feature_id: str, field_name: str, model: Any) -> Any:
        """
        Return the value the form must show for one field.

        A queued edit wins over the stored value. Restore Defaults queues
        without writing, and switching group redraws the form, so a redraw
        that read only the model threw away everything the user had done and
        made Restore Defaults look like it had failed.
        """
        pending = self._pending_values.get(feature_id, {})
        if field_name in pending:
            return pending[field_name]
        return getattr(model, field_name)

    def has_pending_changes(self) -> bool:
        """Return True while at least one edit is waiting to be committed."""
        return any(self._pending_values.values())

    def accept(self) -> None:
        """Apply settings and accept the dialog."""
        self._apply_settings()
        super().accept()

    def reject(self) -> None:
        """Discard every pending edit and close.

        No disk reload is needed. Nothing was written to a model, so there is
        nothing to undo.
        """
        self._pending_values.clear()
        super().reject()

    def _apply_settings(self) -> None:
        """
        Write the pending edits into the models, then persist them.

        A value that the field rejects is skipped and reported, so one bad
        entry cannot stop the rest of the dialog from saving.
        """
        rejected: List[str] = []

        for feature_id, changes in self._pending_values.items():
            presenter = self.features.get(feature_id)
            if presenter is None:
                continue
            for field_name, value in changes.items():
                try:
                    setattr(presenter.model, field_name, value)
                except ValueError:
                    rejected.append(field_name)

        self._pending_values.clear()

        for feature_id, presenter in self.features.items():
            self.settings_service.save_feature_settings(
                feature_id, presenter.model)
            presenter.apply_settings()

        if rejected:
            self.status_label.setText(
                self.tr("Not saved, value not allowed: ")
                + ", ".join(rejected))
        else:
            self.status_label.setText(self.tr("Settings applied."))

    def _restore_defaults(self) -> None:
        """
        Queue the declared default of every settings field.

        The values are queued, not written, so the user can still press Cancel
        after pressing Restore Defaults.
        """
        for feature_id, presenter in self.features.items():
            fields = type(presenter.model).get_fields()
            for name, field in fields.items():
                if not getattr(field, 'is_setting', False):
                    continue
                self._record_pending(feature_id, name, field.default)

        # Redraw the visible form so the widgets show the queued defaults.
        self._on_group_selected()

    def _build_settings_cache(self) -> None:
        """Build a cache of all settings field labels for searching."""
        for feature_id, presenter in self.features.items():
            target_model = presenter.model
            if not target_model:
                continue
            # Explicitly call get_fields on the class
            fields = type(target_model).get_fields()
            labels: list[str] = []
            for name, field in fields.items():
                if hasattr(field, 'is_setting') and field.is_setting:
                    label = field.description or name
                    labels.append(label.lower())
            # Cache even if empty, to know the feature was processed
            self._settings_cache[feature_id] = labels

    def _populate_groups_list(self) -> None:
        """Populates the list using window titles for display."""
        for feature_id, presenter in self.features.items():
            name = presenter.model.feature_name()
            icon = presenter.model.feature_icon()
            item = QListWidgetItem(icon, name)
            item.setData(Qt.ItemDataRole.UserRole, feature_id)
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
            self.status_label.setText("")
            return

        first_match_index = -1
        current_selection_matches = False

        # Check each group
        for i in range(self.groups_list.count()):
            item = self.groups_list.item(i)
            feature_id = item.data(Qt.ItemDataRole.UserRole)

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

        # Say how many groups matched. Without a count the user sees a shorter
        # list and cannot tell whether the search worked.
        matched = sum(
            0 if self.groups_list.item(i).isHidden() else 1
            for i in range(self.groups_list.count())
        )
        self.status_label.setText(
            self.tr("Matching groups: ") + str(matched))

    def _clear_search_highlighting(self) -> None:
        """Remove the search emphasis from every field label."""
        for label_widget in self._current_form_widgets.values():
            if isinstance(label_widget, QLabel):
                font = label_widget.font()
                font.setBold(False)
                label_widget.setFont(font)

    def _highlight_matching_fields(self, search_text: str) -> None:
        """
        Emphasise the field labels that match the search text.

        The emphasis is weight only. A colour would need a contrast check
        against whatever background the active theme paints, and the weight
        change already tells the user which row matched.
        """
        for field_name, label_widget in self._current_form_widgets.items():
            if isinstance(label_widget, QLabel):
                font = label_widget.font()
                font.setBold(search_text in field_name.lower())
                label_widget.setFont(font)

    def _on_group_selected(self) -> None:
        """Called when a group is selected in the list. Generates the form."""
        selected_items = self.groups_list.selectedItems()
        if not selected_items:
            self.scroll_area.setWidget(QWidget())
            return

        feature_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        presenter = self.features.get(feature_id, None)
        if not presenter:
            return
        target_model = presenter.model

        # Clear previous form widgets tracking
        self._current_form_widgets.clear()

        # Create a new container widget and form layout
        container = QWidget()
        layout = QFormLayout()
        container.setLayout(layout)

        # Dynamically generate widgets based on field annotations
        fields = type(target_model).get_fields()
        if not fields:
            return
        for name, field in fields.items():
            if not hasattr(field, 'is_setting') or not field.is_setting:
                continue

            current_value = self._effective_value(feature_id, name, target_model)
            # The description comes from a model field at run time. The model
            # that declares the field must call tr() on its own literal.
            label_text = field.description or name
            label_widget = QLabel(label_text)
            self._current_form_widgets[label_text.lower()] = label_widget

            widget = None
            if hasattr(field, 'ui_type') and field.ui_type == UIType.CHECKBOX:
                widget = QCheckBox()
                widget.setChecked(bool(current_value))
                # The 'stateChanged' signal emits an integer (0, 1, or 2).
                # We compare it to the value of the Qt.CheckState.Checked enum member.
                widget.stateChanged.connect(
                    lambda state, fid=feature_id, name=name: self._record_pending(
                        fid, name, state == Qt.CheckState.Checked.value)
                )
            elif hasattr(field, 'ui_type') and field.ui_type == UIType.SPINBOX:
                widget = QSpinBox()
                if hasattr(field, 'min_value') and field.min_value is not None:
                    widget.setMinimum(int(field.min_value))
                if hasattr(field, 'max_value') and field.max_value is not None:
                    widget.setMaximum(int(field.max_value))
                widget.setValue(int(current_value))
                widget.valueChanged.connect(
                    lambda value, fid=feature_id, name=name: self._record_pending(
                        fid, name, value)
                )
            elif hasattr(field, 'ui_type') and field.ui_type == UIType.DOUBLE_SPINBOX:
                widget = QDoubleSpinBox()
                if hasattr(field, 'min_value') and field.min_value is not None:
                    widget.setMinimum(field.min_value)
                if hasattr(field, 'max_value') and field.max_value is not None:
                    widget.setMaximum(field.max_value)
                widget.setValue(float(current_value))
                widget.valueChanged.connect(
                    lambda value, fid=feature_id, name=name: self._record_pending(
                        fid, name, value)
                )
            elif (field.ui_type in (UIType.COMBOBOX, UIType.DROPDOWN)
                    or field.choices):
                widget = QComboBox()
                # Each item carries the declared choice object as its data,
                # so the queued value keeps the type the field declared. The
                # display text alone loses it: "2" is not 2.
                for choice in (field.choices or []):
                    widget.addItem(field.display(choice), choice)
                index = widget.findText(field.display(current_value))
                if index >= 0:
                    widget.setCurrentIndex(index)
                widget.currentIndexChanged.connect(
                    lambda position, fid=feature_id, name=name,
                    combo=widget: self._record_pending(
                        fid, name, combo.itemData(position))
                )
            elif hasattr(field, 'ui_type') and field.ui_type == UIType.COLOR_PICKER:
                widget = ColorPicker(initial_color=str(current_value))
                widget.colorChanged.connect(
                    lambda color, fid=feature_id, name=name: self._record_pending(
                        fid, name, color)
                )
            else:  # Default to QLineEdit for "text"
                # field.display() is the inverse of field.coerce(). A list
                # shown as str(["a", "b"]) cannot be edited back into a list.
                widget = QLineEdit(field.display(current_value))
                widget.textChanged.connect(
                    lambda text, fid=feature_id, name=name: self._record_pending(
                        fid, name, text)
                )

            if widget:
                layout.addRow(label_widget, widget)

        self.scroll_area.setWidget(container)
