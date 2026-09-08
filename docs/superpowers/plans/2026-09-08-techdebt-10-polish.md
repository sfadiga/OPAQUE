# Consistency and Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the last list: the modules that fail the deletion test, five copies of one number, the typos in shipped docstrings, the dead imports and dead code, the duplicated widgets, the file the settings service reads once per feature, and a type check and a lint run that both come back clean.

**Architecture:** Nothing here changes behaviour a user can see, which is why it comes last and why every task is guarded by a test that would catch a slip. Three kinds of work: deleting what nothing uses (`ApplicationView`, `flow.py`, the unread build templates, the unused imports, the commented-out code), concentrating what exists five times (the hit-target size, the version dictionary keys, the close button, the confirm helper), and making the tools that were never able to run pass cleanly (mypy could not get past `build_tools`; pylint was never in CI).

**Tech Stack:** Python 3.11, PySide6, pytest, mypy, pylint.

**Closes:** review 4.6, all of review Section 6, the remaining `print()` calls, and the CI leniency Plan 01 Task 7 left behind.

**Depends on:** Plan 08 for the module layout and Plan 09 for `build_tools`. This is the last plan. The interpreter is `uv run python`.

---

## A finding from Plan 01

Plan 01 Task 6 found that the Settings and Exit menu items had no usable
keyboard shortcut, because `QKeySequence.StandardKey.Preferences` and
`.Quit` produce nothing on Windows. It is fixed there. Two lessons apply
to the tasks in this plan:

1. A test that asserts a string is non-empty proves very little. The
   shortcut test passed for years while both shortcuts were multimedia
   key names. When a task here writes an accessibility check, assert the
   property the user depends on, not that a value exists.
2. `QKeySequence.StandardKey` is platform dependent and silently empty
   for some keys on some platforms. If a task in this plan adds a
   shortcut, give it an explicit portable string inside `self.tr()`. Qt
   maps `Ctrl` to Command on macOS, so one string serves every platform.

## Rules that apply to every task here

1. Read `docs/superpowers/plans/2026-09-08-techdebt-00-index.md` first. The rules there are binding.
2. Run every command from `C:\Users\sfadiga\sandro\opaque`.
3. Deleting code is a real change. Before you delete anything, run the `grep` the task gives you and paste the output into your report. If it finds a caller, stop and say so.
4. Identifiers use American spelling. Prose and comments keep the British spelling they have. Do not rewrite prose in a file you are not otherwise editing.
5. No task here may change what the application does. If a test has to change to accept a behaviour change, you have gone too far; report it and stop.

---

## File structure

| File | Responsibility |
|---|---|
| Delete: `src/opaque/view/app_view.py`, `src/opaque/view/layouts/flow.py`, `tests/view/test_flow_layout.py` | Nothing uses them. |
| Modify: `src/opaque/view/view.py` | `BaseView` gains the documented `setup_ui()` hook, so it is worth its own class. |
| Modify: `src/opaque/view/widgets/toolbar.py` | The pass-through wrappers go. |
| Create: `src/opaque/view/version_info_schema.py` | A `VersionInfo` dataclass replaces nine stringly-typed keys read in five places. |
| Modify: `src/opaque/view/theme/tokens.py` | One hit-target token. |
| Modify: `src/opaque/view/self_check.py`, `color_picker.py`, `notification_widget.py`, `version_info.py` | They read that token. |
| Modify: `src/opaque/services/version_service.py`, `src/opaque/shell.py` | `VersionManager` is registered once and reused. |
| Modify: about a dozen files | Typos, unused imports, commented-out code. |
| Create: `src/opaque/view/widgets/close_button.py` | One close button instead of three. |
| Modify: `src/opaque/services/settings_service.py` | Read the file once, not once per feature. |
| Modify: `.github/workflows/ci.yml` | mypy and pylint stop being allowed to fail. |
| Create: `tests/test_polish.py` | The guards for the whole plan. |

---

## Task 1: Delete the modules nothing uses

**Files:**
- Delete: `src/opaque/view/app_view.py`
- Delete: `src/opaque/view/layouts/flow.py`, `tests/view/test_flow_layout.py`
- Modify: `src/opaque/shell.py` (`_init_application_settings`)
- Modify: `src/opaque/view/widgets/toolbar.py:83-95`
- Test: `tests/test_polish.py`

`ApplicationView` is 22 lines: it adds nothing to `BaseView` and its one parameter is annotated `feature_id: str` while the caller passes the application object. `view/layouts/flow.py` has a test and no production caller. The toolbar has four one-line wrappers, one of them with the typo "peparator" in its docstring. All of them fail the deletion test: removing them costs the reader nothing.

- [ ] **Step 1: Prove nothing uses them**

```bash
grep -rn "ApplicationView\|app_view" --include=*.py --include=*.md src examples tests docs README.md CLAUDE.md
grep -rn "FlowLayout\|layouts.flow\|layouts import flow" --include=*.py --include=*.md src examples tests docs
grep -rn "add_separator\|connect_slot_to_button_click\|connect_signal_to_set_active\|connect_signal_to_set_inactive" --include=*.py src examples tests
```

Expected: `ApplicationView` appears only in `app_view.py` and in `_init_application_settings`. `FlowLayout` appears only in its own module and in `tests/view/test_flow_layout.py`. The four toolbar wrappers appear only where they are defined. Paste all three outputs into your report. A hit anywhere else means that item is used; leave that item alone and say which one.

- [ ] **Step 2: Write the failing test**

Create `tests/test_polish.py`:

```python
# This Python file uses the following encoding: utf-8
"""Guards for the consistency and polish work."""

import importlib
import pkgutil

import pytest

import opaque


def _modules():
    """Return every module name under the opaque package."""
    return [
        name for _finder, name, _is_package
        in pkgutil.walk_packages(opaque.__path__, prefix="opaque.")
    ]


@pytest.mark.parametrize("removed", [
    "opaque.view.app_view",
    "opaque.view.layouts.flow",
])
def test_a_deleted_module_is_gone(removed):
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(removed)


@pytest.mark.parametrize("wrapper", [
    "add_separator",
    "connect_slot_to_button_click",
    "connect_signal_to_set_active",
    "connect_signal_to_set_inactive",
])
def test_a_pass_through_wrapper_is_gone(wrapper):
    from opaque.view.widgets.toolbar import OpaqueMainToolbar

    assert not hasattr(OpaqueMainToolbar, wrapper)


def test_the_base_view_offers_the_documented_setup_hook():
    from opaque.view.view import BaseView

    assert callable(getattr(BaseView, "setup_ui", None))


def test_every_module_still_imports():
    for name in _modules():
        importlib.import_module(name)
```

