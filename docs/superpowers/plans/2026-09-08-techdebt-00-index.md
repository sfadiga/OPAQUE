# OPAQUE Technical Debt Remediation — Plan Index

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement each plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every finding in `docs/ENGINEERING_REVIEW.md` (2026-09-08), in an order where each plan ships working, tested software on its own.

**Architecture:** The review found four layers of debt. The bottom layer is the toolchain: the package cannot be installed, imported, or type-checked, and no CI ever proved otherwise. Plan 01 repairs that, so every later plan has a feedback loop. The middle layer is a set of small verified defects with one root cause each (Plans 03 to 06). The top layer is two structural moves that change public signatures (Plans 07 and 08); they come last of the code work because they touch every call site. Plan 09 and Plan 10 clean the packaging tools and the polish list.

**Tech Stack:** Python 3.11 (floor), PySide6, pytest, pytest-qt, mypy, pylint, uv, PyInstaller, Nuitka, GitHub Actions.

---

## Decisions of record

These come from Section 7 of the review. Every plan below obeys them. Do not re-open them while executing.

| # | Question | Decision |
|---|---|---|
| D1 | Distribution intent | PyPI publication is real and near-term. Packaging quality is a first-class requirement, not a nicety. |
| D2 | Project tooling | `uv` is the project manager. `uv sync`, `uv run`, `uv lock`, committed `uv.lock`. |
| D3 | Python floor | **3.11**. `requires-python = ">=3.11"`. Classifiers list 3.11, 3.12, 3.13 only. |
| D4 | Theme scope | One consistent built-in theme set (`Default`, `Light`, `Dark`) driven by `QPalette`, which is the single source of truth the token layer already reads. Third-party vendors (qt-themes, qt-material, QDarkStyle) become **optional plug-in providers**, not hard dependencies. |
| D5 | Feature identity | One explicit, stable `FEATURE_ID` string declared on the model. It is the key for the feature registry, the settings file, and the workspace file. `feature_name()` becomes display-only. |
| D6 | Dynamic features | Features never load or unload at run time. This is documented, and the signal-hygiene debt (review 4.7) is accepted with a written note instead of a `disconnect` discipline. |
| D7 | Dead settings | Implement, do not delete. The notification settings model gets registered, `settings_changed` reaches the presenters that care, and the language setting really changes the language (at the next start, with an explicit message). |
| D8 | Service access | Keep the locator, make it typed: `ServiceLocator.get(SettingsService)` raises on a miss, `get_optional(...)` for the soft case. String names survive only as constants in one module. |
| D9 | `build_tools` ownership | Keep it, slimmed. One `BuildConfig`, two backends the user selects (`--backend pyinstaller` or `--backend nuitka`), no third-party import at module scope, and documentation generated from the real signatures. A framework for engineering applications that cannot ship an executable is not finished. |

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
8. Every new string the user can see must be inside `self.tr("...")` with a **literal** argument. Never write `self.tr(f"...")`. Never write `self.tr(some_variable)`. `lupdate` cannot read those. `tests/test_localisation.py` fails the build if you do.
9. Never write a colour, a font family, or a font size as a literal value in a widget. Import them from `opaque.view.theme`.
10. Run every command from the repository root, `C:\Users\sfadiga\sandro\opaque`.
11. **Interpreter:** until Plan 01 Task 6 is merged, the interpreter is `venv\Scripts\python.exe`. From Plan 01 Task 6 on, it is `uv run python`. Each task states the exact command; use what the task states.
12. Identifiers use American spelling (`color`). Do not change British spelling in prose or comments of code you are not otherwise editing.

---

## Plan order

