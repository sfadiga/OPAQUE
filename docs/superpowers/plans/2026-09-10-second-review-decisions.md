# Second Review Decision Items Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the five decision-bearing findings from the 2026-09-10 code review: the field `ui_type` asymmetry, the unbounded/float slider, the silent `setDecimals(6)` rounding, the i18n guarantee gap, and the skipped `on_view_close()` at application exit.

**Architecture:** Each task records its decision, then follows red-green-refactor. Tasks 1–3 harden the settings dialog and the field API. Task 4 makes the i18n and stylesheet guards enforce what the documentation claims. Task 5 routes application exit through the same close sequence as a manual window close, made unit-testable by an extracted `release_features()` method.

**Tech Stack:** Python 3.11, PySide6, pytest (headless, `QT_QPA_PLATFORM=offscreen`), mypy, pylint. `uv` owns the environment.

---

## Decisions this plan records

1. **`ui_type` override symmetry.** `ListField` and `FloatField` accept an explicit `ui_type` argument with the current value as the default, exactly like `StringField` and `IntField` already do. Rejected alternative: keep them locked — it raises `TypeError` at class-definition time and makes the API asymmetric for no gain.
2. **Slider faithfulness rule.** The dialog draws a `QSlider` only when it can represent the field faithfully: both bounds declared, and the field is not a float. Otherwise it falls back to the spinbox family, which has an open range and a fraction. Rejected alternatives: raise at build time (punishes the end user for a developer mistake), or keep Qt's silent 0–99 clamp (corrupts stored data).
3. **Float precision.** The double spinbox default stays at six decimals. A field may declare more with `FloatField(decimals=N, ...)` (carried by the existing `extra_config`), and the widget widens automatically when the stored value needs more places than it shows, so a value can never display as `0.000000` and be written back as `0.0`. Cap: 15 places.
4. **i18n and stylesheet guards get stronger, not the docs weaker.** The missing-`tr()` scanner learns to flag f-strings with readable text, runs over the examples, and every offending string in `examples/` and `src/opaque` is fixed. The literal-style guard scans every string constant in an example file, not only constants lexically inside a `setStyleSheet` call. After that, the CLAUDE.md claim is true and stays as written.
5. **Application exit runs the full close sequence.** `BaseApplication.closeEvent` calls a new public `BasePresenter.shutdown()` (the guarded `on_view_close()` + `cleanup()` sequence) instead of bare `cleanup()`. The shutdown order in CLAUDE.md is unchanged: features first, services after. The loop moves into `BaseApplication.release_features()` so a unit test can run it without closing the session-scoped `app_window` fixture.

---

### Task 1: `ListField` and `FloatField` accept an explicit `ui_type`

**Files:**
- Modify: `src/opaque/models/annotations.py` (classes `FloatField`, `ListField`)
- Test: `tests/models/test_field_coercion.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/models/test_field_coercion.py`:

```python
from opaque.models.annotations import FloatField, ListField, UIType


def test_a_list_field_accepts_an_explicit_ui_type():
    """A comma-text editor is a valid choice; the argument used to raise
    TypeError ('multiple values for ui_type') at class-definition time."""
    field = ListField(ui_type=UIType.TEXT)
    assert field.ui_type is UIType.TEXT


def test_a_float_field_accepts_an_explicit_ui_type():
    field = FloatField(ui_type=UIType.SLIDER)
    assert field.ui_type is UIType.SLIDER


def test_the_ui_type_defaults_are_unchanged():
    assert ListField().ui_type is UIType.LIST_VIEW
    assert FloatField().ui_type is UIType.DOUBLE_SPINBOX
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/models/test_field_coercion.py -k ui_type -q`
Expected: two FAIL with `TypeError: ... got multiple values for keyword argument 'ui_type'`; the defaults test passes.

- [ ] **Step 3: Implement**

In `src/opaque/models/annotations.py` replace the two `__init__` methods:

```python
class FloatField(Field):
    """Field for float values."""

    def __init__(self, ui_type: UIType = UIType.DOUBLE_SPINBOX,
                 **kwargs: Any):
        # A float needs a widget with a fraction by default. It used to
        # declare UIType.SPINBOX, so the dialog drew a QSpinBox and
        # truncated every value it read back.
        super().__init__(ui_type=ui_type, **kwargs)
```

