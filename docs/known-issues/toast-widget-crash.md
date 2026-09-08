# Known issue: intermittent access violation during the full test suite

**Status:** Fixed. See "Resolution" below. The crash was never in `ToastWidget` -
that was a plausible but incorrect suspect that shaped this report's title and
most of its investigation. The real cause was in `KeyboardMapDialog`
(`src/opaque/view/dialogs/keyboard_map.py`), fixed on the `plan-09-accessibility`
branch in the `opaque-plan-09` worktree, commit `3236c64` ("fix(a11y): stop
KeyboardMapDialog from double-deleting itself on teardown").

**Severity:** High. This was a Windows access violation (native crash, not a
Python exception), found in code that ships in the framework
(`KeyboardMapDialog`), not only in test code.

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
This timer has no Qt parent either. It is only started (`.start()`, single-shot, 10 ms) when auto-scroll batches an update. It was checked during the resolution below (see "What actually happened") and ruled out - it is not part of this crash. It shares the same "unparented QTimer on a widget with no explicit teardown" shape as the `ToastWidget` red herring, so it may still be worth hardening on its own merits, but it is not urgent.

## Resolution

The `ToastWidget` structural fixes attempted above (animation reparenting,
stopping the sweep test's abandoned toast's timer/animation) were all
addressing the wrong object. Systematic bisection of the exact repro command
(`pytest tests/theme tests/view/test_accessibility_sweep.py
tests/view/test_notification_widget.py -q`) established the following, each
confirmed by directly running the command, not by inspection alone:

- Removing `ToastWidget` entirely from the accessibility sweep's widget list
  did **not** stop the crash.
- Disabling the fade-in animation's `.start()` call entirely (so no
  `QPropertyAnimation` in the whole process was ever actually running) did
  **not** stop the crash either.
- Both results together rule out `ToastWidget` and its animation/effect
  ownership triangle as the cause. The two partial fixes described above are
  harmless but were never the fix.
- Bisecting the sweep's widget list by half, then by pair, then by singleton,
  isolated the crash to exactly one pair: `VersionInfoDialog` and
  `KeyboardMapDialog` built together. Neither alone reproduces it, only both
  together, which explains the original report's "needs enough Qt object
  churn" observation - it was never about volume in general, only about
  whether these two specific dialogs' construction and teardown landed close
  enough together in the same run.

### The real root cause

`KeyboardMapDialog.__init__` (`src/opaque/view/dialogs/keyboard_map.py`) took
a `window` argument, passed it as its own Qt parent
(`super().__init__(parent or window)`), and then additionally stored
`self._window = window`. That extra line was written to solve a real problem
(a caller passing a `window` with no other Python reference would see it
garbage collected immediately, and Qt would delete the dialog along with it,
since the dialog is `window`'s child) - but it solved it by pointing a strong
Python reference from the dialog back at its own Qt parent, which is the
wrong direction and is itself unsafe:

1. When the dialog's own Python wrapper is deallocated (for example, because
   the accessibility sweep test's local `widgets` list goes out of scope),
   clearing the dialog's `__dict__` drops the last reference to `self._window`.
2. If nothing else references `window`, that triggers `window`'s own,
   immediate deallocation, as part of the dialog's still-in-progress
   deallocation.
3. `window` has no Qt parent of its own, so deleting its C++ object runs
   `~QWidget()`, which cascades through Qt's normal parent-child mechanism and
   deletes its children's C++ objects - including the dialog's own C++
   `QDialog`, the very object whose Python-side teardown is what started this
   chain.
4. The dialog's C++ object is now deleted a second time (or accessed after
   its first, legitimate deletion) once control returns to the outer,
   still-running deallocation of the dialog itself: a reentrant double
   delete / use-after-free. This is consistent with why it needed `tests/theme`
   churn and a second dialog (`VersionInfoDialog`) nearby to manifest as an
   actual segfault reliably rather than silently landing on still-valid,
   not-yet-reused memory - classic use-after-free behaviour.

Every real (non-test) call site (`application.py`: `KeyboardMapDialog(self,
parent=self)`) passes the running application window as both `window` and
`parent`, which is never garbage collected mid-session, so this defect was
invisible in production and only reachable from a test that passes a
throwaway, unreferenced `QWidget()` - exactly what the accessibility sweep
test did.

### The fix

- `src/opaque/view/dialogs/keyboard_map.py`: removed `self._window = window`.
  Qt's own parent-child ownership already keeps the dialog alive exactly as
  long as `window` is alive; the dialog does not need, and must not take, a
  reference back to its own parent.
- `tests/view/test_accessibility_sweep.py`: the sweep's throwaway host window
  for `KeyboardMapDialog` is now a named `keyboard_map_window` local that is
  tracked in the same `widgets` list the sweep already uses to keep every
  other constructed object alive for the test's duration - the same pattern
  already used to keep the shared `notification` object alive across the
  `NotificationListItem` and `ToastWidget` entries.

Verified via the exact repro command run 8 consecutive times with zero
crashes, `tests/view/test_keyboard_map.py` (unaffected, still 5 passed), and
the full suite (`pytest -q`) run twice with zero regressions, 222 passed both
times (the same total as the unfixed baseline - this fix does not add or
remove any tests). Committed on `plan-09-accessibility` in the
`opaque-plan-09` worktree as `3236c64`.

## Lesson for next time

A plausible-looking, well-commented fix for one lifecycle hazard
(`self._window = window`, guarding against premature garbage collection) can
itself be the source of a second, worse hazard (a reentrant double delete) if
it reverses the direction of an existing Qt parent-child ownership
relationship. Never store a strong Python reference from a `QObject` back to
its own Qt parent to keep that parent alive; keep it alive from outside the
parent-child pair instead (as the accessibility sweep test now does).

## Where this was found

Found while executing Plan 09 (`docs/superpowers/plans/2026-09-07-opaque-ui-09-accessibility.md`) Task 4, the accessibility sweep test. The initial investigation misattributed it to `ToastWidget`, the first widget in the sweep's list to be constructed for inspection and abandoned rather than run through its normal close lifecycle; systematic bisection later traced it to `KeyboardMapDialog` and `VersionInfoDialog` instead (see "Resolution").
