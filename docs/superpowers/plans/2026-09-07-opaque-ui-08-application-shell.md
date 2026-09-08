# Plan 08 — Application Shell and Dialogs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the main window: a feature must not disappear from the registry when its window closes, the title must not show empty brackets, the size limits must be applied to the right property, errors must reach a log instead of `print`, `load_workspace` must use the path it was given, a dropped workspace file must be recognised, and the About dialog must not clip its own text.

**Architecture:** `BaseApplication` is one large class that also holds pure decisions: how to build a title, how to apply size limits, and whether a dropped file is a workspace. This plan pulls those three decisions out as static methods, so they can be tested without building a whole application. Everything else is tested against **one** `BaseApplication` built once for the whole test session, because `ServiceLocator` is a process wide singleton and refuses a second registration of the same service.

**Tech Stack:** PySide6, pytest, pytest-qt.

Read **Rules for the executing agent** in `2026-09-07-opaque-ui-00-index.md` before you start.

**Depends on:** Plan 01, Plan 02, Plan 03 and Plan 05. Task 7 connects work that Plan 03 and Plan 05 create.

**About the totals:** the `pytest -q` totals assume Plan 01 to Plan 07 are already merged and that this plan runs after them. If you ran the plans in parallel, compare only the per-file counts and require zero failures in the whole suite.

---

## Findings closed by this plan

| ID | Finding | Task |
|---|---|---|
| C14 | Feature de-registers itself on window close | 1 |
| W21 | Window title shows an empty bracket pair | 2 |
| W20 | `setMinimumSize` called with the maximum size | 2 |
| C8 | No keyboard layer (menu part) | 2 |
| W17 | Errors go to `print()` | 3 |
| W18 | `load_workspace` discards its own argument | 4 |
| W19 | Drag and drop never accepts a real workspace file | 5 |
| C10 | Fixed pixel dialogs clip text | 6 |
| C5 | Dialogs hardcode colours (dialogs part) | 6 |
| C3 | `update_theme()` has no caller (second half) | 7 |
| W6 | Notification count discarded (wiring half) | 7 |

---

## Two corrections to the audit

**W19.** The audit said drag and drop is completely dead because `setAcceptDrops(True)` is never called. That reason is wrong: `QMainWindow` turns `acceptDrops` on by itself, so `dragEnterEvent` and `dropEvent` do run. The real defect is that both handlers only accept `.lab`, while `DefaultApplicationConfiguration.workspace_file_extension` is `.wks`. A user who drags a real workspace file gets nothing. Task 5 fixes the extension, not the flag.

**C14.** The audit reported this as a registry leak. It is worse than that. `closeable=False` means closing a feature window only hides it, but `register_feature` connects `window_closed` to a handler that deletes the feature from `_registered_features`. Closing the window therefore removes the feature's Settings page for the rest of the session, and `closeEvent` never calls that presenter's `cleanup()`. This is proven in Task 1.

---

## File Structure

| Path | Responsibility |
|---|---|
| Modify `src/opaque/view/application.py` | Registry, title, size limits, logging, workspace loading, drag and drop, and the Task 7 wiring. |
| Modify `src/opaque/view/dialogs/version_info.py` | Remove the fixed pixel sizes and the hardcoded colours. |
| Create `tests/test_application_shell.py` | One shared application, plus the pure helper tests. |
| Create `tests/view/test_version_dialogs.py` | Dialog sizing and colour tests. |

---

### Task 1: A feature must survive its own window closing (C14)

`register_feature` connects `window_closed` to a handler that deletes the feature from `_registered_features`. A feature window that is not closeable is only hidden when it closes, so the feature is still there, but the application has forgotten it. Its Settings page disappears and its `cleanup()` never runs.

