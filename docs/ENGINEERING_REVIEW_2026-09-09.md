# OPAQUE Framework — Verification Review

Date: 2026-09-09.
Scope: verification of every closure claim in `docs/ENGINEERING_REVIEW.md` (2026-09-08), plus a fresh audit of the six example applications and all Markdown documentation.
Method: four parallel code explorations with direct source reads, a full test run, mypy, pylint, and an import test of the built package without the `themes` extra.

Findings marked **[verified]** were reproduced or read directly during this review.

---

## 1. Headline

The ten-phase plan did what it claimed. The framework is in a different class from the 2026-09-08 snapshot:

- 945 tests pass headless in ~17 s (was 258 in ~3 s). **[verified]**
- mypy is clean over 62 source files; pylint scores 10.00/10. **[verified]**
- `import opaque` succeeds without any theme package installed; `__version__` is `1.0.2`; `__all__` exports 18 names; `py.typed` ships. **[verified]**
- All seven P0 release blockers are closed in source. Eight of eleven P1 defects are fully closed. The large P2 moves (`FeatureContext`, typed `ServiceLocator`, declarative `register()`, the `shell.py` move, the threading guard) are real and guarded by tests.

What remains is small and specific. Section 2 lists the code defects that are still open. Section 3 lists two closure-table claims in the old review that do not hold in source. Section 4 covers the examples. Section 5 covers documentation drift. Section 6 ranks the work.

---

## 2. Open code defects **[verified]**

These survive from the old review or are new observations. Each is small.

### 2.1 Settings dialog residuals (old item 3.6, marked closed with four commits)
The main corruptions are fixed: `FloatField` renders a `QDoubleSpinBox`, and `Field.coerce()`/`display()` stop the string-overwrite on the line-edit path. Three parts are still open:

- **Spinbox clamp at 99.** `settings.py:429-439` sets minimum/maximum only when `field.min_value`/`max_value` are not `None`. An `IntField` without `max_value` gets Qt's default range 0–99; a stored 5000 silently becomes 99, a negative value becomes 0.
- **`validator=` never runs.** `Field.validator` is consulted only by `Field.validate()` (`annotations.py:72`), which only `AbstractModel.validate()` calls — and nothing in `src/` calls that. The generated setter checks only `choices`/`min_value`/`max_value` (`abstract_model.py:74-83`).
- **Four `UIType` members have no widget branch.** `TEXTAREA`, `SLIDER`, `LIST_VIEW`, `FILE_SELECTOR` (`annotations.py:23-26`) all fall to the `QLineEdit` catch-all (`settings.py:473-480`). Coercion now protects the type, but the declared UI does not exist. Either build the four widgets or delete the enum members.

### 2.2 Two widgets keep stale colours after a theme change (old item 3.10 residual)
The repaint contract is: cache a token, declare `apply_theme()`, and the shell walk calls it. Exactly one widget implements it (`console_widget.py:111`). Two widgets cache tokens into f-string stylesheets at construction and declare no `apply_theme()`:

- `view/widgets/busy.py:31-32,41` — `BusyOverlay` bakes `surface_variant()` and `on_surface()` into its stylesheet in `__init__`.
- `view/widgets/notification_widget.py:255-256,269-278` — `NotificationListItem` caches `status_colors(...)` and `muted_on_surface()` at construction.

The shell's `unpolish`/`polish` pass does not re-evaluate an f-string stylesheet. Both keep old colours across a theme change.

### 2.3 `cleanup()` warns 14 times per test run (new)
`BasePresenter.cleanup()` (`presenters/presenter.py:237-242`) disconnects the view signals inside `try/except RuntimeError`. When a presenter is cleaned twice — once when its view closes, once at shell `closeEvent` — the second disconnect fails. The `except` catches the exception, but libpyside also emits a `RuntimeWarning` the catch cannot silence. The full suite prints 14 of them (visible under `tests/test_shutdown_order.py` and `tests/view/test_version_dialogs.py`). Fix: guard with the `_closed` flag (it already exists at `presenter.py:64`) or track connection state, instead of catching after the fact.

