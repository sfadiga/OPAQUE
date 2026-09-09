# This Python file uses the following encoding: utf-8
"""
The signal policy of the shell.

Decision D6: features never unload at run time, so the shell connects its
signals once and never disconnects them. These tests keep the assumption that
makes it safe. If one of them fails, the policy has to change with the code.
"""

import inspect

from opaque.shell import BaseApplication


def test_the_shell_offers_no_way_to_unregister_a_feature():
    assert not hasattr(BaseApplication, "unregister_feature")


def test_the_wiring_docstring_states_the_policy():
    text = inspect.getdoc(BaseApplication._wire_shell_signals) or ""
    assert "never unload" in text
    assert "disconnect" in text


def test_a_presenter_still_disconnects_from_its_own_view():
    from opaque.presenters.presenter import BasePresenter

    source = inspect.getsource(BasePresenter.cleanup)
    assert "disconnect" in source