**Files:**
- Modify: `src/opaque/view/application.py`
- Test: `tests/test_application_shell.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_application_shell.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""
Tests for the main application window.

ServiceLocator is a process wide singleton and refuses a second registration
of the same service, so exactly one BaseApplication is built for the whole
test session and every test shares it. Each test must therefore use its own
feature name and must not remove anything another test relies on.

The import order below matters. Importing opaque.view.view before
opaque.view.application raises a circular import error.
"""

import pytest
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QLabel

from opaque.models.configuration import DefaultApplicationConfiguration
from opaque.view.application import BaseApplication
from opaque.models.model import BaseModel
from opaque.view.view import BaseView
from opaque.presenters.presenter import BasePresenter


class _TestConfiguration(DefaultApplicationConfiguration):
    """The smallest configuration BaseApplication will accept."""

    def get_application_name(self) -> str:
        return "OpaqueShellTest"

    def get_application_title(self) -> str:
        return "Opaque Shell Test"

    def get_application_description(self) -> str:
        return "A configuration used only by the tests."

    def get_application_icon(self) -> QIcon:
        return QIcon()

    def get_application_organization(self) -> str:
        return "Opaque Tests"


class _StubModel(BaseModel):
    """A feature model with no settings and no workspace data."""

    def __init__(self, app, name: str):
        super().__init__(app)
        self._name = name

    def feature_name(self) -> str:
        return self._name

    def feature_description(self) -> str:
        return "A feature used only by the tests."

    def feature_icon(self) -> QIcon:
        return QIcon()


class _StubView(BaseView):
    """A feature window holding one label."""

    def __init__(self, app):
        super().__init__(app)
        self.setWidget(QLabel("stub"))


class _StubPresenter(BasePresenter):
    """A presenter that records the calls the framework makes on it."""

    def __init__(self, model, view, app, feature_id):
        self.cleanup_calls = 0
        super().__init__(model, view, app, feature_id)

    def bind_events(self) -> None:
        pass

    def initialize(self) -> None:
        pass

    def cleanup(self) -> None:
        self.cleanup_calls += 1

    def update(self, *args, **kwargs) -> None:
        pass

    def on_view_show(self) -> None:
        pass

    def on_view_close(self) -> None:
        pass


@pytest.fixture(scope="session")
def app_window(qapp, tmp_path_factory):
    """Build one BaseApplication for the whole test session."""
    settings_file = tmp_path_factory.mktemp("shell") / "settings.json"
    configuration = _TestConfiguration()
    configuration.settings_file_path = str(settings_file)
    window = BaseApplication(configuration)
    yield window
    window.close()


@pytest.fixture
def make_feature(app_window):
    """Return a factory that registers one feature under a unique name."""
    def _make(name: str) -> _StubPresenter:
        model = _StubModel(app_window, name)
        view = _StubView(app_window)
        return _StubPresenter(model, view, app_window, name)
    return _make


def test_a_registered_feature_is_in_the_registry(app_window, make_feature):
    presenter = make_feature("Registry Feature")
    app_window.register_feature(presenter)
    assert "Registry Feature" in app_window._registered_features


def test_a_closed_feature_window_stays_registered(app_window, make_feature):
    presenter = make_feature("Closing Feature")
    app_window.register_feature(presenter)

    presenter.view.window_closed.emit()

    assert "Closing Feature" in app_window._registered_features
    assert app_window._registered_features["Closing Feature"] is presenter


def test_registering_the_same_feature_twice_is_refused(
        app_window, make_feature):
    app_window.register_feature(make_feature("Twice Feature"))
    with pytest.raises(ValueError):
        app_window.register_feature(make_feature("Twice Feature"))
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_application_shell.py -q
```

Expected: FAIL. `test_a_closed_feature_window_stays_registered` fails with `assert 'Closing Feature' in {...}`.

The other two tests must pass. If they do not, stop and report it.

- [ ] **Step 3: Remove the de-registration handler**

In `src/opaque/view/application.py`, replace this block:

```python
        # Add toolbar button for the feature
        self.toolbar.add_feature(presenter)

        def on_view_closed():
            if feature_name in self._registered_features:
                del self._registered_features[feature_name]
        presenter.view.window_closed.connect(on_view_closed)

        self.mdi_area.addSubWindow(presenter.view)
        presenter.view.show()
```

with exactly this:

```python
        # Add toolbar button for the feature
        self.toolbar.add_feature(presenter)

        # A feature window that closes is only hidden, so the feature is still
        # there. Removing it from the registry here would take away its
        # Settings page and would stop closeEvent from calling its cleanup().
        # Features are released in closeEvent, never on a window close.

        self.mdi_area.addSubWindow(presenter.view)
        presenter.view.show()
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_application_shell.py -q
```

Expected: PASS. `3 passed`.

- [ ] **Step 5: Prove the handler is gone**

Run:

```bash
grep -n "del self._registered_features" src/opaque/view/application.py
```

Expected: no output at all.

- [ ] **Step 6: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `183 passed`.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/view/application.py tests/test_application_shell.py
git commit -m "fix(shell): keep a feature registered when its window closes"
```

---

### Task 2: The title, the size limits and the menu keys (W21, W20, C8)

Three defects in the constructor and the menu:

1. `update_application_title("")` produces `My App 1.0 []`. An empty bracket pair is noise.
2. The maximum size branch calls `setMinimumSize`, not `setMaximumSize`. Any configuration that gives a maximum size would set it as a minimum instead. The defect is hidden today only because the default configuration returns `None` for both.
3. No File menu action has a keyboard shortcut.

**Files:**
- Modify: `src/opaque/view/application.py`
- Test: `tests/test_application_shell.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/test_application_shell.py`:

```python
def test_the_title_has_no_empty_brackets_without_a_workspace():
    title = BaseApplication.build_window_title("My App", "1.0", None)
    assert title == "My App 1.0"
    assert "[" not in title


def test_an_empty_workspace_name_is_the_same_as_none():
    assert BaseApplication.build_window_title("My App", "1.0", "") == \
        BaseApplication.build_window_title("My App", "1.0", None)


def test_the_title_shows_the_workspace_when_there_is_one():
    title = BaseApplication.build_window_title("My App", "1.0", "bench.wks")
    assert title == "My App 1.0 [bench.wks]"


