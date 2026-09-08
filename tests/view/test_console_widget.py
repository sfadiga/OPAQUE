# This Python file uses the following encoding: utf-8
"""Tests for the console widget."""

from datetime import datetime

from opaque.models.console_model import ConsoleOutputItem
from opaque.view.widgets.console_widget import ConsoleWidget
from opaque.view.theme import StatusRole, TypeScale, contrast_ratio, surface
from opaque.view.theme.contrast import TEXT_CONTRAST_MINIMUM

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


def test_the_console_does_not_hardcode_the_editor_palette(qtbot, light_palette_app):
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    sheet = widget.console_display.styleSheet()
    assert "#1e1e1e" not in sheet
    assert "#d4d4d4" not in sheet
    assert "#264f78" not in sheet


def test_the_console_background_comes_from_the_theme(qtbot, light_palette_app):
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    assert widget.background_colour == surface()
    assert surface() in widget.console_display.styleSheet()


def test_the_console_font_is_the_system_fixed_font(qtbot, light_palette_app):
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    assert widget.console_display.font().family() == TypeScale.mono().family()


def test_console_text_passes_contrast_on_a_light_theme(qtbot, light_palette_app):
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    assert contrast_ratio(
        widget.stdout_colour, widget.background_colour) >= TEXT_CONTRAST_MINIMUM
    assert contrast_ratio(
        widget.stderr_colour, widget.background_colour) >= TEXT_CONTRAST_MINIMUM


def test_console_text_passes_contrast_on_a_dark_theme(qtbot, dark_palette_app):
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    assert contrast_ratio(
        widget.stdout_colour, widget.background_colour) >= TEXT_CONTRAST_MINIMUM
    assert contrast_ratio(
        widget.stderr_colour, widget.background_colour) >= TEXT_CONTRAST_MINIMUM


def test_search_is_requested_when_the_user_presses_return(
        qtbot, light_palette_app):
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    with qtbot.waitSignal(widget.search_requested, timeout=1000):
        widget.search_input.returnPressed.emit()


def test_highlighting_selects_the_matching_line(qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha", "beta", "gamma"])
    widget.set_search_results([1])
    assert widget.console_display.textCursor().selectedText() == "beta"


def test_highlighting_a_later_match_moves_the_cursor_down(
        qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha", "beta", "gamma"])
    widget.set_search_results([0, 2])
    first = widget.console_display.textCursor().blockNumber()
    widget._search_next()
    second = widget.console_display.textCursor().blockNumber()
    assert second > first


def test_no_matches_leaves_the_cursor_alone(qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha", "beta"])
    before = widget.console_display.textCursor().position()
    widget.set_search_results([])
    assert widget.console_display.textCursor().position() == before
    assert widget.status_label.text() == "No matches found"


def test_the_status_shows_the_match_position(qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha", "beta", "gamma"])
    widget.set_search_results([0, 1, 2])
    assert widget.status_label.text() == "Match 1 of 3"


def test_next_wraps_to_the_first_match(qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha", "beta", "gamma"])
    widget.set_search_results([0, 1, 2])
    widget._search_next()
    widget._search_next()
    widget._search_next()
    assert widget.status_label.text() == "Match 1 of 3"


def test_previous_wraps_to_the_last_match(qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha", "beta", "gamma"])
    widget.set_search_results([0, 1, 2])
    widget._search_previous()
    assert widget.status_label.text() == "Match 3 of 3"


def test_navigation_does_nothing_without_matches(qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha"])
    widget.set_search_results([])
    widget._search_next()
    widget._search_previous()
    assert widget.status_label.text() == "No matches found"


def test_navigation_buttons_are_disabled_without_matches(
        qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha"])
    widget.set_search_results([])
    assert not widget.next_button.isEnabled()
    assert not widget.prev_button.isEnabled()
