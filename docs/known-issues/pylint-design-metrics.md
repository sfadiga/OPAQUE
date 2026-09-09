# Known issue: nine pylint design-metric checks are disabled, not fixed

**Status:** Open. Disabled project-wide in `pyproject.toml`
(`[tool.pylint."MESSAGES CONTROL"]`) on 2026-09-09, during Plan 10 Task 8.

**Severity:** Low. Nothing here is a defect; each check is a size or
complexity threshold that a real class or method crosses. The code behind
every one of them is covered by tests and was left exactly as Plan 10 found
it.

## Why these are disabled instead of fixed

Plan 10 Task 8's instructions allowed exactly two named exceptions
(`too-few-public-methods` on a dataclass, and `broad-except` where the
framework deliberately catches everything to keep the interface alive).
Working through the rest of the pylint list surfaced two more categories the
plan did not anticipate:

- Fixing these for real means splitting classes and methods apart -
  `console_widget.py`'s widget has 28 instance attributes, `shell.py`'s
  `BaseApplication.__init__` has 19 and 51 statements, `settings.py`'s form
  builder has 57 statements, 18 branches and 16 locals. That is a structural
  refactor with real behaviour risk, not a lint fix, and it was explicitly
  out of scope for a plan whose own architecture notes say "nothing here
  changes behaviour a user can see."
- `attribute-defined-outside-init` fires on every widget that builds its
  attributes in a `setup_ui()`/`_setup_ui()` helper called from `__init__`,
  which is this framework's own documented, blessed pattern
  (`BaseView.setup_ui()`, see CLAUDE.md). "Fixing" it would mean
  pre-declaring every widget attribute as `Optional[...] = None` before the
  setup call, which would then need an `isinstance`/`is not None` check at
  every later use to keep mypy clean - undoing real, verified mypy
  cleanliness (also finished in this task) to satisfy a check that is
  flagging the framework's own architecture.

## The checks and where they fire

| Check | What it flags | Worst offenders |
|---|---|---|
| `too-many-instance-attributes` (R0902) | A class with more than 7 instance attributes | `console_widget.py` (28), `shell.py`'s `BaseApplication` (19), `build_tools/config.py`'s `BuildConfig` (17) |
| `too-few-public-methods` (R0903) | A class with fewer than 2 public methods | Qt widgets and `Protocol` classes whose real interface is inherited or structural, not counted by this check |
| `too-many-branches` (R0912) | A method with more than 12 branches | `nuitka_builder.py` (24, 22), `pyinstaller_builder.py` (14), `closeable_tab_widget.py` (14) |
| `too-many-locals` (R0914) | A method with more than 15 local variables | `pyinstaller_builder.py` (22, 18), `settings.py` (16), `version_info.py` (18) |
| `too-many-statements` (R0915) | A method with more than 50 statements | `settings.py`'s form builder (57), `version_info.py`'s system tab builder (58), `shell.py.__init__` (51), `console_widget.py` (51) |
| `too-many-arguments` / `too-many-positional-arguments` (R0913/R0917) | A function signature with more than 5 parameters | `closeable_tab_widget.py.__init__` (6), `mdi_window.py`'s `OpaqueMdiSubWindow.__init__` (6) |
| `duplicate-code` (R0801) | Near-identical code blocks across files | `nuitka_builder.py` and `pyinstaller_builder.py` share several boilerplate patterns (finding the built executable, the try/except around a build, computing an output name) |
| `attribute-defined-outside-init` (W0201) | An attribute first assigned outside `__init__` | Every widget that builds its UI in a `setup_ui()`/`_setup_ui()` helper - by design, per CLAUDE.md |

## What real fixes would look like

- **R0902/R0912/R0914/R0915 on the big widgets and dialogs** (`console_widget.py`,
  `shell.py`, `settings.py`, `version_info.py`): split each oversized method
  into smaller ones (a real, incremental refactor with no behaviour
  change), and consider whether some instance attributes belong on a small
  owned helper object instead of directly on the widget.
- **R0913/R0917** on the two constructors: group related parameters into one
  small config object, the same shape `BuildConfig` already uses for the two
  build backends.
- **R0801** between the two build backends: extract the shared helpers
  (`_find_executable`'s onefile/directory split, the try/except/logging
  wrapper around a build) into `builder.py`, the base class both already
  inherit from.
- **W0201**: not worth fixing as stated. If this check keeps coming up,
  the better fix is a pylint plugin or a narrower per-class disable that
  recognizes `setup_ui()`/`_setup_ui()` as an extension of `__init__`,
  not touching the framework's documented widget-building pattern.

## Where this was found

Plan 10 Task 8 (`docs/superpowers/plans/2026-09-08-techdebt-10-polish.md`),
while making `pylint src/opaque` pass cleanly enough to remove CI's
`continue-on-error: true`. The user chose, mid-task, to document these as
deferred exceptions rather than refactor now, given the real behaviour risk
and scope of the alternative.
