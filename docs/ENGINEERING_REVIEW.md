# OPAQUE Framework — Engineering Review

Date: 2026-09-08.
Scope: the full framework (`src/opaque`, ~10,800 lines), the examples, the tests, the documentation, and the packaging.
Method: four parallel code explorations, direct verification of each load-bearing claim, a full test run, mypy, and pylint.
Focus: gaps that stop a user — human or AI agent — from using the framework with success.

Findings marked **[verified]** were reproduced or read directly during this review. All other findings carry a file and line reference and were spot-checked.

---

## 1. What works well — keep it

- The test suite is real. 258 tests pass headless in ~3 s with `QT_QPA_PLATFORM=offscreen` and deterministic palette fixtures (`tests/conftest.py`). **[verified]**
- `examples/basic_example/main.py` is a correct, complete reference application.
- The theme token layer (`view/theme/contrast.py`, `tokens.py`, `type_scale.py`) is pure, tested, and documented with a clear rule: "a widget must never write a literal colour".
- `localisation.py` is the best-written module: honest docstrings, a stated policy, no silent failure.
- Newer modules explain *why* in comments, not *what*. Most public classes have docstrings.
- `.gitignore` is complete; no build artifacts are committed.
- `layouts/toast_stack.py` is a good example of a deep module: geometry extracted from the presenter so it can be tested headlessly.

The problem is not the recent UI work. The problem is the layer below it: the contract the framework offers to its users.

---

## 2. P0 — A new user cannot start (release blockers)

These items break the first hour of use. Fix them before anything else.

### 2.1 `pip install opaque-framework` yields an unimportable package **[verified]**
`theme_service.py:18-21` imports `qt_themes`, `qdarkstyle`, and `qt_material` at module scope. `pyproject.toml` declares `qt-themes` as an *optional* extra (`[project.optional-dependencies] themes`). `BaseApplication` imports the theme service, so a plain install cannot import the framework. The three `except ImportError: pass` blocks inside `theme_service.py` (for example line 91) are unreachable, because the import already failed at module load.
**Decision needed:** make all three theme packages hard dependencies, or make the imports lazy and degrade to the `Default` theme.

### 2.2 The README quick start does not run **[verified]**
`MyAppConfig()` from `README.md` raises:
`TypeError: Can't instantiate abstract class MyAppConfig with abstract methods get_application_description, get_application_icon, get_application_name, get_application_organization, get_application_title`.
The README shows field declarations (`app_name = StringField(...)`); the real contract demands five hand-written `get_*` accessors. The first thing every user (and every AI agent) copies is broken.

### 2.3 `docs/API.md` documents a framework that does not exist **[verified sample]**
Example: it documents `opaque.build_tools.cli.build_executable(...)`; no such function exists. It documents an `output_dir` parameter that `build()` does not take. `docs/QUICK_REFERENCE.md:88-91` imports `Application`, `AppModel`, `AppPresenter`, `AppView` — none exist (`BaseApplication`, `ApplicationModel`, ... do). The shipped project template `build_tools/templates/basic_app_template/main.py` uses the same wrong names.
For an AI agent, wrong documentation is worse than no documentation: the agent trusts it, writes broken code, and burns a debugging loop. Delete `API.md` or regenerate it from source. Fix or delete `QUICK_REFERENCE.md`. Fix the template.

### 2.4 `opaque-build` is dead on every Python below 3.12 **[verified]**
`build_tools/pyinstaller_builder.py:268` nests same-quote f-strings (PEP 701, Python 3.12+). On Python 3.11 the module raises `SyntaxError` at import, which kills `build_tools/__init__.py`, `cli.py`, and the `opaque-build` console script. It also stops mypy: the type checker aborts at this file, so the whole package is effectively unchecked. Meanwhile `pyproject.toml` claims `requires-python = ">=3.8"`.
**Decision needed:** pick a floor (recommendation: 3.10 or 3.11, matching current PySide6), fix the f-string, and align the classifiers.

### 2.5 The example services cannot import **[verified]**
All three files in `examples/basic_example/services/` import `from opaque.core.services import BaseService`. The package `opaque.core` does not exist. The same ghost package appears in `presenters/app_presenter.py:25` (a `TYPE_CHECKING` import) and in `pyproject.toml` (`"core/py.typed"`). Even with the import fixed, the example services register names (`"CalculationService"`) that do not match what the example presenters look up (`"calculation"`). The only worked example of "write your own service" fails at import.

