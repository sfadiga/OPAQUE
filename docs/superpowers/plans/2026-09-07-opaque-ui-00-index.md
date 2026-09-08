# OPAQUE UI Audit Remediation — Plan Index

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement each plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair every finding of the 2026-09-07 Qt Widgets UI audit of the OPAQUE framework, in an order where each plan ships working software on its own.

**Architecture:** The audit found 44 defects across eleven loosely-coupled subsystems. Most of the colour, font and contrast defects share one root cause: every widget writes its own literal hex colours and font families. Plan 02 creates one semantic token layer plus one type scale, and every later plan consumes it. Plan 01 creates the test harness the project declares in `pyproject.toml` but never built.

**Tech Stack:** Python 3.8+, PySide6, pytest, pytest-qt. Existing third-party themes: `qdarkstyle`, `qt-material`, `qt-themes`.

---

## Rules for the executing agent

Read these before every task. They are not optional.

1. Do the steps in order. Do not skip a step. Do not reorder steps.
2. Do not change a file that the task does not list under **Files**.
3. Run every command exactly as written. Compare the real output to **Expected**.
4. If the real output does not match **Expected**, stop. Report the difference. Do not continue to the next step.
5. Do not add features. Do not refactor code that the task does not name.
6. Never delete or skip a test to make a suite pass.
7. Commit at the end of every task. Use the exact commit message given.
8. Every new string the user can see must be inside `self.tr("...")` with a **literal** argument. Never write `self.tr(f"...")`. Never write `self.tr(some_variable)`. `lupdate` cannot read those.
9. Never write a colour, a font family or a font size as a literal value in a widget. Import them from `opaque.view.theme`.
10. The Python interpreter for every command is `venv\Scripts\python.exe`. Run all commands from the repository root, `C:\Users\sfadiga\sandro\opaque`.

---

## Plan order

Run the plans in this order. Plan 01 and Plan 02 are prerequisites for all the others.

| # | Plan | Findings closed | Depends on | Suite total after |
|---|---|---|---|---|
| 01 | [Test harness](2026-09-07-opaque-ui-01-test-harness.md) | none (enables all) | — | 3 |
| 02 | [Theme tokens and type scale](2026-09-07-opaque-ui-02-theme-tokens.md) | O1, W22, W23, part of C5, C6 | 01 | 47 |
| 03 | [Toolbar state and theme propagation](2026-09-07-opaque-ui-03-toolbar-state.md) | C1, C2, part of C3, part of W6, O2 | 02 | 65 |
| 04 | [Theme default and Settings dialog](2026-09-07-opaque-ui-04-theme-and-settings.md) | C4, W13, W14, W15, W16 | 02 | 93 |
| 05 | [Notification system](2026-09-07-opaque-ui-05-notifications.md) | C6, C7, C9, C13a, W1, W2, W3, W4, W5, W7 | 02 | 130 |
| 06 | [Console widget](2026-09-07-opaque-ui-06-console.md) | C5, C12, part of C8, C9, W22 | 02 | 155 |
| 07 | [Tabs and ColorPicker](2026-09-07-opaque-ui-07-tabs-and-colorpicker.md) | C13b, W8, W9, W10, W11, W12 | 02 | 180 |
| 08 | [Application shell and dialogs](2026-09-07-opaque-ui-08-application-shell.md) | C10, C14, W17, W18, W19, W20, W21, part of C3, C8 | 02, 03, 05 | 206 |
| 09 | [Accessibility sweep](2026-09-07-opaque-ui-09-accessibility.md) | C8, C9, O4 | 03–08 | 221 |
| 10 | [Localisation](2026-09-07-opaque-ui-10-localisation.md) | C11 | 03–09 | 233 |
| 11 | [Opportunities](2026-09-07-opaque-ui-11-opportunities.md) | O3, O5, O6, O7, O8, rest of W17 | 09, 10 | 254 |

Plans 03 to 07 do not depend on each other. Run them in parallel if you have more than one worker. Plan 08 needs Plan 03 and Plan 05 to be merged first, because its Task 7 calls methods those plans create.

**The `Suite total after` column assumes the plans run in this order.** If you run some of them in parallel, ignore that column, compare only the per-file counts each plan gives, and require zero failures in the whole suite.

---

## Finding to plan map

Use this table to confirm coverage. Every finding in the audit appears here with every task that touches it.

### Critical

| ID | Finding | Owner |
|---|---|---|
| C1 | Toolbar active state never clears (`toolbar.py:86`) | 03 Task 2 |
| C2 | Active state is colour only, `opacity` is not a valid Qt property | 03 Task 3 |
| C3 | `update_theme()` has no caller | 03 Task 3, 08 Task 7 |
| C4 | Default theme `"light"` is not a valid theme name | 04 Task 1, Task 2 |
| C5 | Console and dialogs hardcode colours, ignore the theme | 02 Task 2, 06 Task 2, 08 Task 6 |
| C6 | Hardcoded greys fail 4.5:1 contrast | 02 Task 3, 05 Task 3 |
| C7 | Notification level uses colour as the only cue | 05 Task 2 |
| C8 | No keyboard layer at all | 06 Task 5, 08 Task 2, 09 Task 2, Task 3, Task 4 |
| C9 | Hit targets 16–30 px | 05 Task 3, 06 Task 5, 07 Task 5, 09 Task 3, Task 4 |
| C10 | Fixed pixel dialogs clip text | 08 Task 6 |
| C11 | Localisation does not work | 10 all |
| C12 | Console search never highlights or navigates | 06 Task 1, Task 3, Task 4 |
| C13 | Destructive actions with no confirmation | 05 Task 5 (a), 07 Task 3 (b) |
| C14 | Feature de-registers itself on window close, losing its Settings page and its `cleanup()` | 08 Task 1 |

