# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

OPAQUE — an opinionated PySide6 MDI application framework (MVP pattern). The library lives in `src/opaque`. The reference applications are `examples/quickstart/main.py` (smallest, executed by the suite) and `examples/basic_example/main.py` (full). A ranked engineering review with verified defects and open decisions is in `docs/ENGINEERING_REVIEW.md` — read it before structural work.

## Commands

`uv` owns the environment. It reads `.python-version`, which pins 3.11, and `uv.lock`, which is committed:

```bash
uv sync --all-extras                                  # create or update the environment
uv run python -m pytest tests -q                      # full suite, headless, ~3 s
uv run python -m pytest tests/test_localisation.py -q # one file
uv run python -m pytest tests -k "name" -q            # one test by name
uv run python -m mypy src/opaque                      # type check
uv run python -m pylint src/opaque                    # lint (config in pyproject.toml)
uv run python examples/basic_example/main.py          # run the example app
```

Notes:
- Tests run headless. `tests/conftest.py` sets `QT_QPA_PLATFORM=offscreen` before Qt imports and provides deterministic palette fixtures. Keep new tests headless.
- The interpreter floor is Python 3.11 and `uv` owns the environment. `uv.lock` is committed; run `uv sync --all-extras` after a pull that changes it.

## Documentation state

`docs/API.md` is deleted; it described a framework that does not exist. `docs/QUICK_REFERENCE.md` and the README quick start were rewritten from source on 2026-09-08 and are now guarded by tests: `tests/test_documentation.py` proves every `opaque` import printed in any Markdown file resolves, and `tests/test_quickstart.py` proves the README block is byte-identical to `examples/quickstart/main.py` and that it builds headless.

If you change a public name, those two tests fail. Update the document in the same commit; do not add the file to `SKIPPED_FILES`.

The worked examples are `examples/quickstart/main.py` (smallest) and `examples/basic_example/main.py` (full). The package `opaque.core` does not exist and never did — never import it.

## Architecture

- **One feature = one MVP triple.** `BaseModel` (`models/model.py`), `BaseView` (`view/view.py`, an MDI sub-window), `BasePresenter` (`presenters/presenter.py`). The shell class `BaseApplication` is a `QMainWindow` in `view/application.py` — despite the package name it owns the service registry, the feature registry, the toolbar, and the MDI area. The model must override `feature_name()`; `feature_icon()` and `feature_description()` have working defaults (a null icon and an empty string).
- **Registration recipe** (inside the app subclass `__init__`, after `super().__init__(config)`): construct model, then view, then presenter — each takes the application object — then `self.register_feature(presenter)`. Order matters; wrong order raises a bare `AttributeError`.
- **`BasePresenter.__init__` calls `bind_events()` at its end.** Anything a subclass creates after `super().__init__(...)` does not exist yet inside `bind_events()`. Create the attribute before the `super()` call, or connect it in `on_view_show()`. Getting it wrong raises an `AttributeError` whose message states this rule.
- **`on_view_close()` is a plain hook.** Override it to save state. Do not call `super()` and do not call `cleanup()`; `BasePresenter._handle_view_closed()` owns the order and calls `cleanup()` straight after the hook returns. It runs once even if the view emits `window_closed` twice.
- **Model fields**: declare `Field` subclasses (`models/annotations.py`) as class attributes. `ModelMeta` (`models/abstract_model.py`) rewrites them into validating properties. `settings=True` puts a field in the settings dialog and `settings.json`; `workspace=True` puts it in workspace files. `Field` is pure metadata; the observer list lives on the model instance (`AbstractModel.attach`/`detach`), so two instances of one model class never share observers. One field write gives exactly one `update()` call; `mark_dirty()` only sets a flag and does not notify.
- **ServiceLocator** (`services/service.py`): string-keyed, returns `Optional[BaseService]` — a wrong name is a silent `None`. Registered names: `settings`, `workspace`, `themes` (plural — `"theme"` is a known live bug), `notification`, `logger`, `single_instance`, and `console` (lazy, only after a console feature exists). `VersionManager` is never registered.
- **Three identity keys per feature** (known defect, do not add a fourth): the feature registry uses `model.feature_name()`, settings use `presenter.feature_id` (defaults to the presenter class name), workspace files use the presenter class name.
- **Theme rule**: a widget must never write a literal colour or point size. Ask `view/theme/tokens.py` for colours and `type_scale.py` for fonts. Tokens read `QApplication.palette()`, and `QPalette` is the single source of truth. `ThemeService` offers three built-in themes (`Default`, `Light`, `Dark`) that are palettes and nothing else; `view/theme/palettes.py` is the only module in the framework that holds a hex colour. Every other theme arrives through a `ThemeProvider` (`services/theme_provider.py`, implementations in `services/theme_providers.py`), which imports its package lazily and must set a palette that matches the polarity of the style sheet it installs. No theme package is a hard dependency; install the `themes` extra to get them.
- **Theme repaint**: a widget that caches a token value must declare `apply_theme()` with no arguments. `BaseApplication._repaint_after_theme_change()` walks the widget tree after every theme change and calls it. Do not connect `theme_changed` in a presenter; the shell already does the walk.
- **i18n rule**: every user-visible string is a literal inside `self.tr()`. `tests/test_localisation.py` scans the source and fails on violations.
- **Threading**: everything runs on the UI thread. A model field write synchronously calls presenter code that touches widgets, so a write from a worker thread raises `RuntimeError` naming the model and the field (`_assert_ui_thread` in `models/abstract_model.py`). The check is skipped when no `QCoreApplication` exists, so a model stays unit testable. The queue-and-drain pattern in `services/console_service.py` is the approved shape for cross-thread data.

## Conventions

- Commits: conventional style `type(scope): summary` in plain, simple English (match `git log`).
- Identifiers use American spelling (`color`); historic prose/comments use British spelling — do not "fix" prose spelling in unrelated diffs.
- Shell signal wiring goes through lambdas by stated policy (`_wire_shell_signals` docstring); there is no disconnect discipline yet, and features never unload at runtime.
- Design plans from previous sessions are in `docs/superpowers/plans/`; known-issue write-ups in `docs/known-issues/`.
