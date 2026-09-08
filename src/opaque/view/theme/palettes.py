# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

The built-in theme palettes.

This module is the only place in the framework that holds a hex colour value.
Every other module asks the token layer, and the token layer reads the palette
that these builders produce. That keeps one source of truth for colour.

Both palettes were measured against the WCAG text minimum of 4.5:1. The
measured ratios are checked in tests/theme/test_palettes.py, which fails if a
colour is edited to a value that no longer passes.
"""

from dataclasses import dataclass

from PySide6.QtGui import QColor, QPalette


@dataclass(frozen=True)
class _PaletteSpec:
    """One complete colour set. Every field is a hex string."""

    window: str
    window_text: str
    base: str
    alternate_base: str
    text: str
    button: str
    button_text: str
    mid: str
    highlight: str
    highlighted_text: str
    tool_tip_base: str
    tool_tip_text: str
    placeholder_text: str
    bright_text: str
    link: str
    link_visited: str
    disabled_text: str


# Text on base 17.40:1. Window text on window 15.96:1. Highlight 5.70:1.
_LIGHT = _PaletteSpec(
    window="#f5f5f5",
    window_text="#1a1a1a",
    base="#ffffff",
    alternate_base="#ededed",
    text="#1a1a1a",
    button="#e2e2e2",
    button_text="#1a1a1a",
    mid="#b0b0b0",
    highlight="#0b6ba8",
    highlighted_text="#ffffff",
    tool_tip_base="#ffffe1",
    tool_tip_text="#1a1a1a",
    placeholder_text="#6b6b6b",
    bright_text="#b3261e",
    link="#0b57d0",
    link_visited="#7b1fa2",
    disabled_text="#9e9e9e",
)

# Text on base 14.11:1. Window text on window 12.93:1. Highlight 7.54:1.
# The highlight is a pale fill with dark text. A saturated fill on a dark
# surface glares, which is the rule the status tables in tokens.py follow.
_DARK = _PaletteSpec(
    window="#1f2124",
    window_text="#e6e6e6",
    base="#17191c",
    alternate_base="#24272b",
    text="#e6e6e6",
    button="#2b2f33",
    button_text="#e6e6e6",
    mid="#55595e",
    highlight="#a8c7e0",
    highlighted_text="#08324f",
    tool_tip_base="#2b2f33",
    tool_tip_text="#e6e6e6",
    placeholder_text="#9aa0a6",
    bright_text="#f2b8b5",
    link="#a8c7e0",
    link_visited="#d0bcff",
    disabled_text="#6b7075",
)


def _build(spec: _PaletteSpec) -> QPalette:
    """Turn one specification into a complete QPalette."""
    palette = QPalette()
    role = QPalette.ColorRole
    group = QPalette.ColorGroup

    palette.setColor(role.Window, QColor(spec.window))
    palette.setColor(role.WindowText, QColor(spec.window_text))
    palette.setColor(role.Base, QColor(spec.base))
    palette.setColor(role.AlternateBase, QColor(spec.alternate_base))
    palette.setColor(role.Text, QColor(spec.text))
    palette.setColor(role.Button, QColor(spec.button))
    palette.setColor(role.ButtonText, QColor(spec.button_text))
    palette.setColor(role.Mid, QColor(spec.mid))
    palette.setColor(role.Dark, QColor(spec.mid))
    palette.setColor(role.Midlight, QColor(spec.alternate_base))
    palette.setColor(role.Light, QColor(spec.base))
    palette.setColor(role.Shadow, QColor(spec.mid))
    palette.setColor(role.Highlight, QColor(spec.highlight))
    palette.setColor(role.HighlightedText, QColor(spec.highlighted_text))
    palette.setColor(role.ToolTipBase, QColor(spec.tool_tip_base))
    palette.setColor(role.ToolTipText, QColor(spec.tool_tip_text))
    palette.setColor(role.PlaceholderText, QColor(spec.placeholder_text))
    palette.setColor(role.BrightText, QColor(spec.bright_text))
    palette.setColor(role.Link, QColor(spec.link))
    palette.setColor(role.LinkVisited, QColor(spec.link_visited))

    # A disabled widget must stay legible, only clearly inactive.
    disabled = QColor(spec.disabled_text)
    palette.setColor(group.Disabled, role.Text, disabled)
    palette.setColor(group.Disabled, role.WindowText, disabled)
    palette.setColor(group.Disabled, role.ButtonText, disabled)
    palette.setColor(group.Disabled, role.HighlightedText, disabled)

    return palette


def build_light_palette() -> QPalette:
    """Return a new palette for the built-in Light theme."""
    return _build(_LIGHT)


def build_dark_palette() -> QPalette:
    """Return a new palette for the built-in Dark theme."""
    return _build(_DARK)