### 2.6 The public API surface is empty **[verified]**
`src/opaque/__init__.py` is one comment line. There is no `__version__`, no re-export of `BaseApplication`, `BaseModel`, `BaseView`, `BasePresenter`, `Field` classes, or `ServiceLocator`. There is no `py.typed` file anywhere in `src`, although `pyproject.toml` claims to package one. Users must memorize deep module paths, and type checkers treat the package as untyped.

### 2.7 Packaging placeholders and hygiene
- All four `[project.urls]` entries point to `github.com/yourusername/...`.
- The version string lives in `pyproject.toml` only; `opaque.__version__` does not exist; `VersionManager` probes the filesystem for it at runtime.
- Bare `pytest` fails on a fresh clone (no `pythonpath = ["src"]` in the pytest config; it works here only because the venv has the package installed).
- `cicd.sh` references a `requirements.txt` that does not exist.
- There is no CI configuration at all. No CI is the root cause of 2.4 and 2.5: nothing ever imports these files in an automated run.
- Stray files in the repo root: `asdasd.wks`, `application_name.lock`, `logs/` output next to the source.

---

## 3. P1 — Verified defects inside the framework

### 3.1 The string-keyed service locator already caused a silent bug **[verified]**
`ThemeService` registers as `"themes"` (`theme_service.py:43`). `console_presenter.py:101` looks up `"theme"`, gets `None`, and the `if theme_service is not None` guard skips the connection. Result: the console never repaints on a theme change. No error, no log. `docs/QUICK_REFERENCE.md:210` documents the wrong name too. This is the predictable cost of `get_service(name: str) -> Optional[BaseService]`: every typo compiles, and every miss is silent.

### 3.2 `WorkspaceService.cleanup()` calls `initialize()` **[verified]**
`workspace_service.py:88-90`: `cleanup()` calls `super().initialize()`. A cleaned-up service reports `is_initialized == True`. Copy-paste error.

### 3.3 Teardown order is inverted **[verified]**
`application.py:407-416`: `closeEvent` cleans all services first, then calls `presenter.cleanup()` for each feature. A presenter that touches a service during teardown talks to a dead object. `console_presenter` does exactly that (`stop_capture()`).

### 3.4 Observers are shared across model instances **[verified]**
`Field._observers` lives on the `Field` object (`annotations.py:60`). The `Field` object is a class attribute. So all instances of one model class share one observer list. Presenter A of instance 1 receives updates for instance 2. `AbstractModel.cleanup()` then clears `field._observers` for *every* instance (`abstract_model.py:219-220`). Any application with two windows of the same feature class hits this.

### 3.5 Every field write notifies the presenter twice
The generated setter calls `field.notify(...)` and then `mark_dirty()`, which calls `notify("dirty", True)` (`abstract_model.py:56-57`, `145-146`). A presenter that dispatches on `field_name` receives a surprise `"dirty"` callback per write. `load_workspace` adds a third, manual `self.update(...)` call (`presenter.py:176-178`). The `update()` docstring mentions none of this.

### 3.6 The settings dialog corrupts typed values
- `FloatField` sets `ui_type=UIType.SPINBOX` (`annotations.py:123`); the dialog renders `QSpinBox` and does `int(current_value)` (`settings.py:345-351`). Floats are truncated. **[verified]**
- Four of the eleven declared `UIType` members (`TEXTAREA`, `SLIDER`, `LIST_VIEW`, `FILE_SELECTOR`) fall to the `QLineEdit` catch-all and write a *string* back over the field (`settings.py:382-387`). A `ListField` has no `ui_type` and always takes this path.
- A spinbox field without `max_value` clamps silently at Qt's default of 99.
- The `validator=` callable passed to a `Field` never runs on assignment; the generated setter checks only `choices`, `min_value`, `max_value` (`abstract_model.py:40-49`). Nothing calls `model.validate()`.
- "Restore Defaults" queues defaults but redraws from the old model values (`settings.py:172-187`); the screen does not change.