| # | Plan | Review items closed | Depends on |
|---|---|---|---|
| 01 | [Toolchain, packaging, public API, CI](2026-09-08-techdebt-01-toolchain-and-packaging.md) | 2.4, 2.6, 2.7, 5.3, 5.6, D2, D3 | — |
| 02 | [Documentation and example truth](2026-09-08-techdebt-02-docs-and-examples-truth.md) | 2.2, 2.3, 2.5, 5.1, 5.2, 5.4, 5.5 | 01 |
| 03 | [Theming with one source of truth](2026-09-08-techdebt-03-theming-single-source.md) | 2.1, 3.10, D4 | 01 |
| 04 | [Model and presenter contract](2026-09-08-techdebt-04-model-contract.md) | 3.4, 3.5, 4.5, part of 3.11 | 01 |
| 05 | [Settings subsystem](2026-09-08-techdebt-05-settings-subsystem.md) | 3.6, 3.7, 3.8, D7 | 03, 04 |
| 06 | [Shell lifecycle and feature identity](2026-09-08-techdebt-06-shell-lifecycle-and-identity.md) | 3.1, 3.2, 3.3, 3.9, rest of 3.11, D5, D6 | 04, 05 |
| 07 | [Typed service access and the service seam](2026-09-08-techdebt-07-typed-services.md) | 4.1, D8 | 06 |
| 08 | [FeatureContext and declarative registration](2026-09-08-techdebt-08-feature-context.md) | 4.2, 4.3, 4.4 | 07 |
| 09 | [Build backends](2026-09-08-techdebt-09-build-backends.md) | rest of 2.3, D9 | 01, and 08 for Task 5 |
| 10 | [Consistency and polish](2026-09-08-techdebt-10-polish.md) | 4.6, 4.7, all of Section 6 | 08 |

Plans 02, 03, 04, and 09 do not depend on each other. Run them in parallel if you have more than one worker. Plans 05 to 08 are a chain: each one changes signatures the next one calls.

Do not trust a test count from another plan. After every task, the whole suite must pass with zero failures.

---

## Coverage map

Every numbered item of the review appears here exactly once as an owner.

### P0 — release blockers

| Item | Finding | Owner |
|---|---|---|
| 2.1 | Theme packages imported at module scope, declared optional | 03 Task 1, Task 5 |
| 2.2 | README quick start raises `TypeError` | 02 Task 1 |
| 2.3 | `API.md` and `QUICK_REFERENCE.md` document classes that do not exist | 02 Task 2, Task 3; template in 09 Task 5 |
| 2.4 | `pyinstaller_builder.py:268` f-string kills the package on 3.11 | 01 Task 2 |
| 2.5 | Example services import `opaque.core.services` | 02 Task 4 |
| 2.6 | Empty public API, no `__version__`, no `py.typed` | 01 Task 3 |
| 2.7 | Placeholder URLs, stray root files, no CI, `cicd.sh` lies | 01 Task 1, Task 5, Task 6, Task 7 |

### P1 — verified defects

| Item | Finding | Owner |
|---|---|---|
| 3.1 | `"theme"` looked up, `"themes"` registered | 06 Task 1 |
| 3.2 | `WorkspaceService.cleanup()` calls `initialize()` | 06 Task 2 |
| 3.3 | Services die before presenters clean up | 06 Task 3 |
| 3.4 | Observers shared across model instances | 04 Task 1 |
| 3.5 | Every field write notifies twice | 04 Task 2 |
| 3.6 | Settings dialog corrupts typed values | 05 Task 1, Task 2, Task 3 |
| 3.7 | Settings persistence loses data silently | 05 Task 4, Task 5 |
| 3.8 | Dead configuration surface | 05 Task 6 to Task 11 |
| 3.9 | Three identity schemes for one feature | 06 Task 4, Task 5 |
| 3.10 | Theme system has two sources of truth | 03 Task 1 to Task 5 |
| 3.11 | Eleven smaller confirmed defects | see below |

`3.11` breakdown:

