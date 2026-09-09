# This Python file uses the following encoding: utf-8
"""Tests that the stored language setting reaches the translator."""

import json

from opaque.services.settings_service import stored_language


def test_no_file_gives_no_language(tmp_path):
    assert stored_language(tmp_path / "missing.json") == ""


def test_a_broken_file_gives_no_language(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{ broken", encoding="utf-8")
    assert stored_language(path) == ""


def test_a_stored_language_is_found_whatever_the_block_is_called(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"ApplicationPresenter": {"language": "fr"}}),
        encoding="utf-8")
    assert stored_language(path) == "fr"


def test_a_file_with_no_language_gives_no_language(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"demo": {"theme": "Dark"}}), encoding="utf-8")
    assert stored_language(path) == ""


def test_a_language_that_is_not_text_is_refused(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"demo": {"language": 7}}), encoding="utf-8")
    assert stored_language(path) == ""


def test_a_list_at_the_top_level_gives_no_language(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(["nonsense"]), encoding="utf-8")
    assert stored_language(path) == ""