def test_the_minimum_size_is_applied_as_a_minimum(qtbot):
    widget = QWidget()
    qtbot.addWidget(widget)
    BaseApplication.apply_size_limits(widget, (640, 480), None)
    assert widget.minimumWidth() == 640
    assert widget.minimumHeight() == 480


def test_the_maximum_size_is_applied_as_a_maximum(qtbot):
    widget = QWidget()
    qtbot.addWidget(widget)
    BaseApplication.apply_size_limits(widget, None, (1920, 1080))
    assert widget.maximumWidth() == 1920
    assert widget.maximumHeight() == 1080
    # The bug this replaces set the maximum as a minimum.
    assert widget.minimumWidth() != 1920


def test_the_file_menu_actions_have_shortcuts(app_window):
    shortcuts = [
        action.shortcut().toString()
        for action in app_window.file_menu.actions()
        if not action.isSeparator()
    ]
    assert "" not in shortcuts
    assert len(shortcuts) == 4
```

Then replace this import line at the top of `tests/test_application_shell.py`:

```python
from PySide6.QtWidgets import QLabel
```

with exactly this:

```python
from PySide6.QtWidgets import QLabel, QWidget
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_application_shell.py -q
```

Expected: FAIL. The output contains `AttributeError: type object 'BaseApplication' has no attribute 'build_window_title'`.

- [ ] **Step 3: Add the two static helpers**

In `src/opaque/view/application.py`, replace this block:

```python
    def update_application_title(self, workspace: Optional[str]):
        self.setWindowTitle(
            f"{self._configuration.get_application_title()} {self._configuration.get_application_version()} [{workspace}]")
```

with exactly this:

```python
    @staticmethod
    def build_window_title(
        title: str,
        version: str,
        workspace: Optional[str],
    ) -> str:
        """
        Build the text of the window title bar.

        Args:
            title: The application title.
            version: The application version.
            workspace: The open workspace name, or None when none is open.

        Returns:
            The title. An empty or missing workspace leaves no bracket pair
            behind, because an empty pair of brackets tells the user nothing.
        """
        base = f"{title} {version}".strip()
        if workspace:
            return f"{base} [{workspace}]"
        return base

    @staticmethod
    def apply_size_limits(window: QWidget, min_size, max_size) -> None:
        """
        Apply the configured size limits to a window.

        Args:
            window: The window to limit.
            min_size: A width and height pair, or None.
            max_size: A width and height pair, or None.
        """
        if min_size and len(min_size) == 2:
            window.setMinimumSize(min_size[0], min_size[1])
        if max_size and len(max_size) == 2:
            window.setMaximumSize(max_size[0], max_size[1])

    def update_application_title(self, workspace: Optional[str]) -> None:
        """Put the application name, the version and the workspace in the title."""
        self.setWindowTitle(self.build_window_title(
            self._configuration.get_application_title(),
            self._configuration.get_application_version(),
            workspace,
        ))
```

- [ ] **Step 4: Use the helper in the constructor**

In the same file, replace this block:

```python
        # Application minimum size
        min_size = configuration.get_application_min_size()
        if min_size and len(min_size) == 2:
            self.setMinimumSize(min_size[0], min_size[1])

        # Application maximum size
        max_size = configuration.get_application_max_size()
        if max_size and len(max_size) == 2:
            self.setMinimumSize(max_size[0], max_size[1])
```

with exactly this:

```python
        self.apply_size_limits(
            self,
            configuration.get_application_min_size(),
            configuration.get_application_max_size(),
        )
```

Then replace this line in the same constructor:

```python
        self.update_application_title("")
```

with exactly this:

```python
        self.update_application_title(None)