- [ ] **Step 3: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_polish.py -q
```

Expected: the two `deleted_module` tests FAIL because the modules still import, the four `wrapper` tests FAIL, and `setup_hook` FAILS.

- [ ] **Step 4: Delete them**

```bash
git rm src/opaque/view/app_view.py src/opaque/view/layouts/flow.py tests/view/test_flow_layout.py
```

`flow.py` is not lost: it is in the git history, and the commit message says where to find it if a wrapping toolbar is ever wanted.

Then, in `src/opaque/shell.py`, `_init_application_settings` builds an `ApplicationView`. Replace it with the base class. Before:

```python
        model = ApplicationModel(self)
        view = ApplicationView(self)  # dummy only for settings
        presenter = ApplicationPresenter(model, view, self)
```

After (the context comes from Plan 08):

```python
        model = ApplicationModel(self._context)
        # The application settings have no window of their own. They need a
        # view only because BasePresenter takes one, so this is a plain
        # BaseView that is never shown. ApplicationView was a subclass that
        # added nothing and annotated its one parameter as a string.
        view = BaseView(self._context)
        presenter = ApplicationPresenter(model, view, self._context)
```

Remove the `from opaque.view.app_view import ApplicationView` import and add `BaseView` if Plan 08 Task 4 did not already import it.

Then delete the four wrappers from `src/opaque/view/widgets/toolbar.py`, lines 83 to 95. A caller that wanted a separator calls `addSeparator()`, which is the Qt method the wrapper called.

- [ ] **Step 5: Fix the other false annotation**

`OpaqueMdiSubWindow.__init__` annotates `fixed_size: Tuple[int, int] = None`. `None` is not a `Tuple[int, int]`, so the annotation is false in the same way `ApplicationView`'s was, and mypy reports it. In `src/opaque/view/widgets/mdi_window.py`, change it:

```python
        fixed_size: Optional[Tuple[int, int]] = None,
```

and add `Optional` to the `typing` import of that file if it is not there.

Add this to `tests/test_polish.py`:

```python
def test_no_default_of_none_is_annotated_as_a_value():
    import inspect
    import typing

    from opaque.view.widgets.mdi_window import OpaqueMdiSubWindow

    hints = typing.get_type_hints(OpaqueMdiSubWindow.__init__)
    signature = inspect.signature(OpaqueMdiSubWindow.__init__)

    for name, parameter in signature.parameters.items():
        if parameter.default is None and name in hints:
            assert type(None) in typing.get_args(hints[name]) or hints[
                name] is type(None), name
```

- [ ] **Step 6: Deepen BaseView**

`BaseView` now holds one attribute over `OpaqueMdiSubWindow`, which is why the review called it shallow. Give it the lifecycle hook the documentation has always implied. In `src/opaque/view/view.py`, add to `BaseView.__init__`, as its last statement:

```python
        self.setup_ui()
```

and add this method:

```python
    def setup_ui(self) -> None:
        """
        Build the widgets of this window. Override this.

        It is called at the end of __init__, so `self.context` is already
        there. Use `self.setWidget(widget)` to put your content in the
        window; a sub-window with no widget shows an empty frame.

        This hook is why BaseView is a class and not an alias of
        OpaqueMdiSubWindow: it is the one place a view is built, so every
        view of every feature is built the same way and at the same moment.
        """
```

Then move the widget building of the framework's own views into `setup_ui()`, and check every view under `examples/`: a view that builds widgets in its own `__init__` after `super().__init__(context)` keeps working, and a view that overrides `setup_ui()` is the shape the documentation now shows. Convert the example views; say which ones you converted.

- [ ] **Step 7: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_polish.py -q
```

Expected: `9 passed`.

- [ ] **Step 8: Run the whole suite and the examples**

```bash
uv run python -m pytest tests -q
uv run python examples/basic_example/main.py
uv run python examples/quickstart/main.py
```

Expected: zero failures, and both examples start and close with no traceback.

- [ ] **Step 9: Update the documents**

```bash
grep -rn "ApplicationView\|FlowLayout\|add_separator" --include=*.md docs README.md CLAUDE.md
```

Every hit must go. In `CLAUDE.md`, add `setup_ui()` to the view part of the MVP bullet, and in `docs/QUICK_REFERENCE.md` add it to the contract table.

- [ ] **Step 10: Commit**

```bash
git add -A src tests docs README.md CLAUDE.md examples
git commit -m "refactor(view): delete the modules nothing uses and deepen BaseView

FlowLayout is removed. It had a test and no production caller. Recover it
from this commit's parent if a wrapping toolbar is ever wanted."
```

---

## Task 2: One schema for the version information

**Files:**
- Create: `src/opaque/view/version_info_schema.py`
- Modify: `src/opaque/view/version_info.py`
- Test: `tests/view/test_version_dialogs.py` (add to it)

`version_info.py` reads the same nine string keys out of a dictionary in five places. Nothing declares what the dictionary holds, so a typo in a key gives an empty string in the interface and no error anywhere.

- [ ] **Step 1: List the keys**

```bash
grep -on "\[[\"'][a-z_]*[\"']\]\|get([\"'][a-z_]*[\"']" src/opaque/view/version_info.py | sed "s/.*[\[(]//" | tr -d "\"']" | sort | uniq -c | sort -rn
```

Expected: nine or so key names with a count each. Write the list down; it is the field list of the dataclass. If the real list differs from nine, use the real one and say so.

- [ ] **Step 2: Write the failing test**

Add to `tests/view/test_version_dialogs.py`:

