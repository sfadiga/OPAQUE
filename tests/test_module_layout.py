# This Python file uses the following encoding: utf-8
"""The package layout must say what each module is."""

import warnings


def test_the_shell_lives_in_its_own_module():
    from opaque.shell import BaseApplication

    assert BaseApplication.__module__ == "opaque.shell"


def test_the_old_import_path_still_works():
    # The module warns as it imports, and Python only runs a module's own
    # top level code once per process, so whichever test imports this path
    # first pays for the warning. Guard it here, not just in the test below
    # that means to assert on the warning, or a strict -W error run fails on
    # whichever of the two happens to import it first.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from opaque.view.application import BaseApplication as FromView
    from opaque.shell import BaseApplication as FromShell

    assert FromView is FromShell


def test_the_old_import_path_warns():
    import importlib

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        import opaque.view.application
        importlib.reload(opaque.view.application)

    assert any(issubclass(entry.category, DeprecationWarning)
               for entry in caught)


def test_the_public_api_exports_the_shell():
    import opaque

    assert opaque.BaseApplication.__module__ == "opaque.shell"


def test_the_view_package_holds_no_service_import():
    import inspect

    from opaque.view import view

    source = inspect.getsource(view)
    assert "ServiceLocator" not in source