### 2.4 Example log directories are untracked and unignored (new)
`examples/console_example/logs/` (15 session folders) and `examples/notification_example/logs/application.log` sit on disk from before `LoggerService` moved to `AppDataLocation`. They are not tracked, but `.gitignore` has no rule for them, so `git status` shows them on any machine that ran the old code. Add an ignore rule and delete the leftovers. (Repo-root leftovers `asdasd.wks` and `logs/` are already covered by `.gitignore`; delete them locally when convenient.)

---

## 3. Closure-table corrections

Two rows in `docs/ENGINEERING_REVIEW.md` §9 claim closure that the source does not show:

### 3.1 `self_check.py` is still unwired
The table says the a11y runtime check was wired by Task 4 (`4dbbd3b`). In source, `view/self_check.py` still has zero production callers: no invocation anywhere in `src/` or `examples/`, no export from `opaque/__init__.py` or `opaque/view/__init__.py`. Its docstring says "call it in a debug build"; nothing does. Only tests consume it. (The related hit-target consolidation *was* done: `MINIMUM_HIT_TARGET` lives in `view/theme/tokens.py:39`.) Decision still pending: wire it to a debug flag or delete it.

### 3.2 Item 4.1 is half closed: the `create_services` seam does not exist
The typed half is done and good: `ServiceLocator.get(SettingsService)` returns the right type and raises `LookupError` naming the missing service (`services/service.py:101-138`). The replacement half is not done. There is no `create_services` (or equivalent) hook anywhere in `src/`; `BaseApplication.__init__` still constructs nine concrete services inline and pins them as attributes (`shell.py:117,145,150,157,162,168,177`). A subclass cannot replace a built-in service, because re-registration would not update the shell's own attribute references — the exact failure mode 4.1 described. Either build the seam or record the restriction as a decision, like D6 did for signal hygiene.

### 3.3 `FeatureContext` is wider than its own docstring
The context claims to offer "configuration, `service()`, `show_window()` and nothing else" (`features/context.py:33-35`, repeated in `CLAUDE.md` and `QUICK_REFERENCE.md`). It actually has six members, including `shell` — a typed reference to the whole main window. One example already uses the escape hatch: `examples/basic_example/features/notification_tester/presenter.py:151` reaches `context.shell.notification_presenter`. This is not a defect by itself, but the docstring and the docs must state the truth, and the `shell` accessor deserves a written rule about when it is acceptable.

---

## 4. Examples audit

Six example applications exist, not two: `quickstart`, `basic_example`, `closeable_tab_example`, `console_example`, `my_example`, `notification_example`. Only the first two appear in any document, and only those two are exercised by tests. Every import in all six resolves, and the service names match their lookups. **[verified]** The problems are rule violations — and they matter double, because examples are what users and AI agents copy:

### 4.1 Violations of documented framework rules
- **`setup_ui()` skipped in 3 of 8 views.** `examples/quickstart/main.py:60-66` — the canonical first example — builds its UI in `__init__`, as do `my_example/features/todo_list/view.py:26-45` and `closeable_tab_example/main.py:156-177`. The docs name `setup_ui()` as the method to write; `basic_example` gets it right in all five views. The quickstart is byte-locked into the README by `tests/test_quickstart.py`, so fixing it changes both in one commit.
- **`on_view_close()` calls `cleanup()`.** `examples/my_example/features/todo_list/presenter.py:41-42` does exactly what CLAUDE.md, the README, and the quickstart docstring all forbid. `_handle_view_closed()` calls `cleanup()` itself right after the hook, so this double-cleans.
- **Literal colours and font sizes.** `basic_example/features/calculator/view.py:92-98` (`#4CAF50`, `color: white`), `calculator/model.py:43`, `notification_tester/view.py:35` (`font-size: 16px`), `tab_manager/view.py:117` and `closeable_tab_example/main.py:163` (`color: gray`), `notification_example/main.py:70,105`. The theme rule says a widget must never write a literal colour or point size.
- **`self.tr()` is essentially absent.** Across all six examples there are two `.tr(` calls total. Every user-visible string in the example views is a bare literal. The enforced rule differs from the stated rule: `tests/test_localisation.py:24` scans `src/opaque` only.

### 4.2 Decision needed
Either bring all six examples up to the documented rules and put them under the guards (extend the localisation scan and a colour-literal scan to `examples/`), or delete the four unmentioned ones (`closeable_tab_example`, `console_example` is referenced by code only, `my_example`, `notification_example`) and keep the two that tests already pin. Shipping examples that break the framework's own stated rules is the worst option — an agent cannot tell the rule from the exception.