```python
def test_the_version_schema_holds_every_key_the_dialog_shows():
    import dataclasses

    from opaque.view.version_info_schema import VersionInfo

    names = {entry.name for entry in dataclasses.fields(VersionInfo)}
    for expected in ("version", "build_date", "commit"):
        assert expected in names


def test_the_schema_can_be_built_from_a_dictionary():
    from opaque.view.version_info_schema import VersionInfo

    info = VersionInfo.from_dict({"version": "1.2.3"})

    assert info.version == "1.2.3"


def test_a_missing_key_gives_the_documented_placeholder():
    from opaque.view.version_info_schema import VersionInfo

    info = VersionInfo.from_dict({})

    assert info.version == VersionInfo.UNKNOWN


def test_an_unknown_key_is_ignored_and_not_written():
    from opaque.view.version_info_schema import VersionInfo

    info = VersionInfo.from_dict({"versoin": "1.2.3"})

    assert info.version == VersionInfo.UNKNOWN
    assert not hasattr(info, "versoin")


def test_the_dialog_reads_the_schema_and_not_a_dictionary():
    import inspect

    from opaque.view import version_info

    source = inspect.getsource(version_info)
    assert "VersionInfo" in source
```

Correct the three key names in the first test to the real ones from Step 1.

- [ ] **Step 3: Run the test to verify it fails**

```bash
uv run python -m pytest tests/view/test_version_dialogs.py -q -k "schema or placeholder or unknown_key"
```

Expected: a `ModuleNotFoundError` for `opaque.view.version_info_schema`.

- [ ] **Step 4: Write the schema**

Create `src/opaque/view/version_info_schema.py`:

```python
# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

What the version dialog shows.

The dialog used to read nine string keys out of a plain dictionary in five
places, with nothing declaring what the dictionary held, so a typo in a key
gave an empty line in the interface and no error anywhere.
"""

from dataclasses import dataclass, fields
from typing import Any, ClassVar, Dict


@dataclass(frozen=True)
class VersionInfo:
    """
    One version record.

    Every field is a string, because every field is shown as text. A field
    that the source does not carry reads UNKNOWN, so the dialog always has
    something to show and the user can tell the difference between "not
    recorded" and "empty".
    """

    # What a field reads when the source does not carry it. ClassVar, so it
    # is a constant of the class and not a tenth field.
    UNKNOWN: ClassVar[str] = "unknown"

    version: str = UNKNOWN
    build_date: str = UNKNOWN
    commit: str = UNKNOWN

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VersionInfo":
        """
        Build a record from a dictionary, ignoring what it does not declare.

        Args:
            data: The dictionary to read. A key that is not a field is
                ignored, which is what stops a typo from becoming a silent
                attribute.

        Returns:
            The record. Every missing field reads UNKNOWN.
        """
        known = {entry.name for entry in fields(cls)}
        return cls(**{
            name: str(value)
            for name, value in data.items()
            if name in known and value is not None
        })
```

Replace the three fields with the real key list from Step 1, keeping `UNKNOWN` first. Every field keeps the default `UNKNOWN`.

- [ ] **Step 5: Read the schema in the dialog**

In `src/opaque/view/version_info.py`, replace each of the five places that read a key with one `VersionInfo.from_dict(...)` call near the top of the function that needs it, and read the fields from that object. The dialog stops naming a string key anywhere.

- [ ] **Step 6: Run the test to verify it passes**

```bash
uv run python -m pytest tests/view/test_version_dialogs.py -q
```

Expected: every test passes, the ones that were there and the five you added.

- [ ] **Step 7: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 8: Commit**

```bash
git add src/opaque/view/version_info_schema.py src/opaque/view/version_info.py tests/view/test_version_dialogs.py
git commit -m "refactor(version): give the version information one schema"
```

---

## Task 3: One VersionManager, registered once

**Files:**
- Modify: `src/opaque/shell.py` (`__init__`, `update_application_title`)
- Modify: `src/opaque/services/version_service.py`
- Delete: `src/opaque/build_tools/templates/pyinstaller_config.py`, `src/opaque/build_tools/templates/nuitka_config.cfg`
- Test: `tests/test_polish.py` (add to it)

`VersionManager` is a `BaseService` that nothing ever registers, so `ServiceLocator.get(VersionManager)` raises everywhere, and the title bar builds a fresh one — filesystem probes included — every time the title changes. Two template configuration files under `build_tools/templates/` hold hand-written option lists that nothing reads; Plan 09 replaced the real option list with `BuildConfig`.

- [ ] **Step 1: Prove the current behaviour**

```bash
grep -rn "VersionManager" --include=*.py src examples tests
grep -rn "pyinstaller_config\|nuitka_config" --include=*.py --include=*.md src examples tests docs
```

Expected: `VersionManager` appears in its own module and in `update_application_title`, and nowhere is it registered. The two template files appear nowhere but in their own paths. Paste both outputs into your report.

- [ ] **Step 2: Write the failing test**

Add to `tests/test_polish.py`:

```python
def test_the_version_manager_is_registered(app_window):
    from opaque.services.service import ServiceLocator
    from opaque.services.version_service import VersionManager

    assert isinstance(ServiceLocator.get(VersionManager), VersionManager)


def test_the_title_bar_reuses_one_version_manager(app_window, monkeypatch):
    from opaque.services import version_service

    built = []
    real = version_service.VersionManager.__init__

    def _counting_init(self, *args, **kwargs):
        built.append(True)
        real(self, *args, **kwargs)

    monkeypatch.setattr(
        version_service.VersionManager, "__init__", _counting_init)

    app_window.update_application_title(None)
    app_window.update_application_title(None)

    assert built == []


@pytest.mark.parametrize("removed", [
    "src/opaque/build_tools/templates/pyinstaller_config.py",
    "src/opaque/build_tools/templates/nuitka_config.cfg",
])
def test_an_unread_template_is_gone(removed):
    from pathlib import Path

    assert not Path(removed).exists()
```

Add the `app_window` fixture the same way the earlier plans did.

