# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

OPAQUE — an opinionated PySide6 MDI application framework (MVP pattern). The library lives in `src/opaque`. The reference application is `examples/basic_example/main.py`. A ranked engineering review with verified defects and open decisions is in `docs/ENGINEERING_REVIEW.md` — read it before structural work.

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

## Do not trust these docs

`docs/API.md`, `docs/QUICK_REFERENCE.md`, the README quick start, and `src/opaque/build_tools/templates/basic_app_template/main.py` contain class names and signatures that do not exist (`Application`, `AppModel`, `build_executable`, ...). Verify every import and signature against the source. The one accurate worked example is `examples/basic_example/main.py`. The example *services* under `examples/basic_example/services/` import `opaque.core.services`, which does not exist — `opaque.core` is a ghost package still referenced in `app_presenter.py`; never import it. It used to be referenced in `pyproject.toml` as well, through a `core/py.typed` package-data entry, and that entry is gone.

## Architecture

- **One feature = one MVP triple.** `BaseModel` (`models/model.py`), `BaseView` (`view/view.py`, an MDI sub-window), `BasePresenter` (`presenters/presenter.py`). The shell class `BaseApplication` is a `QMainWindow` in `view/application.py` — despite the package name it owns the service registry, the feature registry, the toolbar, and the MDI area.
- **Registration recipe** (inside the app subclass `__init__`, after `super().__init__(config)`): construct model, then view, then presenter — each takes the application object — then `self.register_feature(presenter)`. Order matters; wrong order raises a bare `AttributeError`.
- **`BasePresenter.__init__` calls `bind_events()` at its end.** Anything a subclass creates after `super().__init__(...)` does not exist yet inside `bind_events()`. Create widgets/attributes before the `super()` call or guard for `None`.
- **`on_view_close()` is abstract but carries the real cleanup in its body.** An override must call `super().on_view_close()` or the presenter never cleans up.
- **Model fields**: declare `Field` subclasses (`models/annotations.py`) as class attributes. `ModelMeta` (`models/abstract_model.py`) rewrites them into validating properties. `settings=True` puts a field in the settings dialog and `settings.json`; `workspace=True` puts it in workspace files. Every field write calls presenter `update()` twice: once with the field name, once with the literal `"dirty"`. Observer lists live on the class-level `Field` objects, so all instances of one model class share observers (known defect).
- **ServiceLocator** (`services/service.py`): string-keyed, returns `Optional[BaseService]` — a wrong name is a silent `None`. Registered names: `settings`, `workspace`, `themes` (plural — `"theme"` is a known live bug), `notification`, `logger`, `single_instance`, and `console` (lazy, only after a console feature exists). `VersionManager` is never registered.
- **Three identity keys per feature** (known defect, do not add a fourth): the feature registry uses `model.feature_name()`, settings use `presenter.feature_id` (defaults to the presenter class name), workspace files use the presenter class name.
- **Theme rule**: a widget must never write a literal colour or point size. Ask `view/theme/tokens.py` for colours and `type_scale.py` for fonts. Tokens read `QApplication.palette()`; only the qt-themes vendor path updates the palette, so stylesheet themes (qt-material, QDarkStyle) leave tokens stale (known defect).
- **i18n rule**: every user-visible string is a literal inside `self.tr()`. `tests/test_localisation.py` scans the source and fails on violations.
- **Threading**: everything runs on the UI thread. A model field write synchronously calls presenter code that touches widgets — never write model fields from a worker thread. The queue-and-drain pattern in `services/console_service.py` is the approved shape for cross-thread data.

## Conventions

- Commits: conventional style `type(scope): summary` in plain, simple English (match `git log`).
- Identifiers use American spelling (`color`); historic prose/comments use British spelling — do not "fix" prose spelling in unrelated diffs.
- Shell signal wiring goes through lambdas by stated policy (`_wire_shell_signals` docstring); there is no disconnect discipline yet, and features never unload at runtime.
- Design plans from previous sessions are in `docs/superpowers/plans/`; known-issue write-ups in `docs/known-issues/`.
