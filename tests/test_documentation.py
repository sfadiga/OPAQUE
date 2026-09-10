# This Python file uses the following encoding: utf-8
"""
Prove that every `opaque` import printed in a Markdown file really exists.

For a human, wrong documentation costs one puzzled minute. For an AI agent
it costs a whole debugging loop: the agent trusts the document, writes code
against a class that was never written, and then has to re-derive the API
from source. This test makes that failure impossible to ship.

The test reads import statements only. It does not execute a snippet: most
snippets are fragments that need a running QApplication. An import that
resolves plus a name that resolves catches every defect the 2026-09-08
review found in the documentation.
"""

import ast
import importlib
import re
import warnings
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# A document may be kept on purpose while it is being rewritten. Name it
# here with the reason, or delete it. An empty exception list is the goal.
#
# The files below are design plans in docs/superpowers/plans/, not
# documentation of the current API. Plans 03, 05, 08, 09, and 10 show code
# for modules the plan itself has not built yet (opaque.shell,
# opaque.features.context, opaque.build_tools.config, ...); this plan's own
# file shows the ghost opaque.core imports it is fixing, as the "before"
# half of a replace. None of them claim the current framework has these
# names, so they are not the lie this checker exists to catch.
SKIPPED_FILES: dict[str, str] = {
    "2026-09-08-techdebt-02-docs-and-examples-truth.md": (
        "Shows the ghost opaque.core.services / opaque.core.application "
        "imports as the 'before' half of a replace instruction, not as a "
        "claim that they exist."
    ),
    "2026-09-08-techdebt-03-theming-single-source.md": (
        "Design plan for modules this plan has not built yet "
        "(opaque.view.theme.palettes, opaque.services.theme_provider(s))."
    ),
    "2026-09-08-techdebt-05-settings-subsystem.md": (
        "Design plan for a notification_presenter/settings_service shape "
        "this plan has not built yet."
    ),
    "2026-09-08-techdebt-08-feature-context.md": (
        "Design plan for opaque.features.context and opaque.shell, which "
        "do not exist until that plan runs."
    ),
    "2026-09-08-techdebt-09-build-backends.md": (
        "Design plan for opaque.build_tools.config, opaque.shell, and "
        "opaque.features.context, none built yet."
    ),
    "2026-09-08-techdebt-10-polish.md": (
        "Design plan for opaque.view.version_info_schema and a "
        "opaque.view.widgets.close_button split, not built yet."
    ),
    "2026-09-07-opaque-ui-11-opportunities.md": (
        "Historical plan that fixed opaque.view.layouts.flow.FlowLayout "
        "before Plan 10 Task 1 deleted that module for having no "
        "production caller. The import was real when this plan ran."
    ),
}

_CODE_BLOCK = re.compile(r"```(?:python|py)\n(.*?)```", re.DOTALL)


def _markdown_files() -> list[Path]:
    files = [REPO_ROOT / "README.md", REPO_ROOT / "CLAUDE.md"]
    files.extend(sorted((REPO_ROOT / "docs").rglob("*.md")))
    return [f for f in files if f.is_file() and f.name not in SKIPPED_FILES]


def _opaque_imports(text: str) -> list[tuple[str, tuple[str, ...]]]:
    """
    Return every opaque import in the Markdown text.

    Each entry is (module_name, imported_names). A plain `import opaque.x`
    gives an empty name tuple.
    """
    found: list[tuple[str, tuple[str, ...]]] = []
    for block in _CODE_BLOCK.findall(text):
        try:
            tree = ast.parse(block)
        except SyntaxError:
            # A fragment that is not a whole module. Its imports are still
            # readable line by line.
            tree = None
        if tree is None:
            for line in block.splitlines():
                stripped = line.strip()
                if not stripped.startswith(("from opaque", "import opaque")):
                    continue
                try:
                    tree = ast.parse(stripped)
                except SyntaxError:
                    continue
                found.extend(_from_tree(tree))
            continue
        found.extend(_from_tree(tree))
    return found


def _from_tree(tree: ast.AST) -> list[tuple[str, tuple[str, ...]]]:
    found: list[tuple[str, tuple[str, ...]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] == "opaque":
                found.append((node.module, tuple(a.name for a in node.names)))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == "opaque":
                    found.append((alias.name, ()))
    return found


CASES = [
    pytest.param(path, module, names, id=f"{path.name}:{module}")
    for path in _markdown_files()
    for module, names in _opaque_imports(path.read_text(encoding="utf-8"))
]


def test_the_scanner_found_documentation_to_check():
    assert len(CASES) > 10


@pytest.mark.parametrize("path,module,names", CASES)
def test_documented_import_resolves(path, module, names):
    # A deprecated-but-still-real module (opaque.view.application) warns as
    # it imports. This check asks only whether the import resolves, not
    # whether it is the current path, so a strict -W error run must not
    # fail here over a warning the module means to raise.
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            imported = importlib.import_module(module)
    except ImportError as error:
        pytest.fail(f"{path.name} documents '{module}', which does not exist: {error}")

    missing = [name for name in names if not hasattr(imported, name)]
    assert missing == [], f"{path.name} documents {missing} in '{module}'"