- [ ] **Step 3: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_polish.py -q -k "version_manager or title_bar or unread_template"
```

Expected: `test_the_version_manager_is_registered` FAILS with a `LookupError`. `test_the_title_bar_reuses_one_version_manager` FAILS with `built == [True, True]`. Both template tests FAIL.

- [ ] **Step 4: Register it once**

In `src/opaque/shell.py`, in `__init__`, register the service beside the others, before the first call to `update_application_title`:

```python
        # Initialize version service
        self.version_service = VersionManager()
        self.version_service.initialize()
        ServiceLocator.register_service(self.version_service)
```

Add the import:

```python
from opaque.services.version_service import VersionManager
```

Then, in `update_application_title`, use the registered service instead of building one. Find the line that constructs a `VersionManager` and replace it with `self.version_service`.

If `update_application_title` runs before that registration in `__init__`, move the registration above it. The order in `__init__` matters and this is the whole point of the task; say what order you ended with.

- [ ] **Step 5: Delete the unread templates**

```bash
git rm src/opaque/build_tools/templates/pyinstaller_config.py src/opaque/build_tools/templates/nuitka_config.cfg
```

The real option list is `BuildConfig`, and `docs/BUILD_GUIDE.md` is generated from it by Plan 09 Task 6.

- [ ] **Step 6: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_polish.py -q
```

Expected: `13 passed`.

- [ ] **Step 7: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors. `tests/test_packaging.py` from Plan 01 Task 1 checks the package data list; if it names the two deleted template files, update that list in the same commit.

- [ ] **Step 8: Commit**

```bash
git add -A src tests
git commit -m "fix(version): register the version service once and reuse it"
```

---

## Task 4: One hit-target token, and the typos

**Files:**
- Modify: `src/opaque/view/theme/tokens.py`, `src/opaque/view/theme/__init__.py`
- Modify: `src/opaque/view/self_check.py`, `src/opaque/view/widgets/color_picker.py`, `src/opaque/view/widgets/notification_widget.py`, `src/opaque/view/version_info.py`
- Modify: the files that hold the five typos
- Modify: `src/opaque/shell.py` (`show_already_running_message`)
- Test: `tests/theme/test_tokens.py`, `tests/test_polish.py` (add to both)

The minimum hit-target size is defined five times, as 24 in some files and 28 in others, so the accessibility self check and the widgets it checks can disagree. Five typos are in shipped docstrings. And `show_already_running_message` builds two user-visible strings outside `tr()`, which `tests/test_localisation.py` does not catch because they are not `tr()` calls at all.

- [ ] **Step 1: Find the five definitions**

```bash
grep -rn "24\|28" --include=*.py src/opaque/view/self_check.py src/opaque/view/widgets/color_picker.py src/opaque/view/widgets/notification_widget.py src/opaque/view/version_info.py | grep -i "size\|target\|minimum\|height\|width"
```

Expected: five or six lines. Write down each value. The token takes the largest of them, because a hit target that is big enough is never wrong and a token that shrinks one would make a widget less accessible than it is today.

- [ ] **Step 2: Write the failing test**

Add to `tests/theme/test_tokens.py`:

```python
def test_the_hit_target_token_exists():
    from opaque.view.theme import MINIMUM_HIT_TARGET

    assert MINIMUM_HIT_TARGET >= 24


def test_the_hit_target_token_is_an_int():
    from opaque.view.theme import MINIMUM_HIT_TARGET

    assert isinstance(MINIMUM_HIT_TARGET, int)
```

Add to `tests/test_polish.py`:

```python
HIT_TARGET_USERS = [
    "opaque.view.self_check",
    "opaque.view.widgets.color_picker",
    "opaque.view.widgets.notification_widget",
    "opaque.view.version_info",
]


@pytest.mark.parametrize("module_name", HIT_TARGET_USERS)
def test_no_module_defines_its_own_hit_target(module_name):
    import importlib
    import inspect

    module = importlib.import_module(module_name)
    source = inspect.getsource(module)

    assert "MINIMUM_HIT_TARGET" in source


TYPOS = ["Prensenter", "worskpace", "heigh ", "single instead service",
         "peparator"]


@pytest.mark.parametrize("typo", TYPOS)
def test_a_shipped_typo_is_gone(typo):
    import pathlib

    hits = [
        str(path) for path in pathlib.Path("src").rglob("*.py")
        if typo in path.read_text(encoding="utf-8")
    ]
    assert hits == []


def test_every_user_visible_string_in_the_running_message_is_translated():
    import inspect

    from opaque import shell

    source = inspect.getsource(shell.BaseApplication.show_already_running_message)

    # Every string the user reads must be inside self.tr(). An f-string
    # cannot be, because lupdate cannot read it.
    assert 'f"' not in source
    assert "setText(self.tr(" in source
    assert "setInformativeText(self.tr(" in source
```

- [ ] **Step 3: Run the test to verify it fails**

```bash
uv run python -m pytest tests/theme/test_tokens.py tests/test_polish.py -q -k "hit_target or typo or running_message"
```

Expected: the two token tests FAIL with an `ImportError`, the four module tests FAIL, four or five typo tests FAIL, and the running message test FAILS.

- [ ] **Step 4: Add the token**

In `src/opaque/view/theme/tokens.py`, add this near the top, beside `_DARK_THEME_LUMINANCE_LIMIT`:

```python
# The smallest square, in device independent pixels, that a control the user
# has to hit may be. It comes from the WCAG target size guidance and the
# platform guidelines, which agree on this order of size. It was defined five
# times across the widgets and the accessibility self check, as 24 in some
# files and 28 in others, so a widget could pass its own rule and fail the
# check that read the other number.
MINIMUM_HIT_TARGET: int = 28
```

Use the largest value Step 1 found, if that is not 28, and say what you used.

Export it from `src/opaque/view/theme/__init__.py`: the import line, and the `__all__` entry before `"on_interactive"` so the list stays alphabetical among the upper case names.

- [ ] **Step 5: Read the token everywhere**

In each of the four modules, delete the local constant or the literal and import the token:

```python
from opaque.view.theme import MINIMUM_HIT_TARGET
```

`self_check.py` compares a widget size against the minimum; it must compare against this token, so the check and the widgets can no longer disagree.

- [ ] **Step 6: Fix the typos**

