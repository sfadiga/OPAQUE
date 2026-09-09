# This Python file uses the following encoding: utf-8
"""Tests for FeatureContext, the only thing a feature may know."""

import pytest

from PySide6.QtGui import QIcon

from opaque.features.context import FeatureContext
from opaque.models.configuration import DefaultApplicationConfiguration
from opaque.services.console_service import ConsoleService
from opaque.services.service import ServiceLocator
from opaque.services.settings_service import SettingsService


class _TestConfiguration(DefaultApplicationConfiguration):
    """
    The smallest concrete configuration.

    DefaultApplicationConfiguration declares its five accessors abstract, so
    it cannot be built directly. tests/conftest.py already has a
    TestConfiguration for the same reason; this one is not imported from
    there because conftest.py is not meant to be imported as a module.
    """

    def get_application_name(self) -> str:
        return "FeatureContextTest"

    def get_application_title(self) -> str:
        return "Feature Context Test"

    def get_application_description(self) -> str:
        return "A configuration used only by this test file."

    def get_application_icon(self) -> QIcon:
        return QIcon()

    def get_application_organization(self) -> str:
        return "Opaque Tests"


@pytest.fixture(autouse=True, scope="module")
def _warm_up_qmdisubwindow(qapp):
    """
    Show and close one QMdiSubWindow before any test in this file runs.

    Building a BaseView and a BasePresenter around it, as the very first
    QMdiSubWindow of an offscreen-platform Qt session, corrupts the heap
    inside pytest-qt's post-test app.processEvents() call -- a native crash,
    not a normal test failure, reproduced with plain PySide6 (no OPAQUE code
    involved) by running only this file's presenter test in isolation. The
    crash never happens as part of the full suite, because
    tests/test_application_shell.py builds a real BaseApplication (and so a
    real QMdiSubWindow) first, alphabetically, and that is enough to avoid
    it. CLAUDE.md documents running a single test file as a supported
    workflow, so this file must not depend on file execution order to stay
    safe; building and discarding one sub-window here does the same warm-up
    without relying on it.
    """
    from opaque.view.widgets.mdi_window import OpaqueMdiSubWindow

    warm_up = OpaqueMdiSubWindow()
    warm_up.show()
    warm_up.close()


@pytest.fixture
def context(tmp_path, qapp):
    """
    Give the test an empty service locator and restore the old one.

    A blind ServiceLocator.cleanup_services() here would call cleanup() on
    whatever tests/conftest.py's session-scoped app_window had already
    registered (single instance, workspace, theme, settings, notification,
    logger), permanently tearing them down for the rest of the session the
    first time a test file runs after this one alphabetically. The same trap
    is documented in tests/test_example_app.py and tests/test_quickstart.py;
    this fixture follows their save/clear/restore pattern instead.
    """
    saved = dict(ServiceLocator._services)
    ServiceLocator._services.clear()
    settings = SettingsService(tmp_path / "settings.json")
    settings.initialize()
    ServiceLocator.register_service(settings)
    yield FeatureContext(configuration=_TestConfiguration())
    ServiceLocator.cleanup_services()
    ServiceLocator._services.update(saved)


def test_the_context_gives_the_configuration(context):
    assert isinstance(
        context.configuration, DefaultApplicationConfiguration)


def test_the_context_gives_a_typed_service(context):
    assert isinstance(context.service(SettingsService), SettingsService)


def test_a_missing_service_raises_through_the_context(context):
    from opaque.services.theme_service import ThemeService

    with pytest.raises(LookupError):
        context.service(ThemeService)


def test_an_optional_service_answers_none(context):
    assert context.optional_service(ConsoleService) is None


def test_the_context_gives_the_application_icon(context):
    assert isinstance(context.application_icon(), QIcon)


def test_the_context_carries_no_main_window_by_default(context):
    assert context.shell is None


def test_showing_a_window_without_a_shell_is_refused(context, qtbot):
    from PySide6.QtWidgets import QWidget

    widget = QWidget()
    qtbot.addWidget(widget)

    with pytest.raises(RuntimeError) as error:
        context.show_window(widget)

    assert "shell" in str(error.value)


def test_the_context_holds_no_reference_to_a_service_instance(context):
    # The context looks a service up on every call, so a service that is
    # replaced at run time is not shadowed by a stale reference.
    first = context.service(SettingsService)
    ServiceLocator.unregister_service(SettingsService.SERVICE_NAME)

    with pytest.raises(LookupError):
        context.service(SettingsService)

    assert first is not None


def test_a_model_takes_a_context(context):
    from opaque.models.model import BaseModel

    class _Model(BaseModel):
        FEATURE_ID = "ctx_model"

        def feature_name(self) -> str:
            return "Context Model"

    model = _Model(context)
    assert model.context is context


def test_a_model_no_longer_offers_the_whole_application(context):
    from opaque.models.model import BaseModel

    assert not hasattr(BaseModel, "app")


def test_a_view_takes_a_context(context, qtbot):
    from opaque.view.view import BaseView

    view = BaseView(context)
    qtbot.addWidget(view)
    assert view.context is context


def test_a_view_no_longer_offers_the_whole_application():
    from opaque.view.view import BaseView

    assert not hasattr(BaseView, "app")


def test_a_presenter_takes_a_context(context, qtbot):
    from opaque.models.model import BaseModel
    from opaque.presenters.presenter import BasePresenter
    from opaque.view.view import BaseView

    class _Model(BaseModel):
        FEATURE_ID = "ctx_presenter"

        def feature_name(self) -> str:
            return "Context Presenter"

    class _Presenter(BasePresenter):
        def bind_events(self) -> None:
            pass

        def update(self, field_name, new_value, old_value=None, model=None):
            pass

        def on_view_show(self) -> None:
            pass

    view = BaseView(context)
    qtbot.addWidget(view)
    presenter = _Presenter(_Model(context), view, context)

    assert presenter.context is context


def test_the_presenter_constructor_asks_for_a_context():
    import inspect

    from opaque.presenters.presenter import BasePresenter

    parameters = list(inspect.signature(BasePresenter.__init__).parameters)
    assert parameters == ["self", "model", "view", "context"]
