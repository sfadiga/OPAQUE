# This Python file uses the following encoding: utf-8
"""Tests for the console widget."""

from datetime import datetime

from opaque.models.console_model import ConsoleOutputItem
from opaque.view.widgets.console_widget import ConsoleWidget

TIMESTAMP = datetime(2026, 9, 7, 12, 0, 0)


def _console_with_lines(qtbot, lines):
    """Build a console showing one plain line for each string in lines."""
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    # Without the timestamp prefix the block text is exactly the line text,
    # which keeps every assertion below readable.
    widget.show_timestamps_checkbox.setChecked(False)
    for text in lines:
        widget.add_output_item(ConsoleOutputItem("stdout", text, TIMESTAMP))
    return widget


def test_a_new_console_has_no_displayed_items(qtbot, light_palette_app):
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    assert widget.displayed_item_count() == 0


def test_each_added_item_records_a_block_number(qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha", "beta"])
    assert widget.displayed_item_count() == 2


def test_block_numbers_increase_with_each_item(qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha", "beta", "gamma"])
    numbers = widget.block_number_for_items()
    assert numbers == sorted(numbers)
    assert numbers[0] < numbers[-1]


def test_clearing_the_display_forgets_the_block_numbers(qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha", "beta"])
    widget.clear_display()
    assert widget.displayed_item_count() == 0


def test_a_multi_line_item_records_only_one_entry(qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["one\ntwo", "three"])
    numbers = widget.block_number_for_items()
    assert len(numbers) == 2
    assert numbers[1] - numbers[0] == 2