| Typo | Where | Correction |
|---|---|---|
| `Prensenter` | `presenters/presenter.py`, the `__hash__` docstring | `Presenter` |
| `worskpace` | `presenters/presenter.py`, `save_workspace` | `workspace` |
| `heigh` | find it with the grep in Step 2 | `height` |
| `Initialize single instead service` | `shell.py`, a comment in `__init__` | `Initialize the single instance service` |
| `peparator` | `view/widgets/toolbar.py` | gone with the wrapper in Task 1 |

Find each one exactly:

```bash
grep -rn "Prensenter\|worskpace\|heigh\|single instead service\|peparator" --include=*.py src
```

- [ ] **Step 7: Translate the two strings**

In `src/opaque/shell.py`, replace the two lines in `show_already_running_message`. Before:

```python
        msg.setText(
            f"Another instance of {self._configuration.get_application_name()} is already running.")
        msg.setInformativeText(
            "Please use the existing instance or close it before starting a new one.")
```

After:

```python
        # The name goes in through a placeholder, because lupdate cannot read
        # an f-string and a translator needs to move the name in the sentence.
        msg.setText(
            self.tr("Another instance of %1 is already running.").replace(
                "%1", self._configuration.get_application_name()))
        msg.setInformativeText(
            self.tr("Use the instance that is open, or close it before you "
                    "start a new one."))
```

- [ ] **Step 8: Run the test to verify it passes**

```bash
uv run python -m pytest tests/theme/test_tokens.py tests/test_polish.py tests/test_localisation.py -q
```

Expected: zero failures.

- [ ] **Step 9: Run the whole suite and the accessibility sweep**

```bash
uv run python -m pytest tests -q
uv run python -m pytest tests/view/test_accessibility_sweep.py -q
```

Expected: zero failures. The sweep now measures every widget against one number; if a widget fails it, that widget is genuinely too small, and making it big enough is in scope for this step. Say which widgets you had to resize.

- [ ] **Step 10: Commit**

```bash
git add src tests
git commit -m "refactor(a11y): one hit target token, and fix the shipped typos"
```

---

## Task 5: The unused imports and the commented-out code

**Files:**
- Modify: about eight files, listed by the tools in Step 1
- Test: `tests/test_polish.py` (add to it)

The review counted unused imports in about eight files and commented-out code in `view.py`, `toolbar.py`, `configuration.py` and `notification_presenter.py`. Both are noise a reader has to step over, and commented-out code is worse than deleted code: nobody can tell whether it is a plan or a leftover.

- [ ] **Step 1: List them**

```bash
uv run python -m pylint --disable=all --enable=W0611,W0612,W0613 src/opaque
```

Expected: a list of unused imports (`W0611`), unused variables (`W0612`) and unused arguments (`W0613`). Write down every `W0611` and `W0612`. Leave `W0613` alone for now: an unused argument in a Qt slot or an overridden method is required by the signature.

```bash
grep -rn "^\s*#\s*\(self\.\|from \|import \|return \|def \|if \|for \|widget\|layout\)" --include=*.py src/opaque
```

Expected: the commented-out code lines. Write them down.

- [ ] **Step 2: Write the failing test**

Add to `tests/test_polish.py`:

```python
def test_no_module_has_an_unused_import():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "pylint", "--disable=all",
         "--enable=W0611", "--score=n", "src/opaque"],
        capture_output=True, text=True, check=False)

    assert result.stdout.strip() == "", result.stdout


def test_no_module_has_an_unused_variable():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "pylint", "--disable=all",
         "--enable=W0612", "--score=n", "src/opaque"],
        capture_output=True, text=True, check=False)

    assert result.stdout.strip() == "", result.stdout


COMMENTED_OUT_CODE = [
    "src/opaque/view/view.py",
    "src/opaque/view/widgets/toolbar.py",
    "src/opaque/models/configuration.py",
    "src/opaque/presenters/notification_presenter.py",
]


@pytest.mark.parametrize("path", COMMENTED_OUT_CODE)
def test_a_file_holds_no_commented_out_code(path):
    import pathlib
    import re

    # A comment that starts with a statement keyword or an attribute write is
    # code, not prose.
    pattern = re.compile(
        r"^\s*#\s*(self\.|from |import |return |def |class |if |for |while )")

    offenders = [
        line for line in pathlib.Path(path).read_text(
            encoding="utf-8").splitlines()
        if pattern.match(line)
    ]

    assert offenders == []
```

These two pylint tests run the linter in a subprocess, which is slow but honest: the alternative is a hand-written list that goes stale. If the whole suite becomes noticeably slower, mark both with `@pytest.mark.slow` and say that you did.

- [ ] **Step 3: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_polish.py -q -k "unused or commented_out"
```

Expected: every one FAILS, each printing the list from Step 1.

- [ ] **Step 4: Delete the unused imports**

Remove every `W0611` the tool named. Do not remove an import that only a type annotation uses; those are used, and pylint knows it. If pylint names an import inside a `TYPE_CHECKING` block, check whether the annotation that needed it is still there after Plan 08; if it is not, the import goes with it.

- [ ] **Step 5: Delete the commented-out code**

Delete every line the pattern in Step 2 matches. Two of them carry information, so replace those with a real sentence instead of deleting them:

`src/opaque/view/view.py` has `#self._content_widget = None`. Plan 10 Task 1 already deleted it with the `setup_ui()` work. Confirm it is gone.

`src/opaque/presenters/notification_presenter.py` had the commented-out `register_model` line. Plan 05 Task 6 replaced it with the real call. Confirm it is gone.

For anything left, if the comment records a decision, write the decision as prose. If it records an unfinished plan, put it in `docs/known-issues/` with a sentence about what is missing, and delete the code.