```

- [ ] **Step 5: Give the File menu its keys**

In the same file, replace the whole `_setup_file_menu` method with exactly this:

```python
    def _setup_file_menu(self) -> None:
        """Build the File menu. Every action carries a keyboard shortcut."""
        menu_bar = self.menuBar()
        self.file_menu = menu_bar.addMenu(self.tr("&File"))

        save_workspace_action = QAction(self.tr("Save Workspace"), self)
        save_workspace_action.setShortcut(QKeySequence.StandardKey.Save)
        save_workspace_action.triggered.connect(self.save_workspace)
        self.file_menu.addAction(save_workspace_action)

        load_workspace_action = QAction(self.tr("Load Workspace"), self)
        load_workspace_action.setShortcut(QKeySequence.StandardKey.Open)
        load_workspace_action.triggered.connect(self.load_workspace)
        self.file_menu.addAction(load_workspace_action)

        self.file_menu.addSeparator()

        settings_action = QAction(self.tr("Settings..."), self)
        settings_action.setShortcut(QKeySequence.StandardKey.Preferences)
        settings_action.triggered.connect(self.show_settings_dialog)
        self.file_menu.addAction(settings_action)

        self.file_menu.addSeparator()

        exit_action = QAction(self.tr("Exit"), self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        self.file_menu.addAction(exit_action)
```

`QKeySequence.StandardKey` gives the key the platform expects. Do not write `Ctrl+S` by hand.

- [ ] **Step 6: Add `QKeySequence` to the imports**

In the same file, replace this line:

```python
from PySide6.QtGui import QAction, QIcon, QCloseEvent, QDragEnterEvent, QDropEvent
```

with exactly this:

```python
from PySide6.QtGui import (
    QAction, QIcon, QCloseEvent, QDragEnterEvent, QDropEvent, QKeySequence,
)
```

- [ ] **Step 7: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_application_shell.py -q
```

Expected: PASS. `9 passed`.

If `test_the_file_menu_actions_have_shortcuts` fails because `Preferences` or `Quit` resolves to an empty string on Windows, replace only those two lines with `QKeySequence("Ctrl+,")` and `QKeySequence("Ctrl+Q")`, then run the test again. Do not change the Save or Open lines.

- [ ] **Step 8: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `189 passed`.

- [ ] **Step 9: Commit**

```bash
git add src/opaque/view/application.py tests/test_application_shell.py
git commit -m "fix(shell): correct the title, the size limits and add File menu shortcuts"
```

---

### Task 3: Errors must reach a log, not `print` (W17)

Every failure in the shell and in the presenters ends in `print(e)`. That line is invisible in a packaged build, it carries no timestamp, no level and no traceback, and the framework already runs a `LoggerService`.

**Files:**
- Modify: `src/opaque/view/application.py`
- Modify: `src/opaque/presenters/presenter.py`
- Modify: `src/opaque/presenters/notification_presenter.py`
- Modify: `src/opaque/presenters/console_presenter.py`
- Modify: `src/opaque/view/widgets/closeable_tab_widget.py`
- Test: `tests/test_application_shell.py`

**Run this task only after Plan 05, Plan 06 and Plan 07 are merged.** Three of the five files above belong to those plans.

`src/opaque/build_tools/`, `src/opaque/services/console_service.py` and `src/opaque/services/logger_service.py` are **out of scope**. The build tools print on purpose, they are command line programs. The console service and the logger service are the machinery that captures and writes output, and routing them into a logger risks a loop.

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/test_application_shell.py`:

```python
_UI_MODULES = [
    "src/opaque/view/application.py",
    "src/opaque/presenters/presenter.py",
    "src/opaque/presenters/notification_presenter.py",
    "src/opaque/presenters/console_presenter.py",
    "src/opaque/view/widgets/closeable_tab_widget.py",
]


def test_the_shell_modules_have_a_logger():
    import opaque.presenters.notification_presenter as notification_module
    import opaque.view.application as application_module

    assert isinstance(application_module.logger, logging.Logger)
    assert isinstance(notification_module.logger, logging.Logger)


def test_no_ui_module_reports_an_error_with_print():
    root = Path(__file__).resolve().parents[1]
    offenders = []
    for relative in _UI_MODULES:
        source = (root / relative).read_text(encoding="utf-8")
        for number, line in enumerate(source.splitlines(), 1):
            if line.strip().startswith("print("):
                offenders.append(f"{relative}:{number}")
    assert offenders == []
```

Then add these two imports at the top of `tests/test_application_shell.py`, above the `import pytest` line:

```python
import logging
from pathlib import Path
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_application_shell.py -q
```

Expected: FAIL. The output contains `AttributeError: module 'opaque.view.application' has no attribute 'logger'`.

- [ ] **Step 3: Give each of the five files a logger**

In each of the five files listed under **Files**, do exactly two things.

First, add this line at the top of the import block, above the `from PySide6...` lines:

```python
import logging
```

Second, add these two lines directly below the last import of the file, separated from it by one blank line:

```python

logger = logging.getLogger(__name__)
```

- [ ] **Step 4: Replace every `print` in those five files**

Apply this rule to every line in those five files that starts with `print(`:

- If the line sits inside an `except` block, replace the whole line with
  `logger.exception("<the message text, with the exception part removed>")`.
  `logger.exception` writes the traceback by itself, so `{e}` is not needed.
- If the line does not sit inside an `except` block, replace it with
  `logger.warning("<the same message text>")`.

Worked example. In `src/opaque/view/application.py`, this block:

```python
        except Exception as e:
            print(e)
            QMessageBox.critical(self, self.tr("Error Saving Workspace"), self.tr(
                f"An error happened while saving workspace file. Details {e}"))
```

becomes exactly this:

```python
        except Exception:
            logger.exception("Failed to save the workspace file")
            QMessageBox.critical(
                self,
                self.tr("Error Saving Workspace"),
                self.tr("The workspace file could not be saved. "
                        "See the log for details."),
            )
```

Note two things in that example. The `as e` is gone, because nothing uses `e` any more. The message the user reads is now a literal inside `self.tr(...)`, which `lupdate` can read. `self.tr(f"...")` can never be translated.

Do the same for the other `print` lines. Keep every message short and plain.

- [ ] **Step 5: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_application_shell.py -q
```

Expected: PASS. `11 passed`.

If the test lists a file and a line number, that `print` was missed. Go back to Step 4 for that line.

- [ ] **Step 6: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `191 passed`.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/view/application.py src/opaque/presenters/presenter.py src/opaque/presenters/notification_presenter.py src/opaque/presenters/console_presenter.py src/opaque/view/widgets/closeable_tab_widget.py tests/test_application_shell.py
git commit -m "fix(shell): report failures through logging instead of print"
```

---

### Task 4: `load_workspace` must use the path it was given (W18)

`load_workspace(self, file_path: Optional[str] = None)` opens a file dialog and then writes the result over its own `file_path` argument. The argument can therefore never do anything. A drop, a command line argument and a recent files list are all impossible.

**Files:**
- Modify: `src/opaque/view/application.py`
- Test: `tests/test_application_shell.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/test_application_shell.py`:

```python
def test_load_workspace_does_not_ask_when_a_path_is_given(
        app_window, monkeypatch, tmp_path):
    given = str(tmp_path / "given.wks")
    asked = []
    loaded = []
    monkeypatch.setattr(
        app_window, "_ask_for_workspace_path",
        lambda for_load: asked.append(for_load) or "")
    monkeypatch.setattr(
        app_window.workspace_service, "load_workspace",
        lambda path: loaded.append(path) or "given")

    app_window.load_workspace(given)

    assert asked == []
    assert loaded == [given]


def test_load_workspace_asks_when_no_path_is_given(app_window, monkeypatch):
    asked = []
    loaded = []
    monkeypatch.setattr(
        app_window, "_ask_for_workspace_path",
        lambda for_load: asked.append(for_load) or "chosen.wks")
    monkeypatch.setattr(
        app_window.workspace_service, "load_workspace",
        lambda path: loaded.append(path) or "chosen")

    app_window.load_workspace()

    assert asked == [True]
    assert loaded == ["chosen.wks"]


def test_load_workspace_does_nothing_when_the_user_cancels(
        app_window, monkeypatch):
    loaded = []
    monkeypatch.setattr(
        app_window, "_ask_for_workspace_path", lambda for_load: "")
    monkeypatch.setattr(
        app_window.workspace_service, "load_workspace",
        lambda path: loaded.append(path))

    app_window.load_workspace()

    assert loaded == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_application_shell.py -q
```

Expected: FAIL. The output contains `AttributeError: 'BaseApplication' object has no attribute '_ask_for_workspace_path'`.

- [ ] **Step 3: Replace both workspace methods**

In `src/opaque/view/application.py`, replace the whole `save_workspace` method and the whole `load_workspace` method, from `    def save_workspace(self) -> None:` down to the line before `    def show_settings_dialog(self) -> None:`, with exactly this:

```python
    def _ask_for_workspace_path(self, for_load: bool) -> str:
        """
        Ask the user for a workspace file path.

        Args:
            for_load: True to open an existing file, False to save a new one.

        Returns:
            The chosen path, or an empty string when the user cancelled.
        """
        description = self.tr("Application Workspace")
        extension = self._configuration.get_workspace_file_extension()
        file_filter = f"{description} (*{extension})"

        if for_load:
            path, _ = QFileDialog.getOpenFileName(
                self, self.tr("Load Workspace"), "", file_filter)
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, self.tr("Save Workspace"), "", file_filter)
        return path

    def save_workspace(self, file_path: Optional[str] = None) -> None:
        """
        Save the workspace.

        Args:
            file_path: Where to save. When empty, the user is asked.
        """
        if not file_path:
            file_path = self._ask_for_workspace_path(for_load=False)
        if not file_path:
            return

        try:
            name = self.workspace_service.save_workspace(file_path)
            self.update_application_title(name)
        except Exception:
            logger.exception("Failed to save the workspace file")
            QMessageBox.critical(
                self,
                self.tr("Error Saving Workspace"),
                self.tr("The workspace file could not be saved. "
                        "See the log for details."),
            )

    def load_workspace(self, file_path: Optional[str] = None) -> None:
        """
        Load a workspace.

        Args:
            file_path: The workspace file to load. When empty, the user is
                asked. The old code asked always and then wrote the answer
                over this argument, so a drop or a command line argument
                could never work.
        """
        if not file_path:
            file_path = self._ask_for_workspace_path(for_load=True)
        if not file_path:
            return

        try:
            name = self.workspace_service.load_workspace(file_path)
            self.update_application_title(name)
        except Exception:
            logger.exception("Failed to load the workspace file")
            QMessageBox.critical(
                self,
                self.tr("Error Loading Workspace"),
                self.tr("The workspace file could not be loaded. "
                        "See the log for details."),
            )
```

Both menu actions still work. `QAction.triggered` passes a boolean, and `not False` is True, so the dialog still opens from the menu.

The file filter is no longer built with `self.tr(f"...")`. A translator cannot read an f-string.

- [ ] **Step 4: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_application_shell.py -q
```

Expected: PASS. `14 passed`.

- [ ] **Step 5: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `194 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/view/application.py tests/test_application_shell.py
git commit -m "fix(shell): load and save the workspace path the caller gave"
```

---

### Task 5: A dropped workspace file must be recognised (W19)

`dragEnterEvent` and `dropEvent` both accept only `.lab`. The configured extension is `.wks`. Dragging a real workspace file onto the window does nothing at all.

**Files:**
- Modify: `src/opaque/view/application.py`
- Test: `tests/test_application_shell.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/test_application_shell.py`:

```python
def test_a_dropped_file_with_the_configured_extension_is_accepted():
    urls = [QUrl.fromLocalFile("C:/work/bench.wks")]
    path = BaseApplication.workspace_path_from_urls(urls, ".wks")
    assert path is not None
    assert path.endswith("bench.wks")


def test_a_dropped_file_with_another_extension_is_refused():
    urls = [QUrl.fromLocalFile("C:/work/bench.lab")]
    assert BaseApplication.workspace_path_from_urls(urls, ".wks") is None


def test_two_dropped_files_are_refused():
    urls = [
        QUrl.fromLocalFile("C:/work/one.wks"),
        QUrl.fromLocalFile("C:/work/two.wks"),
    ]
    assert BaseApplication.workspace_path_from_urls(urls, ".wks") is None


def test_the_extension_check_ignores_case():
    urls = [QUrl.fromLocalFile("C:/work/BENCH.WKS")]
    assert BaseApplication.workspace_path_from_urls(urls, ".wks") is not None
```

Then add this import at the top of `tests/test_application_shell.py`, above the `from PySide6.QtGui...` line:

```python
from PySide6.QtCore import QUrl
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_application_shell.py -q
```

Expected: FAIL. The output contains `AttributeError: type object 'BaseApplication' has no attribute 'workspace_path_from_urls'`.

- [ ] **Step 3: Replace both drag and drop handlers**

In `src/opaque/view/application.py`, replace the whole `dragEnterEvent` method and the whole `dropEvent` method, from `    def dragEnterEvent(self, event: QDragEnterEvent):` to the end of the file, with exactly this:

```python
    @staticmethod
    def workspace_path_from_urls(urls, extension: str) -> Optional[str]:
        """
        Return the single dropped workspace file path, or None.

        Args:
            urls: The QUrl list carried by the drag or the drop event.
            extension: The configured workspace extension, for example ".wks".

        Returns:
            The local file path, when exactly one file is offered and it has
            the configured extension. None in every other case.
        """
        if len(urls) != 1:
            return None

        path = urls[0].toLocalFile()
        if not path:
            return None

        if not path.lower().endswith(extension.lower()):
            return None

        return path

    def _dropped_workspace_path(self, event) -> Optional[str]:
        """Return the workspace file this event carries, or None."""
        if not event.mimeData().hasUrls():
            return None
        return self.workspace_path_from_urls(
            event.mimeData().urls(),
            self._configuration.get_workspace_file_extension(),
        )

    def dragEnterEvent(self, event: QDragEnterEvent):
        """
        Accept a drag that carries one workspace file.

        The extension comes from the configuration. The old code compared
        against ".lab", which no configuration in this framework ever uses.
        """
        if self._dropped_workspace_path(event):
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Load the workspace file this drop carries."""
        file_path = self._dropped_workspace_path(event)
        if not file_path:
            event.ignore()
            return

        event.acceptProposedAction()
        self.load_workspace(file_path)
```

`dropEvent` now calls `load_workspace`, which Task 4 made able to use a given path. It also reports its own errors, so the duplicated `try` block is gone.

- [ ] **Step 4: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_application_shell.py -q
```

Expected: PASS. `18 passed`.

- [ ] **Step 5: Prove the wrong extension is gone**

Run:

```bash
grep -n "\.lab" src/opaque/view/application.py
```

Expected: no output at all.

- [ ] **Step 6: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `198 passed`.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/view/application.py tests/test_application_shell.py
git commit -m "fix(shell): accept a dropped workspace file with the configured extension"
```

---

### Task 6: The dialogs must grow with their text (C10, C5)

`AboutDialog` calls `setFixedSize(400, 300)`. A German or Finnish translation, or an operating system font size set to Large, will not fit, and the text is simply cut off. The dialogs also write `QFont("Courier", 9)`, `color: #666666` and `rgba(0, 0, 0, 0.1)`, none of which follow the theme.

**Files:**
- Modify: `src/opaque/view/dialogs/version_info.py`
- Test: `tests/view/test_version_dialogs.py`

- [ ] **Step 1: Write the failing test**

Create `tests/view/test_version_dialogs.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the version and About dialogs."""

from pathlib import Path

from opaque.view.dialogs.version_info import AboutDialog, VersionInfoDialog
from opaque.view.theme import TypeScale, contrast_ratio, surface
from opaque.view.theme.contrast import TEXT_CONTRAST_MINIMUM

_SOURCE = Path(__file__).resolve().parents[2] / \
    "src" / "opaque" / "view" / "dialogs" / "version_info.py"


def test_the_about_dialog_is_not_a_fixed_size(qtbot, light_palette_app):
    dialog = AboutDialog()
    qtbot.addWidget(dialog)
    assert dialog.maximumWidth() > dialog.minimumWidth()
    assert dialog.maximumHeight() > dialog.minimumHeight()


def test_the_about_dialog_keeps_a_sensible_floor(qtbot, light_palette_app):
    dialog = AboutDialog()
    qtbot.addWidget(dialog)
    assert dialog.minimumWidth() >= 400


def test_the_framework_label_colour_passes_contrast(qtbot, light_palette_app):
    dialog = AboutDialog()
    qtbot.addWidget(dialog)
    ratio = contrast_ratio(dialog.framework_label_colour, surface())
    assert ratio >= TEXT_CONTRAST_MINIMUM


def test_the_system_tab_uses_the_system_fixed_font(qtbot, light_palette_app):
    dialog = VersionInfoDialog()
    qtbot.addWidget(dialog)
    assert dialog.system_text.font().family() == TypeScale.mono().family()


def test_no_dialog_hardcodes_a_grey_or_a_font_family():
    source = _SOURCE.read_text(encoding="utf-8")
    assert "#666666" not in source
    assert "rgba(0, 0, 0" not in source
    assert 'QFont("Courier"' not in source
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_version_dialogs.py -q
```

Expected: FAIL. `test_the_about_dialog_is_not_a_fixed_size` fails, because `setFixedSize` makes the minimum and the maximum the same number.

- [ ] **Step 3: Add the theme imports**

In `src/opaque/view/dialogs/version_info.py`, add this block directly below the last existing import line:

```python
from opaque.view.theme import (
    TypeScale,
    muted_on_surface,
    outline,
    surface_variant,
)
```

- [ ] **Step 4: Let the About dialog grow**

In the same file, replace this line:

```python
        self.setFixedSize(400, 300)
```

with exactly this:

```python
        # A minimum, not a fixed size. A translated string is often 30 to 40
        # per cent longer than the English source, and the operating system
        # font size can be set to Large. A fixed size cuts both off.
        self.setMinimumSize(400, 300)
```

Then replace this block in the same file:

```python
        framework_label.setAlignment(Qt.AlignCenter)
        framework_label.setStyleSheet("color: #666666;")
```

with exactly this:

```python
        framework_label.setAlignment(Qt.AlignCenter)
        self.framework_label_colour = muted_on_surface()
        framework_label.setStyleSheet(f"color: {self.framework_label_colour};")
```

- [ ] **Step 5: Give the version dialog a floor and the system tab a real font**

In the same file, replace this line:

```python
        self.resize(500, 400)
```

with exactly this:

```python
        self.setMinimumSize(480, 360)
        self.resize(500, 400)
```

Then replace this block:

```python
        text_widget = QTextEdit()
        text_widget.setReadOnly(True)
        text_widget.setFont(QFont("Courier", 9))
```

with exactly this:

```python
        text_widget = QTextEdit()
        text_widget.setReadOnly(True)
        # The platform fixed width font, at the size the user chose. A named
        # family is not installed everywhere and a fixed point size ignores
        # the operating system font scale.
        text_widget.setFont(TypeScale.mono())
        self.system_text = text_widget
```

- [ ] **Step 6: Replace the status widget style**

In the same file, replace this block:

```python
        self.setStyleSheet("""
            QLabel {
                padding: 2px 8px;
                border: 1px solid transparent;
                border-radius: 3px;
            }
            QLabel:hover {
                background-color: rgba(0, 0, 0, 0.1);
                border-color: rgba(0, 0, 0, 0.2);
            }
        """)
```

with exactly this:

```python
        # The hover colours come from the palette. A black overlay is
        # invisible on a dark theme.
        self.setStyleSheet(f"""
            QLabel {{
                padding: 2px 8px;
                border: 1px solid transparent;
                border-radius: 3px;
            }}
            QLabel:hover {{
                background-color: {surface_variant()};
                border-color: {outline()};
            }}
        """)
```

- [ ] **Step 7: Remove the unused font import**

In the same file, find the `from PySide6.QtGui import ...` line and delete `QFont` from it. Leave every other name on that line untouched.

- [ ] **Step 8: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_version_dialogs.py -q
```

Expected: PASS. `5 passed`.

- [ ] **Step 9: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `203 passed`.

- [ ] **Step 10: Commit**

```bash
git add src/opaque/view/dialogs/version_info.py tests/view/test_version_dialogs.py
git commit -m "fix(dialogs): let the About dialog grow and take its colours from the theme"
```

---

### Task 7: Connect the toolbar to the rest of the shell (C3, W6)

Plan 03 gave `OpaqueMainToolbar` three public methods, and nothing calls any of them:

- `update_theme()` repaints the toolbar after a theme change.
- `set_notifications_visible(bool)` makes the notification button show whether the panel is open.
- `set_notification_count(int)` shows the unread count on that button.

This task connects all three. Without it, Plan 03 and Plan 05 are only half finished.

**Files:**
- Modify: `src/opaque/view/application.py`
- Test: `tests/test_application_shell.py`

**Run this task only after Plan 03 and Plan 05 are merged.** It calls methods those plans create.

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/test_application_shell.py`:

```python
def test_a_theme_change_reaches_the_toolbar(app_window, monkeypatch):
    calls = []
    monkeypatch.setattr(
        app_window.toolbar, "update_theme", lambda: calls.append(True))

    app_window.theme_service.theme_changed.emit("Default")

    assert calls == [True]


def test_the_notification_dock_visibility_reaches_the_toolbar(
        app_window, monkeypatch):
    seen = []
    monkeypatch.setattr(
        app_window.toolbar, "set_notifications_visible", seen.append)

    dock = app_window.notification_presenter.get_notification_widget()
    dock.visibilityChanged.emit(True)

    assert seen == [True]


def test_the_notification_count_reaches_the_toolbar(app_window, monkeypatch):
    seen = []
    monkeypatch.setattr(
        app_window.toolbar, "set_notification_count", seen.append)

    model = app_window.notification_presenter.get_notification_model()
    model.notification_count_changed.emit(7)

    assert seen == [7]
```

Each of the three connections must be made through a `lambda`, not through the bound method. A signal connected straight to `self.toolbar.update_theme` keeps the method object it saw at connect time, and the test above could never see the call.

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_application_shell.py -q
```

Expected: FAIL. `test_a_theme_change_reaches_the_toolbar` fails with `assert [] == [True]`.

- [ ] **Step 3: Add the wiring method**

In `src/opaque/view/application.py`, add this method directly above `def _init_application_settings`:

```python
    def _wire_shell_signals(self) -> None:
        """
        Connect the toolbar to the services that change what it must show.

        Every connection below goes through a lambda on purpose. A signal
        connected straight to a bound method keeps the object it saw at
        connect time, which makes the connection impossible to replace in a
        test and impossible to follow when the toolbar is rebuilt.
        """
        self.theme_service.theme_changed.connect(
            lambda _name: self.toolbar.update_theme())

        dock = self.notification_presenter.get_notification_widget()
        if dock is not None:
            dock.visibilityChanged.connect(
                lambda visible: self.toolbar.set_notifications_visible(visible))

        model = self.notification_presenter.get_notification_model()
        if model is not None:
            model.notification_count_changed.connect(
                lambda count: self.toolbar.set_notification_count(count))
```

- [ ] **Step 4: Call it after the toolbar button exists**

In the same file, replace this block:

```python
        # Add notification toggle to toolbar
        self.toolbar.add_notification_button(self.notification_presenter.toggle_notifications)
```

with exactly this:

```python
        # Add notification toggle to toolbar
        self.toolbar.add_notification_button(
            self.notification_presenter.toggle_notifications)

        # The wiring must come after the notification button exists, because
        # set_notifications_visible and set_notification_count act on it.
        self._wire_shell_signals()
```

- [ ] **Step 5: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_application_shell.py -q
```

Expected: PASS. `21 passed`.

- [ ] **Step 6: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `206 passed`.

- [ ] **Step 7: Check the running application**

Run:

```
venv\Scripts\python.exe examples\basic_example\main.py
```

Expected, in this order:

1. The title bar reads the application name and the version, with **no** empty square brackets.
2. Open a feature window from the toolbar. Its button stays highlighted.
3. Close that feature window. Its button clears.
4. Open Settings. The feature is still listed there. This is C14.
5. Change the theme in Settings and press Apply. The toolbar repaints with the new theme.
6. Press the notification button. The panel opens and the button shows as pressed.

Close the window to end the check. If any step does not match, stop and report which one.

- [ ] **Step 8: Commit**

```bash
git add src/opaque/view/application.py tests/test_application_shell.py
git commit -m "feat(shell): connect the toolbar to the theme and notification signals"
```

---

## Definition of done

- [ ] `venv\Scripts\python.exe -m pytest tests/test_application_shell.py -q` prints `21 passed`.
- [ ] `venv\Scripts\python.exe -m pytest tests/view/test_version_dialogs.py -q` prints `5 passed`.
- [ ] `venv\Scripts\python.exe -m pytest -q` reports zero failures.
- [ ] `grep -n "del self._registered_features\|\.lab\|setFixedSize" src/opaque/view/application.py src/opaque/view/dialogs/version_info.py` returns no output.
- [ ] `grep -rn "^\s*print(" src/opaque/view/application.py src/opaque/presenters/` returns no output.
- [ ] The manual check in Task 7 Step 7 passes every one of its six points.

## Left for another plan

- `VersionStatusWidget` is a `QLabel` with a `mousePressEvent` handler. It cannot take the keyboard focus and a screen reader does not know it is a control. Plan 09 Task 3 turns it into a real button.
- The remaining `self.tr(f"...")` calls across the framework are Plan 10.
- `print()` in `src/opaque/services/` and `src/opaque/models/console_model.py` is Plan 11 Task 6.