### 3.7 Settings persistence loses data silently
- A corrupt `settings.json` is logged, replaced by `{}`, and overwritten on the next save. No backup, no user message (`settings_service.py:130-146`).
- Writes are not atomic (plain truncate-and-write). A crash mid-write creates the corrupt case above.
- There is no schema version and no migration hook. A renamed field is dropped; a removed field lingers forever.
- `export_settings`/`import_settings` open files without `encoding=`; on Windows the round-trip can mangle non-ASCII.
- The settings dialog reports "Settings applied." whether or not the save succeeded.

### 3.8 Dead configuration surface — settings that do nothing
- `NotificationSettingsModel` (193 lines, ~20 fields) is constructed but never registered; the registration line is commented out (`notification_presenter.py:85`). Every notification setting is inert.
- `ApplicationModel.language` is a persisted setting with choices `["en", "es", "fr"]`; nothing reads it. The translator always uses `QLocale.system()`. A user changes the language and nothing happens, now or after restart.
- `get_application_min_size`/`get_application_max_size` return `None` with the real code commented out (`configuration.py:133,139`); the four min/max fields are dead.
- No `.qm`/`.ts` translation files ship, so the whole i18n path has never run against a real translation. `install_translator` also hardcodes the `opaque` prefix, so an application author *cannot* load their own translation through the public function.

### 3.9 Three identity schemes for one feature
- Registry key: `model.feature_name()` (`application.py:302-306`), except the built-in settings feature, which uses `feature_id` (`application.py:183`).
- Settings key: `presenter.feature_id` (defaults to the presenter class name).
- Workspace key: `presenter.__class__.__name__` (`presenter.py:158`).
Consequences: the duplicate check guards the wrong key; two presenters with the same class name silently share settings and overwrite each other's workspace; renaming a display string or a class silently orphans stored data.

### 3.10 Theme system has two sources of truth **[design defect]**
All tokens read `QApplication.palette()`. `ThemeService.apply_theme` updates the palette in only one of four paths (`qt-themes`); qt-material, QDarkStyle, and QLightStyle set a *stylesheet* and leave the palette stale (`theme_service.py:114-153`). With QDarkStyle active, `is_dark_theme()` returns `False` and the status colors pick the light set. Also, only two widgets subscribe to `theme_changed`; every other widget caches token values in its constructor and keeps stale colors after a theme change. There is no way to add a custom theme: `apply_theme` is a closed `if/elif` chain and the service class is hardcoded in the shell constructor.

### 3.11 Smaller confirmed defects
- `ApplicationView.__init__(self, feature_id: str)` — the parameter is actually the application object; the annotation is false (`app_view.py:21`).
- `BaseApplication`'s class docstring lists three methods that do not exist on the class; `register_feature`'s docstring describes lazy instantiation that does not happen and a parameter name that is wrong (`application.py:48-57`, `296-300`).
- `on_view_close` is `@abstractmethod` *with a body* that performs the real cleanup and logs a spurious `WARNING` on every close (`presenter.py:143-150`). A subclass that forgets `super()` silently never cleans up.
- `BaseModel.feature_name/icon/description` raise `NotImplementedError` at call time instead of being abstract; an incomplete model constructs cleanly and fails later, each method at a different point (`model.py:34-47`).
- `bind_events()` runs at the end of `BasePresenter.__init__`, before the subclass `__init__` body; attributes created after `super().__init__` do not exist yet in `bind_events`. Undocumented trap (`presenter.py:78`).
- `app.main_window = self  # type: ignore` (`application.py:70`) — a monkey-patched global that nothing reads. Dead.
- The keyboard map dialog cannot see `QShortcut` objects, so the console Find shortcuts never appear, although the docstring claims the map "can never disagree with the application".
- `self_check.py` (the a11y runtime check) has zero production callers. It is a good module in the wrong state: wire it to a debug flag or it is pure cost.
- `OpaqueMdiArea` re-declares `subWindowActivated`, shadowing Qt's built-in signal with one that never fires (`mdi_window.py:32`).
- `logger_service.py` reports its own failures with `print()`; if console capture is active, those prints can be dropped by the capture queue. The framework's error reporting can vanish into itself.
- Services log through the stdlib `logging` root, not through `LoggerService`, so their errors bypass the notification escalation path.