- [ ] **Step 6: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_polish.py -q
```

Expected: zero failures.

- [ ] **Step 7: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors. Deleting an import that was doing work as a side effect breaks something here; if that happens, put that import back with a comment saying what it is for.

- [ ] **Step 8: Commit**

```bash
git add src tests
git commit -m "refactor: remove the unused imports and the commented-out code"
```

---

## Task 6: One close button, one confirm, and no print

**Files:**
- Create: `src/opaque/view/widgets/close_button.py`
- Modify: the three widgets that each build their own close button
- Modify: `src/opaque/view/widgets/notification_widget.py`
- Modify: `src/opaque/services/logger_service.py:135, 155, 227`, `src/opaque/services/console_service.py:188, 193`
- Modify: `src/opaque/presenters/notification_presenter.py`
- Test: `tests/test_polish.py` (add to it)

Three widgets each hand-roll a "×" close button, `ToastWidget` and `NotificationListItem` build the same row twice, two identical `_confirm_*` helpers exist, five `print()` calls report framework failures, and four connected signal handlers have `pass` for a body.

The five prints matter more than they look. `console_service.py` captures `stdout`, so a `print()` from inside the console machinery can be swallowed by the very queue that is failing. The framework's error reporting can vanish into itself.

- [ ] **Step 1: List them**

```bash
grep -rn "×\|✕\|✖\|u00d7" --include=*.py src/opaque
grep -rn "def _confirm" --include=*.py src/opaque
grep -rn "print(" --include=*.py src/opaque
grep -rn "def _on_.*:$" -A 3 --include=*.py src/opaque/presenters/notification_presenter.py | grep -B 3 "pass"
```

Expected: three close buttons, two `_confirm_` helpers, five prints, four `pass` handlers. Paste every output into your report. If a count differs, use the real one.

- [ ] **Step 2: Write the failing test**

Add to `tests/test_polish.py`:

```python
def test_no_framework_module_calls_print():
    import pathlib

    offenders = []
    for path in pathlib.Path("src/opaque").rglob("*.py"):
        for number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("print(") or " print(" in stripped:
                offenders.append(f"{path}:{number}")

    assert offenders == []


def test_the_close_button_has_one_definition():
    import pathlib

    offenders = [
        str(path) for path in pathlib.Path("src/opaque").rglob("*.py")
        if "×" in path.read_text(encoding="utf-8")
        and path.name != "close_button.py"
    ]

    assert offenders == []


def test_the_close_button_is_big_enough_to_hit(qtbot):
    from opaque.view.theme import MINIMUM_HIT_TARGET
    from opaque.view.widgets.close_button import CloseButton

    button = CloseButton()
    qtbot.addWidget(button)

    assert button.minimumWidth() >= MINIMUM_HIT_TARGET
    assert button.minimumHeight() >= MINIMUM_HIT_TARGET


def test_the_close_button_reaches_a_screen_reader(qtbot):
    from opaque.view.widgets.close_button import CloseButton

    button = CloseButton()
    qtbot.addWidget(button)

    assert button.accessibleName()


def test_the_confirm_helper_has_one_definition():
    import pathlib
    import re

    pattern = re.compile(r"def _confirm[a-z_]*\(")
    offenders = []
    for path in pathlib.Path("src/opaque").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        offenders.extend(
            [str(path)] * len(pattern.findall(text)))

    assert len(offenders) <= 1, offenders


def test_no_connected_handler_has_an_empty_body():
    import inspect
    import re

    from opaque.presenters import notification_presenter

    source = inspect.getsource(notification_presenter)
    # A handler with nothing but a docstring and pass is either dead wiring
    # or an unfinished job. Both have to be resolved, not left connected.
    assert not re.search(r"def _on_[a-z_]+\([^)]*\)[^:]*:\s*\n(\s*\"\"\"[^\"]*\"\"\"\s*\n)?\s*pass\s*\n", source)
```

- [ ] **Step 3: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_polish.py -q -k "print or close_button or confirm or empty_body"
```

Expected: every one FAILS.

- [ ] **Step 4: Write the one close button**

Create `src/opaque/view/widgets/close_button.py`:

```python
# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

The one close button.

Three widgets each built their own, with three sizes, three tool tips and
three accessible names, and two of them were smaller than the minimum hit
target. This is the only module in the framework that holds the multiplication
sign used as a close glyph.
"""

from typing import Optional

from PySide6.QtWidgets import QPushButton, QWidget

from opaque.view.theme import MINIMUM_HIT_TARGET, TypeScale


class CloseButton(QPushButton):
    """
    A small square button that closes the thing it sits on.

    It carries an accessible name, because a screen reader cannot read a
    glyph, and it is never smaller than the minimum hit target.
    """

    GLYPH = "×"

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(self.GLYPH, parent)

        self.setMinimumSize(MINIMUM_HIT_TARGET, MINIMUM_HIT_TARGET)
        self.setMaximumSize(MINIMUM_HIT_TARGET, MINIMUM_HIT_TARGET)
        self.setFont(TypeScale.body())
        self.setFlat(True)
        self.setAccessibleName(self.tr("Close"))
        self.setToolTip(self.tr("Close"))
```

Then replace all three hand-rolled buttons with `CloseButton()`, keeping each one's existing `clicked` connection.

- [ ] **Step 5: Share the notification row**

`ToastWidget` and `NotificationListItem` build the same row: an icon or a level colour, a title, a message and a close button. Give them one private helper in `notification_widget.py` that builds that row and returns the widgets both need, and call it from both. Keep every visible difference the two have today; this task changes no appearance. Say what the helper is called and what it returns.

Then delete the second `_confirm_` helper and call the first from both places.

- [ ] **Step 6: Replace the five prints**

`logger_service.py:135` and `:155` are inside `_setup_file_logging` and `_setup_console_logging`. They cannot use `self._logger`, because that is what they are setting up. Use the module logger, which Plan 06 Task 9 made reach the session file once the setup succeeds:

```python
        except OSError:
            logger.exception("Failed to set up file logging")
```

Add `logger = logging.getLogger(__name__)` at the top of `logger_service.py` if it is not there.

`logger_service.py:227` is inside `_send_to_notification_service`. Use the module logger there too, and narrow the `except Exception` to what can really happen:

```python
        except (LookupError, AttributeError, TypeError):
            logger.exception(
                "Failed to send the log record to the notification service")
```

`console_service.py:188` and `:193` are inside the drain loop that captures `stdout`. A `print()` there writes into the stream the service is capturing, so the report can be swallowed by the queue that is failing. Use the module logger, and say in a comment why:

