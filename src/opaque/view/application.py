# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

Deprecated import path for the application shell.

BaseApplication moved to opaque.shell, because it is the shell and not a view.
Import it from there. This module is kept for one release so existing code and
existing documentation keep working.
"""

import warnings

from opaque.shell import BaseApplication

warnings.warn(
    "opaque.view.application is deprecated. Import BaseApplication from "
    "opaque.shell instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["BaseApplication"]