| Sub-item | Owner |
|---|---|
| `ApplicationView.__init__(feature_id: str)` false annotation | 10 Task 1 |
| False `BaseApplication` and `register_feature` docstrings | 02 Task 5 |
| `on_view_close` abstract with a body and a spurious WARNING | 04 Task 3 |
| `BaseModel.feature_*` raise at call time | 04 Task 4 |
| `bind_events()` timing trap | 04 Task 5 |
| `app.main_window = self` dead monkey patch | 06 Task 6 |
| Keyboard map cannot see `QShortcut` objects | 06 Task 7 |
| `self_check.py` has no production caller | already fixed by commit 570d5ac, which wired it to a debug build. 10 Task 4 makes it read the shared hit-target token, so the check and the widgets can no longer disagree. |
| `OpaqueMdiArea` shadows `subWindowActivated` | 06 Task 8 |
| `logger_service.py` reports failures with `print()` | 10 Task 6. Commit a7f57c2 fixed `console_model.py`, `settings_service.py` and `single_instance_service.py` only. Five `print()` calls are still there: `logger_service.py:135, 155, 227` and `console_service.py:188, 193`. |
| Services log through the stdlib root logger | 06 Task 9 |

### P2 — architecture

| Item | Finding | Owner |
|---|---|---|
| 4.1 | Shallow service seam, stringly typed | 07 all tasks |
| 4.2 | Everything holds the whole application | 08 Task 1 to Task 3 |
| 4.3 | Feature assembly is manual and order-fragile | 08 Task 4, Task 5 |
| 4.4 | Layering does not match the package names | 08 Task 6 (Task 7 writes it down) |
| 4.5 | Threading contract is implicit | 04 Task 6 |
| 4.6 | Shallow modules | 10 Task 1, Task 2, Task 3 |
| 4.7 | Signal hygiene | 06 Task 10 (documented per D6) |

### AI-agent readiness and polish

