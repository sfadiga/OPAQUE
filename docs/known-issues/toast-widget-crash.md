# Known issue: intermittent access violation in ToastWidget during the full test suite

**Status:** Open, unfixed. Blocks Plan 09 (accessibility sweep) Task 4 and everything that depends on it (Plans 10, 11) in `docs/superpowers/plans/2026-09-07-opaque-ui-*.md`.

**Severity:** High. This is a Windows access violation (native crash, not a Python exception), found in code that ships in the framework (`ToastWidget`), not only in test code.

## Symptom

Running the full `pytest -q` suite after Plan 09's Task 4 (`tests/view/test_accessibility_sweep.py`) is added crashes the whole test process with:

```
Windows fatal exception: access violation
```

The Python-level traceback at the moment of the crash always points to the same place:

```
File "...\pytestqt\qt_compat.py", line 160 in exec
File "...\pytestqt\wait_signal.py", line 58 in wait
File "...\pytestqt\wait_signal.py", line 155 in __exit__
File "tests\view\test_notification_widget.py", line 131 in test_closed_is_emitted_after_the_fade_out_finishes
```

That traceback only shows where the nested Qt event loop was pumping when the fault happened — it does not show which native slot Qt was dispatching. Finding that requires a real native debugger (e.g. WinDbg) attached to the Python process, which was not available in the environment where this was diagnosed.

## Reproduction

In a shell with the project's venv active and `PYTHONPATH` pointed at `src`:

```
pytest tests/theme tests/view/test_accessibility_sweep.py tests/view/test_notification_widget.py -q
```

This crashes reliably (confirmed on 6+ consecutive runs). Notes from isolating it:

- `tests/view` alone (which includes both the sweep and the notification widget tests) does **not** crash, run 5 times in a row.
- Adding `tests/theme` (all four files) before `tests/view` **does** crash, reliably.
- No single file under `tests/theme` on its own is enough to trigger it — only running the whole directory first.
- **Order matters.** Running `test_notification_widget.py` *before* `test_accessibility_sweep.py` avoids the crash entirely, even with the same `tests/theme` volume ahead of both. Running the sweep first, then the notification tests, crashes.
- Disabling Python's cyclic garbage collector (`gc.disable()`) before running pytest does **not** prevent the crash, which rules out GC-timing as the trigger.

This points to a genuine object-lifecycle race in `ToastWidget`, not simple test pollution or a GC scheduling artifact — it needs enough prior Qt object churn in the same process before it becomes visible, but it is deterministic given a fixed amount of that churn and a fixed test order.

## What was tried and did not fully fix it

Both applied in a scratch worktree, individually and together, verified against the repro above (6 runs each):

1. **Parent the fade animation to the widget.** In `src/opaque/view/widgets/notification_widget.py`, `_setup_animation` builds:
   ```python
   self.opacity_effect = QGraphicsOpacityEffect(self)   # parented to self
   self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")  # NOT parented
   ```
   The animation has no Qt parent, so its C++ lifetime is tied only to the Python reference `self.anim`, while its target (`opacity_effect`) is destroyed as soon as `self` is destroyed. Passing `self` as a third constructor argument (`QPropertyAnimation(self.opacity_effect, b"opacity", self)`) ties the animation's destruction to the widget's, which is the standard Qt-recommended pattern. This did not eliminate the crash (reduced apparent frequency in one small sample, but still crashed on repeated runs).

2. **Stop the toast's own timer and animation when it is never given to a presenter.** `tests/view/test_accessibility_sweep.py`'s `_every_widget()` helper builds one `ToastWidget` for inspection only, and previously left it to `qtbot`'s default teardown, which does not stop `close_timer` (a real `QTimer(self)` that starts on construction) or `anim` (the fade-in `QPropertyAnimation`, also running on construction). Added:
   ```python
   if isinstance(widget, ToastWidget):
       widget.close_timer.stop()
       widget.anim.stop()
   ```
   This is legitimate test hygiene regardless of the segfault (a test-only widget should not leave background timers armed) and has been kept in the Plan 09 worktree. It did **not** eliminate the crash either, alone or combined with fix 1.

Both fixes address plausible, real gaps in `ToastWidget`'s lifecycle management, but neither is the actual root cause of this specific crash. The real trigger is still unknown.

## Other latent issue noticed in passing (not confirmed related)

`src/opaque/view/widgets/console_widget.py:52`:
```python
self._scroll_timer = QTimer()
```
This timer has no Qt parent either. It is only started (`.start()`, single-shot, 10 ms) when auto-scroll batches an update, so it is less obviously live during the sweep than `ToastWidget`'s timers, but it shares the same "unparented QTimer on a widget with no explicit teardown" shape. Worth checking if this crash is ever chased again.

## Suggested next steps for whoever picks this up

- Attach a native debugger (WinDbg, or run under a debug-build Python/PySide6) to get the actual C++ frame at the moment of the access violation, rather than just the Python frame.
- Consider replacing `QGraphicsOpacityEffect` + `QPropertyAnimation` in `ToastWidget` with a simpler mechanism (e.g. a `QVariantAnimation` driving a stylesheet opacity, or a manual `QTimer`-stepped fade) if the effect/animation/target ownership triangle turns out to be the underlying PySide6 fragility.
- Consider giving `ToastWidget` a real `closeEvent` override and `WA_DeleteOnClose`, and auditing every place a `ToastWidget` can be constructed and abandoned without going through `close_toast()` — the accessibility sweep test is the first place that does this, but production code should not be able to leak the same way if, for example, a presenter is torn down mid-toast.

## Where this was found

Found while executing Plan 09 (`docs/superpowers/plans/2026-09-07-opaque-ui-09-accessibility.md`) Task 4, the accessibility sweep test, which is the first test in the suite to construct a `ToastWidget` purely for inspection and abandon it rather than running it through its normal close lifecycle.