---

## 5. Documentation drift **[verified]**

The import-level guard (`tests/test_documentation.py`) works: every `opaque` import in every Markdown file resolves. But it checks imports only, not prose, and the prose has drifted:

| Location | Problem |
|---|---|
| `docs/QUICK_REFERENCE.md:105` | Says `VersionManager` is "not registered by the framework". False: `shell.py:117-119` registers it. `CLAUDE.md` has it right; the two documents contradict each other. |
| `docs/QUICK_REFERENCE.md:20` | Lists `on_view_close()` under "You must write". It is optional — no `@abstractmethod` (`presenter.py:185`). |
| `docs/QUICK_REFERENCE.md:3` | "Every name on this page is checked by tests" — overclaim. The service table, method names, and field-argument table are unchecked prose. Line 105 went stale exactly this way. |
| `docs/QUICK_REFERENCE.md:24` | "configuration, `service()`, `show_window()` and nothing else" — the context has six members; line 81 itself uses `optional_service()`. |
| `CLAUDE.md:46` | "`palettes.py` is the only module holding a hex colour." False: `tokens.py:153-166` holds 30 hex literals (the `StatusColors` tables) and `contrast.py:27-28` holds two. Restate the rule as "widgets never hold a hex colour; the theme package owns them". |
| `CLAUDE.md:15` | "full suite … ~3 s" — actual is 945 tests in ~17 s. |
| `CLAUDE.md:48` | Says the localisation test "scans the source"; the scan root is `src/opaque` only, examples excluded. |
| `README.md:174` | Points at `ENGINEERING_REVIEW.md` as "the current known-defect list". It is a closed historical snapshot; point here instead. |
| `README.md` | Never states the Python floor (`>=3.11` per `pyproject.toml:10`). |
| `tests/test_documentation.py:32,35` | Comment says "six files" in `SKIPPED_FILES`; there are seven. |
| `view/dialogs/keyboard_map.py:12-13` | Module docstring says the list reads "off the live QAction objects"; the code also walks `QShortcut` (`keyboard_map.py:63`). The function docstring is correct. |

Everything else checked clean: all eight `SERVICE_NAME` values, every cited path and test in `CLAUDE.md`, the README quickstart byte-identity, the install command and extras, and the three docstrings the old review called false (`BaseApplication`, `register_feature`, `ApplicationView` — the last fixed by deletion).

---

## 6. Recommended sequence

1. **Small code fixes, one commit each, with a regression test.** The spinbox default range (2.1), the two stale-theme widgets (2.2), the double-disconnect warning (2.3), the example `on_view_close` double-clean (4.1). Each is under an hour.
2. **Two decisions, then act.** `validator=`: run it in the generated setter or remove the parameter (2.1). Four dead `UIType` members: build or delete (2.1). `self_check.py`: wire or delete (3.1). Examples: fix-and-guard or prune (4.2).
3. **One docs pass.** Every row in section 5, in one commit. Add the corrections from section 3 (`self_check`, 4.1) to the old review's closure table so it stops overstating, or mark that document as a frozen snapshot at the top.
4. **Optional structural item.** The `create_services` seam (3.2), only if replaceable services are a real requirement; otherwise write the decision down as D-series and close it.

Nothing here blocks a release. Items 1–3 are a day or two of work in total.

### Decisions taken (2026-09-09), executed by `docs/superpowers/plans/2026-09-09-review-followup-fixes.md`

- `validator=` (2.1): runs in the generated setter.
- Four dead `UIType` members (2.1): all four built — `TEXTAREA`, `SLIDER`, `LIST_VIEW`, `FILE_SELECTOR` each draw a real widget.
- `self_check.py` (3.1): wired to the `OPAQUE_SELF_CHECK` environment variable; the shell runs it once, at first show.
- Examples (4.2): fixed and guarded, not pruned. `examples/my_example` was deleted (it duplicated `basic_example` and carried the double-cleanup defect); the other four were brought up to the theme, i18n and lifecycle rules and are covered by `tests/test_example_hygiene.py`.
- `create_services` seam (3.2): accepted as not built — see the "Items accepted rather than fixed" table in `docs/ENGINEERING_REVIEW.md` §9.