```python
            except Exception:  # pylint: disable=broad-except
                # Never print here. This method drains the captured stdout
                # queue, so a print would go back into the queue that is
                # already failing, and the report would vanish into itself.
                logger.exception("The console handler failed")
```

- [ ] **Step 7: Resolve the four empty handlers**

`_on_notifications_changed`, `_on_notification_count_changed`, `_on_log_entry_added` and `_on_logger_configuration_changed` are connected and do nothing. Each one is now either dead wiring or a real job:

- `_on_notification_count_changed`: the toolbar count already arrives through `BaseApplication._wire_shell_signals`, so this handler is dead wiring. Delete the handler and its `connect` call.
- `_on_notifications_changed`: the comment says the work moved to `_on_service_notification_added`. Dead wiring. Delete both.
- `_on_log_entry_added`: the comment says the logger service forwards to notifications itself. Dead wiring. Delete both.
- `_on_logger_configuration_changed`: this one has a job now. Plan 05 Task 9 gave the presenter `_apply_logger_settings`, so make the handler call it, and keep the connection.

- [ ] **Step 8: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_polish.py -q
```

Expected: zero failures.

- [ ] **Step 9: Run the whole suite and look at the application**

```bash
uv run python -m pytest tests -q
uv run python examples/basic_example/main.py
```

Expected: zero failures. In the application, raise a notification from the notification tester feature and check that the toast and the list row both look the way they did, and that both close buttons work. Record what you saw.

- [ ] **Step 10: Commit**

```bash
git add src tests
git commit -m "refactor(widgets): one close button, and report failures through logging"
```

---

## Task 7: The settings file is read once

**Files:**
- Modify: `src/opaque/services/settings_service.py`
- Test: `tests/models/test_settings_service.py` (add to it)

`register_model` calls `load_settings_file()` every time a feature registers, and `save_feature_settings` writes the whole file for every feature on every Apply. An application with ten features reads the file ten times at start and writes it ten times per Apply. `SettingsService.__init__` also creates a directory as a side effect of construction, so building the object touches the disk before anybody asked it to.

- [ ] **Step 1: Write the failing test**

Add to `tests/models/test_settings_service.py`:

```python
def test_the_file_is_read_once_however_many_models_register(tmp_path,
                                                            monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"a": {}, "b": {}}), encoding="utf-8")

    service = SettingsService(path)
    service.initialize()

    reads = []
    real = service.load_settings_file
    monkeypatch.setattr(
        service, "load_settings_file",
        lambda: (reads.append(True), real())[1])

    try:
        for name in ("a", "b", "c"):
            service.register_model(name, TypedSettingsModel())
        assert reads == []
    finally:
        service.cleanup()


def test_registering_a_model_still_fills_it_from_the_file(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"demo": {"count": 4}}), encoding="utf-8")

    service = SettingsService(path)
    service.initialize()
    model = TypedSettingsModel()
    try:
        service.register_model("demo", model)
        assert model.count == 4
    finally:
        service.cleanup()


def test_building_the_service_touches_no_disk(tmp_path):
    folder = tmp_path / "not_yet"
    SettingsService(folder / "settings.json")

    assert not folder.exists()


def test_initialize_creates_the_folder(tmp_path):
    folder = tmp_path / "later"
    service = SettingsService(folder / "settings.json")
    service.initialize()
    try:
        assert folder.exists()
    finally:
        service.cleanup()


def test_saving_every_feature_writes_the_file_once(tmp_path, monkeypatch):
    service = SettingsService(tmp_path / "settings.json")
    service.initialize()
    try:
        service.register_model("a", TypedSettingsModel())
        service.register_model("b", TypedSettingsModel())

        writes = []
        real = service.save_settings_file
        monkeypatch.setattr(
            service, "save_settings_file",
            lambda: (writes.append(True), real())[1])

        service.save_all_feature_settings()

        assert len(writes) == 1
    finally:
        service.cleanup()
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/models/test_settings_service.py -q -k "read_once or touches_no_disk or initialize_creates or writes_the_file_once"
```

Expected: `test_the_file_is_read_once_however_many_models_register` FAILS with three reads. `test_building_the_service_touches_no_disk` FAILS. `test_saving_every_feature_writes_the_file_once` FAILS with `AttributeError: ... 'save_all_feature_settings'`.

- [ ] **Step 3: Write the implementation**

In `src/opaque/services/settings_service.py`, move the directory creation out of `__init__` and into `initialize`. Before, in `__init__`:

```python
        self.settings_file = settings_file
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
```

After:

```python
        self.settings_file = settings_file
```

and in `initialize`:

```python
    def initialize(self) -> None:
        # The folder is made here and not in __init__: building an object
        # must not touch the disk, and a test that only reads the path used
        # to leave a folder behind.
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        self.load_settings_file()
        return super().initialize()
```

Then drop the read from `register_model`. Before:

```python
        # Fill the model from what was already loaded. initialize() reads the
        # file once; re-reading it here made every registration touch the disk.
        self.load_settings_file()
        for key, value in self._settings.get(feature_id, {}).items():
```

After:

```python
        # initialize() has already read the file. Reading it again here made
        # start up touch the disk once per feature.
        for key, value in self._settings.get(feature_id, {}).items():
```

Then add the one call that saves everything, directly after `save_feature_settings`:

```python
    def save_all_feature_settings(self) -> bool:
        """
        Collect every registered model and write the file once.

        The settings dialog used to call save_feature_settings() per feature,
        and each call wrote the whole JSON file, so an application with ten
        features wrote the file ten times per Apply.

        Returns:
            True when the file was written.
        """
        for feature_id, model in self._feature_models.items():
            settings_data = self._collect_annotated_settings(model)
            self._settings.setdefault(feature_id, {}).update(settings_data)

        return self.save_settings_file()
```

- [ ] **Step 4: Use it in the dialog**

In `src/opaque/view/dialogs/settings.py`, `_apply_settings` loops over the features and calls `save_feature_settings` for each. Replace the write with one call, and keep the `apply_settings()` call per presenter. Before:

```python
        for feature_id, presenter in self.features.items():
            self.settings_service.save_feature_settings(
                feature_id, presenter.model)
            presenter.apply_settings()