```python
class ListField(Field):
    """Field for list values. Shown and edited as a list; coerce() still
    accepts comma separated text for old settings files."""

    def __init__(self, ui_type: UIType = UIType.LIST_VIEW, **kwargs: Any):
        super().__init__(ui_type=ui_type, **kwargs)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run python -m pytest tests/models/test_field_coercion.py -q`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/opaque/models/annotations.py tests/models/test_field_coercion.py
git commit -m "feat(models): ListField and FloatField accept an explicit ui_type"
```

---

### Task 2: the slider falls back when it cannot represent the field

**Files:**
- Modify: `src/opaque/view/dialogs/settings.py` (the widget-building loop in the form builder, currently the `field.ui_type` branch chain near line 410)
- Test: `tests/view/test_settings_dialog.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/view/test_settings_dialog.py`:

```python
class OpenSliderModel(AbstractModel):
    """A slider without bounds and a float slider; neither is drawable."""

    FEATURE_ID = "open_slider"

    level = IntField(default=500, description="Level", settings=True,
                     ui_type=UIType.SLIDER)
    ratio = FloatField(default=0.5, min_value=0.0, max_value=1.0,
                       description="Ratio", settings=True,
                       ui_type=UIType.SLIDER)

    def feature_name(self) -> str:
        return "OpenSlider"

    def feature_icon(self):
        from PySide6.QtGui import QIcon
        return QIcon()


@pytest.fixture
def open_slider_dialog(qtbot, service):
    presenter = DemoPresenter(OpenSliderModel())
    presenter.feature_id = "open_slider"
    widget = SettingsDialog([presenter], parent=None)
    qtbot.addWidget(widget)
    return widget


def test_a_slider_without_bounds_falls_back_to_a_spinbox(open_slider_dialog):
    """Qt's default slider range is 0-99. A stored 500 rendered at 99 and
    one drag wrote the clamped value back. The spinbox has an open range."""
    assert _widget_for(open_slider_dialog, "Level").value() == 500
    assert isinstance(_widget_for(open_slider_dialog, "Level"), QSpinBox)


def test_a_float_slider_falls_back_to_a_double_spinbox(open_slider_dialog):
    """QSlider moves in integer steps and truncates every fraction."""
    widget = _widget_for(open_slider_dialog, "Ratio")
    assert isinstance(widget, QDoubleSpinBox)
    assert widget.value() == 0.5


def test_a_bounded_int_slider_is_still_a_slider(rich_dialog):
    assert isinstance(_widget_for(rich_dialog, "Volume"), QSlider)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/view/test_settings_dialog.py -k slider -q`
Expected: the two fallback tests FAIL (a `QSlider` is drawn, and the level slider reads 99); the bounded test passes.

- [ ] **Step 3: Implement**

In `src/opaque/view/dialogs/settings.py`:

1. Import `FloatField` next to the existing `UIType` import:

```python
from opaque.models.annotations import FloatField, UIType
```

2. Add this method to `SettingsDialog`:

```python
def _effective_ui_type(self, field: Any) -> Optional[UIType]:
    """
    Return the ui_type the form actually draws for this field.

    A slider can only represent a field faithfully when both bounds
    are declared and the value is an integer: Qt's default range is
    0-99, which silently clamps the stored value on the first drag,
    and QSlider moves in integer steps, which truncates a float. In
    both cases the spinbox family draws the field instead.
    """
    ui_type = getattr(field, "ui_type", None)
    if ui_type != UIType.SLIDER:
        return ui_type
    if isinstance(field, FloatField):
        return UIType.DOUBLE_SPINBOX
    if field.min_value is None or field.max_value is None:
        return UIType.SPINBOX
    return ui_type
```

3. In the widget-building loop, right after `current_value = self._effective_value(...)`, add:

```python
ui_type = self._effective_ui_type(field)
```

and change every branch condition from `hasattr(field, 'ui_type') and field.ui_type == UIType.X` to `ui_type == UIType.X`. The combo branch becomes `elif ui_type in (UIType.COMBOBOX, UIType.DROPDOWN) or field.choices:`. The `hasattr` guard is subsumed: `getattr(field, "ui_type", None)` returns `None` for an object without the attribute, and `None` matches no branch, so the default `QLineEdit` branch still catches it.

4. In the now-guaranteed-bounded SLIDER branch, drop the two `if ... is not None` bound checks and the fallback comment; set the range unconditionally:

```python
elif ui_type == UIType.SLIDER:
    widget = QSlider(Qt.Orientation.Horizontal)
    # _effective_ui_type only lets a slider through with both
    # bounds declared and an integer value.
    widget.setRange(int(field.min_value), int(field.max_value))
    if current_value is not None:
        widget.setValue(int(current_value))
    widget.valueChanged.connect(
        lambda value, fid=feature_id, name=name: self._record_pending(
            fid, name, value)
    )