### Warning

| ID | Finding | Owner |
|---|---|---|
| W1 | Toast position uses widget-local coordinates as global | 05 Task 1, Task 4 |
| W2 | Toast exit animation never plays, object deleted early | 05 Task 6 |
| W3 | Fixed 4 s dismiss, no hover pause | 05 Task 7 |
| W4 | Toast stack has no cap | 05 Task 1, Task 4 |
| W5 | Two startup toasts report that nothing happened | 05 Task 8 |
| W6 | Notification count discarded, no unread badge | 03 Task 4, 08 Task 7 |
| W7 | Notification dock steals space at startup | 05 Task 8 |
| W8 | ColorPicker swatch invisible under stylesheet themes | 07 Task 4 |
| W9 | ColorPicker gives no validation feedback | 07 Task 5 |
| W10 | `"+"` tab identified by label text | 07 Task 1 |
| W11 | Modal dialog opened from `currentChanged` | 07 Task 2 |
| W12 | Minimum-tab rule enforced with a warning box | 07 Task 3 |
| W13 | Settings write through on keystroke, Cancel unreliable | 04 Task 3, Task 4 |
| W14 | Modal success box on Apply | 04 Task 5 |
| W15 | `palette(highlight)` used as a text colour | 04 Task 6 |
| W16 | Settings search gives no result count | 04 Task 6 |
| W17 | Errors go to `print()` | 08 Task 3, 11 Task 6 |
| W18 | `load_workspace` discards its own argument | 08 Task 4 |
| W19 | Drag and drop never accepts a real workspace file | 08 Task 5 |
| W20 | `setMinimumSize` called with the maximum size | 08 Task 2 |
| W21 | Window title shows an empty bracket pair | 08 Task 2 |
| W22 | Fonts hardcoded by family and point size | 02 Task 5, 06 Task 2 |
| W23 | No type scale | 02 Task 5 |

### Opportunity

| ID | Finding | Owner |
|---|---|---|
| O1 | Token layer | 02 all |
| O2 | Use Qt native checked state | 03 Task 2 |
| O3 | Expose `QMdiArea` tabbed view mode | 11 Task 2 |
| O4 | Publish a keyboard map | 09 Task 1, Task 2 |
| O5 | Debug-build UI self-check | 11 Task 5 |
| O6 | Group and filter the notification centre | 11 Task 3 |
| O7 | Shared busy-state primitive | 11 Task 4 |
| O8 | `FlowLayout.minimumSize` axis defect | 11 Task 1 |

---

## Three corrections to the audit

The planning pass read every file the audit named. Three findings were stated wrongly, and each owning plan repeats the correction where the work happens.

1. **C12 was too broad.** The console search does count matches today. `ConsolePresenter._perform_search` calls `ConsoleModel.search_output` and that works. What is missing is the highlight, the navigation, and any map from a match index to a text block. See Plan 06.
2. **W19 had the wrong cause.** `QMainWindow` turns `acceptDrops` on by itself, so the drop handlers do run. They only accept `.lab`, while the configured extension is `.wks`. See Plan 08.
3. **C4 and C14 were understated.** A stale `theme` value in `settings.json` **crashes the application at start up**, because `ModelMeta` generates a setter that raises `ValueError` for a value outside `choices`. And C14 is not only a registry leak: a closed feature window takes the feature's Settings page away for the rest of the session and stops its `cleanup()` from ever running. See Plan 04 and Plan 08.

---

## Definition of done for the whole set

- [ ] `venv\Scripts\python.exe -m pytest -q` passes with zero failures and reports at least `254 passed`.
- [ ] `venv\Scripts\python.exe -m pytest tests/theme/test_contrast.py -q` proves every status colour pair is at or above 4.5:1 in both the light and the dark palette.
- [ ] `grep -rn "color: gray\|#666666\|#1e1e1e\|QFont(\"" src/opaque/view/` returns nothing.
- [ ] `venv\Scripts\python.exe -m pytest tests/test_localisation.py -q` passes. It fails the build on any `tr()` call that does not hold a literal, and on any user visible string outside `tr()`.
- [ ] `venv\Scripts\python.exe -m pytest tests/view/test_accessibility_sweep.py -q` passes. It fails the build on any button capped below 24 pixels and on any control a screen reader cannot name.
- [ ] `venv\Scripts\python.exe examples\basic_example\main.py` starts, and every toolbar button clears its highlight when its window closes.