```

After:

```python
        # One write for every feature. This loop used to write the whole file
        # once per feature.
        self.settings_service.save_all_feature_settings()

        for presenter in self.features.values():
            presenter.apply_settings()
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
uv run python -m pytest tests/models/test_settings_service.py tests/view/test_settings_dialog.py -q
```

Expected: zero failures. `tests/view/test_settings_dialog.py` has a test that Apply reaches `apply_settings` on the presenter; it must still pass.

- [ ] **Step 6: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors. A test that built a `SettingsService` and expected the folder to exist without calling `initialize()` fails here; call `initialize()` in that test and say which one you changed.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/services/settings_service.py src/opaque/view/dialogs/settings.py tests/models/test_settings_service.py
git commit -m "perf(settings): read the file once and write it once"
```

---

## Task 8: A clean type check and a clean lint, enforced

**Files:**
- Modify: whatever mypy and pylint report
- Modify: `.github/workflows/ci.yml`
- Modify: `pyproject.toml` (the pylint section, only if a rule has to be switched off)
- Test: CI

`mypy` never got past `src/opaque/build_tools/pyinstaller_builder.py:268`, so nothing after that file was ever checked. Plan 01 Task 7 put mypy and pylint in CI with `continue-on-error: true` and a comment pointing here. This task makes both pass and removes the leniency.

- [ ] **Step 1: See where you are**

```bash
uv run python -m mypy src/opaque 2>&1 | tail -20
uv run python -m pylint src/opaque 2>&1 | tail -30
```

Write down both counts. This is the baseline, and your report must give the before and after numbers.

- [ ] **Step 2: Fix the type errors**

Work through the mypy list. Three kinds turn up, and each has one right answer:

- A missing annotation on a function the framework exports: add the annotation. Do not add `Any` where the real type is known.
- An `Optional` that is used without a check: this is the class of defect review 4.1 was about. Where the value comes from `ServiceLocator.get`, it is no longer optional after Plan 07. Where it is genuinely optional, add the check and decide what happens when it is `None`; never add `# type: ignore` to silence it.
- A third-party module with no stubs: `[tool.mypy]` already carries `ignore_missing_imports = true` from Plan 01 Task 1. If a specific module still complains, add a `[[tool.mypy.overrides]]` block naming that module, with a comment saying why.

Every `# type: ignore` you add needs a comment saying what cannot be expressed. If you cannot write that comment, the fix is wrong.

- [ ] **Step 3: Fix the lint messages**

Work through the pylint list. Do not switch a rule off to make it quiet. Two exceptions, both to be recorded in `pyproject.toml` with a comment:

- `too-few-public-methods` on a dataclass. A dataclass is data.
- `broad-except` where the framework deliberately catches everything to keep the interface alive, which is the notification and the logging paths. Each of those already carries an inline `# pylint: disable=broad-except`; leave those inline and do not make it global.

- [ ] **Step 4: Verify both are clean**

```bash
uv run python -m mypy src/opaque
uv run python -m pylint src/opaque
```

Expected: `Success: no issues found` from mypy, and `10.00/10` from pylint. If you cannot reach either, stop and report exactly what is left and why, with the file and the line.

- [ ] **Step 5: Make CI enforce it**

In `.github/workflows/ci.yml`, delete `continue-on-error: true` from the mypy step and from the pylint step, and delete the comment that pointed at this plan.

- [ ] **Step 6: Run everything one last time**

```bash
uv run python -m pytest tests -q
uv run python -m mypy src/opaque
uv run python -m pylint src/opaque
uv run python examples/basic_example/main.py
uv run python examples/quickstart/main.py
```

Expected: zero test failures, no mypy issue, a perfect pylint score, and both examples start and close cleanly.

- [ ] **Step 7: Commit**

```bash
git add .github/workflows/ci.yml pyproject.toml src tests
git commit -m "chore: make the type check and the lint pass, and enforce both in CI"
```

---

## Verification of the whole plan

- [ ] **Check 1: nothing unused is left**

```bash
uv run python -m pytest tests/test_polish.py -q
```

Expected: zero failures.

- [ ] **Check 2: one definition per idea**

```bash
grep -rn "×" --include=*.py src/opaque | grep -v close_button.py
grep -rn "print(" --include=*.py src/opaque
grep -rn "MINIMUM_HIT_TARGET" --include=*.py src/opaque | wc -l
```

Expected: no output from the first two. The third prints five or more: the definition plus every reader.

- [ ] **Check 3: the tools are clean and enforced**

```bash
uv run python -m mypy src/opaque
uv run python -m pylint src/opaque
grep -n "continue-on-error" .github/workflows/ci.yml
```

Expected: no mypy issue, `10.00/10`, and no output from the grep.

- [ ] **Check 4: the review is closed**

Read `docs/ENGINEERING_REVIEW.md` from the top with the index open beside it. For every numbered item, name the commit that closed it. Write the result as a new section at the end of the review:

```markdown
---

## 9. Closure

Every item above was closed by the plans in `docs/superpowers/plans/`. The
index at `2026-09-08-techdebt-00-index.md` maps each item to its plan and
task. Items accepted rather than fixed, with the reason:

| Item | Decision |
|---|---|
| 4.7 signal hygiene | Accepted per D6: features never unload, so the shell connects once and never disconnects. `tests/test_signal_policy.py` keeps the assumption honest. |
| `NotificationPresenter` is not a feature | Accepted: it is a system presenter and takes the main window by design. |
| `opaque/view/application.py` | Kept for one release as a deprecated re-export of `opaque.shell`. |
```

Add a row for anything else you accepted instead of fixing. Then commit:

```bash
git add docs/ENGINEERING_REVIEW.md
git commit -m "docs: record how every review item was closed"
```

---

## What this plan does not do

| Left open | Why |
|---|---|
| Deleting `opaque/view/application.py`. | It is a deprecated re-export, and one release has to pass first. |
| A build in CI. | A build takes minutes and needs a backend installed. |
| Publishing anything, anywhere. | Out of scope by decision, and a destination question, not a code question. |