```

- [ ] **Step 4: Run the dialog tests and the full suite**

Run: `uv run python -m pytest tests/view/test_settings_dialog.py -q && uv run python -m pytest tests -q`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/opaque/view/dialogs/settings.py tests/view/test_settings_dialog.py
git commit -m "fix(settings): a slider that cannot represent its field falls back to a spinbox"
```

---

### Task 3: float precision is declared, and never silently rounded away

**Files:**
- Modify: `src/opaque/view/dialogs/settings.py` (module top for the helper, and the DOUBLE_SPINBOX branch)
- Test: `tests/view/test_settings_dialog.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/view/test_settings_dialog.py`:

```python
class PrecisionModel(AbstractModel):
    """Floats finer than the default six decimal places."""

    FEATURE_ID = "precision"

    tiny = FloatField(default=1e-7, description="Tiny", settings=True)
    declared = FloatField(default=0.5, decimals=9,
                          description="Declared", settings=True)

    def feature_name(self) -> str:
        return "Precision"

    def feature_icon(self):
        from PySide6.QtGui import QIcon
        return QIcon()


@pytest.fixture
def precision_dialog(qtbot, service):
    presenter = DemoPresenter(PrecisionModel())
    presenter.feature_id = "precision"
    widget = SettingsDialog([presenter], parent=None)
    qtbot.addWidget(widget)
    return widget


def test_a_tiny_float_is_not_rounded_to_zero(precision_dialog):
    """setDecimals(6) displayed 1e-7 as 0.000000, and the first user
    interaction wrote the rounded 0.0 back into the model."""
    widget = _widget_for(precision_dialog, "Tiny")
    assert widget.value() == 1e-7


def test_a_declared_decimals_widens_the_widget(precision_dialog):
    widget = _widget_for(precision_dialog, "Declared")
    assert widget.decimals() == 9


def test_the_default_stays_at_six_decimals(typed_dialog):
    widget = _widget_for(typed_dialog, "Ratio")
    assert widget.decimals() == 6
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/view/test_settings_dialog.py -k "decimals or tiny" -q`
Expected: the tiny test FAILS with `assert 0.0 == 1e-07`; the declared test FAILS with `assert 6 == 9`; the default test passes.

- [ ] **Step 3: Implement**

In `src/opaque/view/dialogs/settings.py`, add `import math` to the standard-library imports and this module-level helper:

```python
def _decimal_places(field: Any, current_value: Any) -> int:
    """
    Return the decimal places the double spinbox must show.

    The default is six. A field may declare more with decimals=N (the
    keyword lands in Field.extra_config), and a stored value smaller
    than the shown precision widens the result, so the box can never
    display 1e-7 as 0.000000 and write the rounded 0.0 back on the
    first edit. Qt caps a QDoubleSpinBox at 15 useful places.
    """
    decimals = int(field.extra_config.get("decimals", 6))
    if current_value:
        needed = -math.floor(math.log10(abs(float(current_value))))
        decimals = max(decimals, min(needed, 15))
    return decimals
```

In the DOUBLE_SPINBOX branch replace `widget.setDecimals(6)` with:

```python
widget.setDecimals(_decimal_places(field, current_value))
```

- [ ] **Step 4: Run the dialog tests and the full suite**