---

## 4. P2 — Architecture assessment

Vocabulary: a *module* is anything with an interface and an implementation. A module is *deep* when a small interface hides a lot of behavior. A *seam* is where an interface lives; one adapter per seam is a hypothetical seam, two adapters make it real.

### 4.1 The service locator is a shallow seam with zero real adapters
Every abstraction in the service layer has exactly one implementation, and every consumer names the concrete class. Lookups are stringly typed, return `Optional[BaseService]`, and force one of three downcast styles found in the code (lying annotations, `isinstance` guards, twelve local `typing.cast` calls in one file). A user cannot replace a built-in service: the shell constructs concrete classes inline and keeps direct attribute references, so re-registration would not even take effect.

**Direction:** keep the locator, but make it typed and make replacement a first-class seam.
- `ServiceLocator.get(SettingsService)` — lookup by type, return type follows the argument, raise on missing (with an explicit `get_optional` for the rare soft case).
- Name constants or an enum for any remaining string paths.
- A `BaseApplication.create_services(config) -> Services` factory method the subclass can override. That one hook makes every service replaceable and testable without monkey-patching.

### 4.2 Everything holds the whole application
Model, view, and presenter each store `BaseApplication`. The application is a `QMainWindow` that owns nine public service attributes, the MDI area, the toolbar, and the feature registry. That means: no layer boundary is enforced (the framework's own `ApplicationModel` reaches through the window into `_configuration`), every feature can reach every other feature, and nothing under a feature can be unit-tested without a window.

**Direction:** introduce a narrow `FeatureContext` interface (services accessor, notification API, logger, configuration — and nothing else). Pass the context, not the window. The window keeps the context as one attribute. This is the single highest-leverage refactor in the codebase: it restores locality (a feature's dependencies become visible in one small interface) and makes headless feature tests trivial.

### 4.3 Feature assembly is manual and order-fragile
A feature costs three classes, three constructor calls in a fixed order, and one `register_feature` call, with the application passed three times. Mistakes produce raw `AttributeError`s. The base classes do not document the wiring the presenter performs (signals it connects, methods it calls on the view).

**Direction:** one declarative entry point, for example:
`self.register_feature(Feature(model=CalculatorModel, view=CalculatorView, presenter=CalculatorPresenter))`
The framework constructs the triple in the right order, injects the context, and validates the contract (abstract methods, duplicate ids) with error messages that state the fix. This also gives AI agents one canonical pattern to imitate instead of five conventions to reverse-engineer.

### 4.4 The layering does not match the package names
`BaseApplication` — the service registry and feature registry — lives in `opaque/view/application.py`. The presenter package imports the view package through a `TYPE_CHECKING` workaround with a comment that documents the cycle. The packages are `models` (plural) and `view` (singular); the application shell files are `application.py`, `app_view.py`, `app_model.py`, `app_presenter.py` — two prefixes for one feature.

**Direction:** move the shell (application, service locator, feature registry) into `opaque/app/` or `opaque/core/` (the name half the code already believes exists). The view package should contain widgets only.

### 4.5 The threading contract is implicit and wrong-by-default
`model.field = x` synchronously calls presenter `update()`, which touches widgets. From a worker thread this is undefined behavior in Qt. There is no documentation, no assertion, no queued path. For an "engineering" framework whose users will run computations, this is the trap most likely to produce mystery crashes.

**Direction:** minimum — document the rule ("models must be written from the UI thread") and add a debug assertion in the generated setter. Better — route observer notification through a signal with `Qt.QueuedConnection` when the caller is not the UI thread. The console service's queue-and-drain pattern already shows the correct shape.

### 4.6 Shallow modules (deletion-test failures)
- `ApplicationView` (23 lines): pass-through with a false signature. Delete or fix.
- `BaseView` (38 lines): adds one attribute over `OpaqueMdiSubWindow` and forces the import-cycle dance. Either deepen it (give it the documented lifecycle hooks: `setup_ui()`, geometry contract) or collapse it.
- `view/layouts/flow.py`: zero production callers. Delete or use.
- Toolbar one-line wrappers (`add_separator`, three `connect_*` methods): pass-throughs.
- `version_info.py` reads the same nine stringly-typed dict keys in five places; there is no schema. A `VersionInfo` dataclass would concentrate that in one place.

### 4.7 Signal hygiene
No `disconnect` exists anywhere in `src/opaque/view/`. The toolbar has `add_feature` but no `remove_feature`; its lambdas capture buttons forever. `_wire_shell_signals` documents "every connection goes through a lambda on purpose" — and each lambda pins the main window. This is survivable today because features live as long as the application, but it hard-blocks any future dynamic feature unload, and it is the kind of invisible policy an AI agent will copy into user code.

---

## 5. AI-agent readiness

An AI agent learns a framework from four sources: package exports, docstrings, documentation, and examples. Current state per source:

| Source | State | Effect on an agent |
|---|---|---|
| Exports | `opaque/__init__.py` empty | Agent guesses deep paths; sometimes guesses `opaque.core.*`, which the codebase itself does in three places |
| Docstrings | Mostly present, several actively false (BaseApplication, register_feature, keyboard map) | Agent writes methods on the wrong class |
| Docs | README sample fails; QUICK_REFERENCE and API.md name fictional classes | Agent trusts and fails, then must re-derive the API from source |
| Examples | Main example correct; example services unimportable | Mixed signal: the one "write a service" model is broken |

Concrete actions, in value order:
1. **Fix the lies first.** False docs and false docstrings are negative-value for agents. Sections 2.2, 2.3, 3.11 list them all.
2. **Add a `CLAUDE.md` / `AGENTS.md`** at the repo root: the MVP contract in ten lines, the feature-registration recipe, the service names table, the three identity keys (until unified), the threading rule, the test command, and the "known traps" (bind_events timing, `on_view_close` super call, `"dirty"` notifications). Everything in it must be verified against source, and CI should run its code snippets.
3. **Export the public API** from `opaque/__init__.py` with `__all__` and ship `py.typed`. Typed lookups (4.1) matter double for agents: the type checker becomes the agent's feedback loop.
4. **Make errors teach.** Every framework-raised error should state the fix ("Feature 'X' is already registered. feature_name() must be unique; rename it or reuse the existing presenter."). Agents recover from loud, instructive errors in one step; silent `None`s cost a whole debugging session.
5. **Track the plans.** `docs/superpowers/plans/` (13 design documents from the UI sessions) is untracked. It is the only written architecture record. Commit it, or convert the durable decisions into ADRs under `docs/adr/`.
6. **Add CI** that runs: import of every module (this alone catches 2.4 and 2.5), pytest, mypy, and execution of the README quick start. A doc-snippet test keeps the docs honest permanently.

---

## 6. Consistency and polish (P3)

- Spelling: British prose (`colour`, `localisation`) against American identifiers (`color_picker`, `ColorPicker`) — sometimes in one statement (`color_picker.py:127`). Pick one for identifiers (American matches Qt) and apply it.
- Naming: `apply_theme` vs `update_theme` for the same concept; `setup_ui` vs `_setup_ui` vs `_init_ui`; camelCase Qt setters next to snake_case framework methods on the same class.
- Five independent definitions of the minimum hit-target size (24/28 px) across `self_check.py`, `color_picker.py`, `notification_widget.py` (twice), `version_info.py`. One token in the theme package should own it.
- Typos in shipped docstrings: "Prensenter", "worskpace", "heigh", "Initialize single instead service", "peparator".
- Unused imports in ~8 files; commented-out code in `view.py`, `toolbar.py`, `configuration.py`, `notification_presenter.py`.
- Duplicated widgets: three hand-rolled "×" close buttons; `ToastWidget` and `NotificationListItem` build the same row twice; two identical `_confirm_*` helpers.
- `SettingsService` writes and reads the whole JSON file once per feature during registration and once per feature on every Apply; the title bar constructs a fresh `VersionManager` (filesystem probes included) on every update.

---

## 7. Open questions for the owner

These need a decision before the fixes above are shaped:

1. **Distribution intent.** Is PyPI publication real and near-term? That decides how hard to push on 2.1-2.7 versus internal use. 
A. YES , and we should move to UV as project management infraestructure
2. **Python floor.** 3.8 is claimed, 3.12 is required by one file, 3.11 is what the venv runs. Pick one floor and enforce it in CI.
A.  Floor should be 3.11
3. **Theme scope.** Three third-party theme packages are hard dependencies for one service. Is multi-vendor theming a core promise, or would two built-in palettes (light/dark through QPalette, one source of truth) serve users better? The current design (3.10) suggests the second.
A. lets pick a good one that is consistent and leave the possibility to plug third party themes package if users want to develop that
4. **Feature identity.** `feature_name` vs `feature_id` vs class name (3.9). Recommendation: one explicit, stable `feature_id` string, declared on the model, used for registry, settings, and workspace; `feature_name()` becomes display-only.
A. your recommendation.
5. **Dynamic features.** Should features load/unload at runtime? If never, document it and the signal-hygiene debt (4.7) is acceptable. If yes, `remove_feature` and disconnect discipline become P1.
A. no need for dynamic features.
6. **The dead settings surface** (3.8): implement notification settings and language switching, or delete the fields. Shipping inert settings is the worst option.
A. not sure I understand this, the notification should be plugable by features, so for settings that means in changes we just inform that settings changed, if that's not working we should fix it (same for language (which is a settings btw?))
7. **`build_tools` ownership.** It is the least maintained area (syntax error, fictional docs, silently excluded scientific stack). Is it core to the product, or should it be split out or reduced to a documented PyInstaller recipe?
A. not sure I got, but I would like for this framework to be friendly to packaging with both pyinstaller and nuitka allowing the users to easily select one of them and set , if this does not make sense (in your opinion) then we can remove from the framework (users can decide on their projects what to use to build/pack) - your recommendation

---

## 8. Recommended sequence

1. **Week 1 — stop the bleeding (P0).** Fix imports/dependencies (2.1, 2.5), the f-string (2.4), the README (2.2); delete or quarantine `API.md` and fix `QUICK_REFERENCE.md` and the template (2.3); fill `__init__.py`, add `py.typed` and `__version__` (2.6); real URLs (2.7). Add CI with import-check + pytest + mypy. Commit `docs/superpowers/plans/`.
2. **Week 2 — verified defects (P1).** Items 3.1-3.11. Each is small; each deserves a regression test. Write `CLAUDE.md` while fixing them — the traps are freshest then.
3. **Then — the two structural moves (P2).** Typed service access + `create_services` seam (4.1), and `FeatureContext` (4.2). Do these before the framework gains external users; both change signatures.
4. **Ongoing.** Declarative feature registration (4.3), package re-layering (4.4), threading contract (4.5), and the P3 polish, each behind its own small plan.

---

## 9. Closure

Every item above was closed by the plans in `docs/superpowers/plans/`. The
index at `2026-09-08-techdebt-00-index.md` maps each item to its plan and
task; the table below names the commit(s) that did the work, for the items
where one commit is not obvious from the index alone.

### P0 — release blockers

| Item | Closed by |
|---|---|
| 2.1 theme packages hard dependencies | `77d4e29` (lazy imports), `54b0dea` (provider wrappers), `04cc8e0` (provider discovery) |
| 2.2 README quick start raises `TypeError` | `40b5d4d` |
| 2.3 `API.md`/`QUICK_REFERENCE.md` fictional classes | `b9fa5d7` (deleted `API.md`, rewrote the reference); template: `03d0868` |
| 2.4 f-string kills the package on 3.11 | `205162f` |
| 2.5 example services import `opaque.core.services` | `541efef` |
| 2.6 empty public API, no `__version__`/`py.typed` | `cc3f9ea` |
| 2.7 placeholder URLs, no CI, stray files | `46a202a` (packaging), `b91b408`/`661d9db` (CI) |

### P1 — verified defects

| Item | Closed by |
|---|---|
| 3.1 `"theme"`/`"themes"` name mismatch | `5f57053` |
| 3.2 `WorkspaceService.cleanup()` calls `initialize()` | `8322783` |
| 3.3 teardown order inverted | `dd0b9cf` |
| 3.4 observers shared across model instances | `5a7cc98` |
| 3.5 every field write notifies twice | `3dd1980` |
| 3.6 settings dialog corrupts typed values | `5cffcea`, `59e01a8`, `eb4f13d`, `029d7f3` |
| 3.7 settings persistence loses data silently | `e218fa4` (atomic writes); read/write-once perf: `e26c474` (this plan, Task 7) |
| 3.8 dead configuration surface | `addfa0d`, `a72a32a`, `d55c38f`, `c34e1f5`, `798ff42`, `2718b0a` |
| 3.9 three identity schemes for one feature | `30b4a84`, `16d41ee` |
| 3.10 theme system has two sources of truth | `459745b`, `d8dfe53`, `4a48eca`, `04cc8e0` |
| 3.11 (11 sub-items) | see the index's own breakdown table; the five `print()` calls are closed by this plan's Task 6 (`257e941`). `self_check.py` wiring was NOT closed by `4dbbd3b` (only the hit-target token moved); it was closed later — see `ENGINEERING_REVIEW_2026-09-09.md` and the review-followup plan. |

### P2 — architecture

| Item | Closed by |
|---|---|
| 4.1 shallow, stringly-typed service seam | `2e8387b`, `197c69d`, `85b098d`, `d87c29c` (typed lookups only; the `create_services` replacement seam was not built — accepted, see the decision below) |
| 4.2 everything holds the whole application | `0ec6a73`, `51952eb`, `121bd06` |
| 4.3 feature assembly manual and order-fragile | `c27fbaf`, `6185c7e` |
| 4.4 layering does not match the package names | `303826f`, `46f4fca` |
| 4.5 threading contract implicit | `e324446` |
| 4.6 shallow modules | this plan, Tasks 1-3: `e2d7e3c`, `656c99b`, `ea775e3` |
| 4.7 signal hygiene | accepted, not fixed — see below |

### AI-agent readiness and polish

| Item | Closed by |
|---|---|
| 5.1 fix the lies first | every Plan 02 commit (docs and example truth) |
| 5.2 `CLAUDE.md` kept true | `8e02ff7` and every plan since, by the rule each plan states: update the doc that changed in the same commit |
| 5.3 export the public API, ship `py.typed` | `cc3f9ea` |
| 5.4 make errors teach | `8fbd782`, `30b4a84`, `6185c7e` |
| 5.5 track the plans | `8e02ff7` |
| 5.6 add CI | `b91b408` |
| 6. spelling, naming, hit-target token, typos, unused imports, duplicated widgets, settings I/O churn | this plan, Tasks 4-8: `4dbbd3b`, `201c64c`, `257e941`, `e26c474`, `12a31b3` |

### Items accepted rather than fixed, with the reason

| Item | Decision |
|---|---|
| 4.7 signal hygiene | Accepted per D6: features never unload, so the shell connects once and never disconnects. `tests/test_signal_policy.py` keeps the assumption honest. |
| `NotificationPresenter` is not a feature | Accepted: it is a system presenter and takes the main window by design. |
| `opaque/view/application.py` | Kept for one release as a deprecated re-export of `opaque.shell`; not deleted by this plan (see "What this plan does not do"). |
| `models`, `presenters`, `services` have no `__init__.py` (implicit namespace packages) | Accepted as latent: no `pkgutil`/`iter_modules`/`collect_submodules` call anywhere in `src/` or `examples/` depends on it, and the wheel ships every module regardless. `tests/test_imports.py` no longer depends on the walk order either. Revisit only if a generated PyInstaller/Nuitka spec starts calling `collect_submodules("opaque")`. |
| `SingleInstanceService` binds a fixed TCP port (49152) to detect a second instance | Accepted as open: the lock file already moved to a per-user path; the port is still fixed, so two CI runners or a developer with the example already open can still collide. No task in this plan owns it. |
| Nine pylint design-metric checks (`too-many-instance-attributes`, `too-few-public-methods`, `too-many-branches`/`locals`/`statements`/`arguments`/`positional-arguments`, `duplicate-code`, `attribute-defined-outside-init`) | Disabled project-wide in `pyproject.toml`, not fixed. Real fixes mean splitting classes and methods apart or extracting a shared base between the two build backends — real refactors with behaviour risk, beyond a lint-cleanliness task. See `docs/known-issues/pylint-design-metrics.md`. |
| `create_services` seam (4.1 second half) | Accepted 2026-09-09: services are constructed inline in the shell and are not replaceable by subclasses. Revisit only if a real application needs to substitute a built-in service. |