| Item | Finding | Owner |
|---|---|---|
| 5.1 | Fix the lies first | 02 all tasks |
| 5.2 | `CLAUDE.md` at the repo root | exists; 02 Task 6 keeps it true |
| 5.3 | Export the public API, ship `py.typed` | 01 Task 3 |
| 5.4 | Make errors teach | 02 Task 5, 06 Task 4, 08 Task 5 |
| 5.5 | Track the plans | 01 Task 7 |
| 5.6 | Add CI | 01 Task 6 |
| 6 | Spelling, naming, hit-target token, typos, unused imports, duplicated widgets, settings I/O churn | 10 Task 4 to Task 8 |
| — | Working-directory writes: the single instance lock and the log folder are relative paths (noted in passing by the review, not numbered) | 06 Task 11 |
| — | `SingleInstanceService` detects a second instance by binding TCP port 49152. Two jobs on one CI runner, or a developer with the example already open, collide on that port. Found while reviewing 01 Task 4, which builds the example and therefore starts the service. Pre-existing, and not a defect of that task. | 06 Task 11 already moves the lock file to a per-user location; give it the port too. Take a free port, or key the lock on a per-user path instead of a fixed port. |
| — | Measured on 2026-09-08, after 01 Task 2 unblocked the tools: `mypy src/opaque` reports **111 errors in 26 files** (55 files checked) on the old `venv` and **112** under `uv run`, because the newer PySide6 stubs add one. `pylint src/opaque` reports **187 messages**, rated 9.34/10, in both. Both tools exit non-zero, which is why 01 Task 7 makes CI report without gating. The largest groups are 25 `invalid-name`, 22 `missing-function-docstring`, 21 `trailing-whitespace`, 19 `attribute-defined-outside-init`, 12 `unused-import`, 9 `line-too-long`, 8 `import-outside-toplevel` and 8 `broad-exception-caught`. 10 Task 8 asks for both to be clean and to drop `continue-on-error` from CI. That is a much larger task than the plan text implies, and `attribute-defined-outside-init` in particular is a real design smell, not a formatting nit. | 10 Task 8. Split it before starting: the mechanical groups (whitespace, unused imports, docstrings, line length) are one commit each; `invalid-name` and `attribute-defined-outside-init` need judgement and may need their own tasks. Until then CI reports without gating, per 01 Task 7 Step 2. |
| — | `tests/test_imports.py` guards discovery with `assert len(MODULES) >= 50`, and the real count is 52. Plan 10 Task 1 deletes `app_view.py` and `layouts/flow.py`, which takes it to 50, and Plan 08 adds `features/context.py` and renames `view/application.py` to `shell.py`, which is one more module. The floor is a secondary guard: `test_the_walk_reaches_the_namespace_packages` is the one that catches a whole layer going missing. | 08 Task 6 and 10 Task 1 must move the floor in the same commit that changes the module count, and must not delete the guard. Raise it to the new real count minus two. |
| — | `.gitignore` held two rules that predated uv and each hid a file decision D2 requires committed. `.python-version` was ignored under a `# pyenv` heading, for a layout this project never used. `*.lock`, written for the application's own single instance lock, also matches `uv.lock`. In both cases `git add` succeeds silently and adds nothing, so the file simply never reaches the repository. Found by 01 Task 6, one at a time, because each only appears when you try to stage that file. | Fixed in 01 Task 6: the pyenv rule is gone and `!uv.lock` follows the glob. When 06 Task 11 moves the runtime lock to a per-user location, the `*.lock` glob and its exception can both be deleted. |
| — | **The review missed this one too.** `BaseApplication` gave the Settings and Exit menu items `QKeySequence.StandardKey.Preferences` and `.Quit`. Qt has no standard shortcut for either on Windows. Up to Qt 6.10 it answered with the multimedia key names `Settings` and `Exit`, which no ordinary keyboard has, and from 6.11 with an empty sequence. So those two items never had a usable shortcut. `test_the_file_menu_actions_have_shortcuts` only asserted the string was non-empty, and `"Settings"` is non-empty, so it passed while the defect was live. Found by 01 Task 6, when `uv` resolved PySide6 6.11.2 and the test finally failed. An accessibility gap in a project that has explicit accessibility work. | Fixed in 01 Task 6: both actions carry an explicit shortcut through `self.tr()`, and the test now also rejects a shortcut with no modifier. |
| — | **P0, and the review missed it.** `pyproject.toml` pinned the `themes` extra at `qt-themes>=1.0.0`. That version has never been published: PyPI has 0.1.0 to 0.4.0. `pip install opaque-framework[themes]` therefore fails on every Python version, and `uv sync` refuses to resolve at all. Found by 01 Task 6, which could not create an environment until it was fixed. Decision D1 makes this a release blocker. `qt-material>=2.14` and `QDarkStyle>=3.2.0` were checked and both resolve. | Fixed in 01 Task 6: the floor is now 0.4.0, and `uv.lock` plus CI `uv sync` keep resolution honest from here. Plan 03 moves `qt-material` and `QDarkStyle` into this same extra, so it must re-check every floor it touches. |
| — | The generated PyInstaller spec interpolates paths into single quoted Python literals with a bare placeholder, so a Windows backslash becomes an escape sequence when PyInstaller executes the spec. `C:\new\app.py` is read back as `'C:\new\x07pp.py'`. `C:\venv\...` and `C:\temp\...` break the same way. Older than this programme: the same pattern is at `pyinstaller_builder.py:212` in the parent commit of 01 Task 2. Not a regression from 01 Task 2, which only removed the nested f-string. Found while reviewing that task. | 09, binding rule 6. Task 2 and Task 3 each carry a test that asserts on the parsed literal. |
| — | `models`, `presenters` and `services` have no `__init__.py`, so they are implicit namespace packages. Found while executing 01 Task 2: a `pkgutil.walk_packages` walk sees 30 of the 52 modules, and every module it misses is in one of those three layers. Verified as latent, not live: no `walk_packages`, `iter_modules` or `collect_submodules` call exists anywhere in `src/` or `examples/`, and the wheel ships all 55 modules, because `[tool.setuptools.packages.find]` includes namespace packages by default. The risk is a future generated PyInstaller spec that calls `collect_submodules("opaque")` and silently drops the model, presenter and service layers. | No task owns it. Decide in 09 Task 1, which is where a generated spec would first depend on discovery. 01 Task 2 already stopped the test suite from depending on it. |