Run: `uv run python -m pytest tests/view/test_settings_dialog.py -q && uv run python -m pytest tests -q`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/opaque/view/dialogs/settings.py tests/view/test_settings_dialog.py
git commit -m "fix(settings): the double spinbox shows the precision the value needs"
```

---

### Task 4: the i18n and stylesheet guards enforce what CLAUDE.md claims

**Files:**
- Modify: `tests/test_localisation.py` (`_is_a_readable_string`)
- Modify: `tests/test_example_hygiene.py` (two new checks, one widened check)
- Modify: `src/opaque/presenters/console_presenter.py:171`
- Modify: `src/opaque/view/dialogs/version_info.py:410`
- Modify: `src/opaque/view/widgets/closeable_tab_widget.py:157`
- Modify: `examples/basic_example/features/calculator/view.py` (three bare literals)
- Modify: `examples/notification_example/main.py` (eight f-string `setText` calls)

- [ ] **Step 1: Write the failing scanner tests**

Append to `tests/test_localisation.py`:

```python
def test_the_scanner_catches_an_fstring_with_words(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text(
        'def build(label, count):\n'
        '    label.setText(f"Sent {count} messages")\n',
        encoding="utf-8",
    )
    assert _untranslated_strings(sample) == [2]


def test_an_fstring_of_pure_placeholders_passes(tmp_path):
    """f"{label} ({count})" holds no words of its own; the parts were
    translated where they were made."""
    sample = tmp_path / "sample.py"
    sample.write_text(
        'def build(label, a, b):\n'
        '    label.setText(f"{a} ({b})")\n',
        encoding="utf-8",
    )
    assert _untranslated_strings(sample) == []
```

- [ ] **Step 2: Run them to verify one fails**

Run: `uv run python -m pytest tests/test_localisation.py -k fstring -q`
Expected: the first FAILS (`assert [] == [2]`), the second passes.

- [ ] **Step 3: Teach the scanner to read f-strings**

In `tests/test_localisation.py` replace `_is_a_readable_string`:

```python
def _is_a_readable_string(node: ast.AST) -> bool:
    """True for a string literal, or an f-string, holding a letter."""
    if isinstance(node, ast.JoinedStr):
        return any(
            isinstance(part, ast.Constant)
            and isinstance(part.value, str)
            and any(character.isalpha() for character in part.value)
            for part in node.values
        )
    if not isinstance(node, ast.Constant):
        return False
    if not isinstance(node.value, str):
        return False
    return any(character.isalpha() for character in node.value)
```

- [ ] **Step 4: Run the scanner tests, then the src-wide scan, and watch the src scan fail**

Run: `uv run python -m pytest tests/test_localisation.py -q`
Expected: the two new tests PASS; the whole-source scan test now FAILS listing exactly three lines: `console_presenter.py:171`, `version_info.py:410`, `closeable_tab_widget.py:157`.

- [ ] **Step 5: Fix the three src sites**

`src/opaque/presenters/console_presenter.py:171` (inside `_export_console`; the presenter is not a QObject, so tr() comes from the widget):

```python
console_widget.status_label.setText(
    console_widget.tr("Exported to {0}").format(file_path))
```

`src/opaque/view/dialogs/version_info.py:410`:

```python
version_label = QLabel(self.tr("Version {0}").format(info.version))
```

`src/opaque/view/widgets/closeable_tab_widget.py:157`:

```python
layout.addWidget(QLabel(
    self.tr("Error creating widget: {0}").format(e)))
```

Run: `uv run python -m pytest tests/test_localisation.py -q`
Expected: all PASS.

- [ ] **Step 6: Add the failing example checks**

Append to `tests/test_example_hygiene.py` (extend the existing import from `tests.test_localisation` with `_untranslated_strings`):

```python
@pytest.mark.parametrize(
    "path", _example_files(),
    ids=lambda p: str(p.relative_to(EXAMPLES_ROOT)))
def test_every_user_visible_string_is_translated(path):
    offenders = _untranslated_strings(path)
    assert not offenders, (
        f"{path}: user-visible string outside self.tr() at lines "
        f"{offenders}. Wrap the literal in self.tr(); format an "
        f"f-string as self.tr('... {{0}} ...').format(value)."
    )
```

Widen the literal-style guard in the same file so a hoisted stylesheet variable cannot evade it — replace the body of `_stylesheet_offenders` with a file-wide constant scan:

```python
# A string that is one bare colour and nothing else is data (a colour
# picker default), not a stylesheet. A stylesheet always carries more
# text around the colour.
_BARE_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\Z")


def _stylesheet_offenders(path: Path) -> List[Tuple[int, str]]:
    """The literal-style patterns (hex colours in CSS text, font sizes,
    named CSS colours) only ever appear in stylesheet text, so every
    string constant in the file is scanned. Scanning only inside the
    setStyleSheet call missed a stylesheet hoisted into a variable."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders: List[Tuple[int, str]] = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and _LITERAL_STYLE.search(node.value)
                and not _BARE_COLOR.match(node.value.strip())):
            offenders.append((node.lineno, node.value.strip()))
    return offenders
```

- [ ] **Step 7: Run the hygiene tests to verify the i18n check fails on the known sites**

Run: `uv run python -m pytest tests/test_example_hygiene.py -q`
Expected: `test_every_user_visible_string_is_translated` FAILS for `basic_example/features/calculator/view.py` (three lines) and `notification_example/main.py` (eight lines). The widened style guard stays green: the only file-wide hit is the calculator's colour-picker default `"#4CAF50"` (`calculator/model.py:43`), which the bare-colour exemption passes on purpose.

- [ ] **Step 8: Fix the eleven example sites**

`examples/basic_example/features/calculator/view.py`:

```python
history_group = QGroupBox(self.tr("History"))
```

```python
clear_history_btn = QPushButton(self.tr("Clear History"))
```

```python
self.status_label = QLabel(self.tr("Ready"))
```

`examples/notification_example/main.py` — every `status_label.setText(f"...")` becomes a `tr().format()` call; the class is a QWidget, so `self.tr` exists:

```python
self.status_label.setText(
    self.tr("Sent {0} notification (ID: {1})").format(
        level_text, notification_id))
```

```python
self.status_label.setText(
    self.tr("Error sending notification: {0}").format(e))
```

```python
self.status_label.setText(
    self.tr("Logged {0} message").format(level_text))
```

```python
self.status_label.setText(
    self.tr("Error logging message: {0}").format(e))
```

```python
self.status_label.setText(
    self.tr("Error running demo: {0}").format(e))
```

```python
self.status_label.setText(
    self.tr("Demo error: {0}").format(e))
```

```python
self.status_label.setText(
    self.tr("Error toggling notifications: {0}").format(e))
```

```python
self.status_label.setText(
    self.tr("Error clearing notifications: {0}").format(e))
```

- [ ] **Step 9: Run the full suite, mypy and pylint**

Run: `uv run python -m pytest tests -q && uv run python -m mypy src/opaque && uv run python -m pylint src/opaque`
Expected: all PASS, no issues, 10.00/10.

- [ ] **Step 10: Commit**

```bash
git add tests/test_localisation.py tests/test_example_hygiene.py src/opaque examples
git commit -m "test(i18n): the scanner reads f-strings and sweeps the examples, and every hit is fixed"
```

---

### Task 5: application exit runs `on_view_close()` for open windows

**Files:**
- Modify: `src/opaque/presenters/presenter.py` (new `shutdown()`, docstring truth fixes)
- Modify: `src/opaque/shell.py` (`closeEvent`, new `release_features()`)
- Modify: `CLAUDE.md` (the shutdown-order bullet)
- Test: `tests/test_presenter_contract.py`, `tests/test_application_shell.py`

- [ ] **Step 1: Write the failing presenter tests**

Append to `tests/test_presenter_contract.py`:

```python
def test_shutdown_runs_the_hook_then_the_cleanup(make_presenter):
    """At application exit the shell used to call cleanup() directly,
    so a window still open at exit silently lost the state its
    on_view_close() hook would have saved."""
    presenter = make_presenter()
    presenter.shutdown()
    assert presenter.events[-2:] == ["on_view_close", "cleanup"]


def test_shutdown_after_a_manual_close_does_nothing(make_presenter):
    presenter = make_presenter()
    presenter.view.window_closed.emit()
    presenter.events.clear()

    presenter.shutdown()

    assert presenter.events == []
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run python -m pytest tests/test_presenter_contract.py -k shutdown -q`
Expected: FAIL with `AttributeError: ... has no attribute 'shutdown'`.

- [ ] **Step 3: Implement `shutdown()` and fix the docstrings**

In `src/opaque/presenters/presenter.py`, after `_handle_view_closed`:

```python
def shutdown(self) -> None:
    """
    Run the close sequence for a window that is still open.

    The shell calls this at application exit, so on_view_close() runs
    for every feature exactly as it runs when the user closes the
    sub-window by hand. Safe to call after a manual close: the
    sequence runs once.
    """
    self._handle_view_closed()
```

In the `on_view_close` docstring, replace the paragraph added on 2026-09-10 ("The hook runs when the sub-window itself closes. At application exit the shell calls cleanup() directly, so a window that is still open at that moment does not run this hook.") with:

```
The hook runs on a manual window close and at application exit,
once per presenter.
```

- [ ] **Step 4: Run the presenter tests**

Run: `uv run python -m pytest tests/test_presenter_contract.py -q`
Expected: all PASS.

- [ ] **Step 5: Write the failing shell test**

`app_window` is session-scoped, so no test may close it. The loop moves into `release_features()`, which a stand-in can run. Append to `tests/test_application_shell.py`:

```python
def test_release_features_runs_the_full_close_sequence(qapp):
    """closeEvent used to call cleanup() directly, skipping
    on_view_close() for every window still open at exit."""
    from opaque.shell import BaseApplication

    calls = []

    class _Presenter:
        feature_id = "fake"

        def shutdown(self):
            calls.append("shutdown")

    class _ShellStandIn:
        _registered_features = {"fake": _Presenter()}
        release_features = BaseApplication.release_features

    _ShellStandIn().release_features()

    assert calls == ["shutdown"]


def test_release_features_guards_a_raising_presenter(qapp):
    from opaque.shell import BaseApplication

    calls = []

    class _Raising:
        feature_id = "raising"

        def shutdown(self):
            raise RuntimeError("boom")

    class _Fine:
        feature_id = "fine"

        def shutdown(self):
            calls.append("shutdown")

    class _ShellStandIn:
        _registered_features = {"raising": _Raising(), "fine": _Fine()}
        release_features = BaseApplication.release_features

    _ShellStandIn().release_features()

    assert calls == ["shutdown"]
```

- [ ] **Step 6: Run them to verify they fail**

Run: `uv run python -m pytest tests/test_application_shell.py -k release_features -q`
Expected: FAIL with `AttributeError: type object 'BaseApplication' has no attribute 'release_features'`.

- [ ] **Step 7: Implement `release_features()` and route `closeEvent` through it**

In `src/opaque/shell.py`, replace the presenter loop inside `closeEvent` with a call, and add the method:

```python
def release_features(self) -> None:
    """
    Run every feature's close sequence: on_view_close(), then cleanup().

    An MDI sub-window receives no closeEvent of its own when the main
    window closes, so without this call a window still open at exit
    skipped its on_view_close() hook and silently lost the state the
    hook saves. One presenter that raises must not stop the others,
    so each one is guarded.
    """
    for feature_id, presenter in list(self._registered_features.items()):
        try:
            presenter.shutdown()
        except Exception:  # pylint: disable=broad-except
            logger.exception(
                "The feature %s failed to shut down", feature_id)


def closeEvent(self, event: QCloseEvent):
    """
    Release the features first, then the services.

    The order matters. A presenter saves its state on the way down, and it
    asks the settings service or the workspace service to do it. Cleaning
    the services up first handed every presenter a service that had
    already released everything, so the last thing the user did was the
    most likely thing to be lost.
    """
    self.release_features()
    ServiceLocator.cleanup_services()
    super().closeEvent(event)
```

- [ ] **Step 8: Run the shell tests and the full suite**

Run: `uv run python -m pytest tests/test_application_shell.py -q && uv run python -m pytest tests -q`
Expected: all PASS. Watch `tests/test_signal_policy.py` and the shutdown-order tests in particular; the feature-before-service order is unchanged, only the per-feature sequence grew.

- [ ] **Step 9: Update CLAUDE.md**

In the Architecture section, replace the shutdown-order bullet:

```
- **Shutdown order**: `BaseApplication.closeEvent` runs every feature's full close sequence first (`on_view_close()`, then `cleanup()`, via `BasePresenter.shutdown()`) and releases the services afterwards, each presenter guarded, so a presenter can still use a service while it saves. `on_view_close()` therefore runs on a manual window close and at application exit, once per presenter. Do not move the service cleanup earlier.
```

- [ ] **Step 10: Run everything and commit**

Run: `uv run python -m pytest tests -q && uv run python -m mypy src/opaque && uv run python -m pylint src/opaque`
Expected: all PASS, no issues, 10.00/10.

```bash
git add src/opaque/presenters/presenter.py src/opaque/shell.py CLAUDE.md tests/test_presenter_contract.py tests/test_application_shell.py
git commit -m "fix(shell): application exit runs on_view_close for every open window"
```

---

## Out of scope

- `BoolField` and `ChoiceField` keep their locked `ui_type`; open them with the Task 1 pattern only when a caller needs it.
- The calculator's `font.setPointSize(20)` literal predates this review and is not stylesheet text, so no guard sees it; sweep it into `TypeScale` when the examples are next touched.
- The docstring of `ListField.coerce` still advertises comma text on purpose: Task 1 makes `ListField(ui_type=UIType.TEXT)` legal, and that editor needs the comma round trip.
