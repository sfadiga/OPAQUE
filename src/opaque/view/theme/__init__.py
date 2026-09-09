# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

Theme token layer.

A widget must never write a literal colour, font family or font size. Import
the tokens from this package instead. That keeps every widget correct when the
user changes the theme, and it keeps every colour pair above the WCAG contrast
threshold.
"""

from opaque.view.theme.contrast import (
    contrast_ratio,
    readable_foreground,
    relative_luminance,
)
from opaque.view.theme.palettes import build_dark_palette, build_light_palette
from opaque.view.theme.tokens import (
    interactive,
    is_dark_theme,
    MINIMUM_HIT_TARGET,
    muted_on_surface,
    on_interactive,
    on_surface,
    on_surface_variant,
    outline,
    StatusColors,
    StatusRole,
    status_colors,
    surface,
    surface_variant,
)
from opaque.view.theme.type_scale import TypeScale

__all__ = [
    "contrast_ratio",
    "build_dark_palette",
    "build_light_palette",
    "interactive",
    "is_dark_theme",
    "MINIMUM_HIT_TARGET",
    "muted_on_surface",
    "on_interactive",
    "on_surface",
    "on_surface_variant",
    "outline",
    "readable_foreground",
    "relative_luminance",
    "StatusColors",
    "StatusRole",
    "status_colors",
    "surface",
    "surface_variant",
    "TypeScale",
]
