# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

The one close button.

Three widgets each built their own, with three sizes, three tool tips and
three accessible names, and two of them were smaller than the minimum hit
target. This is the only module in the framework that holds the multiplication
sign used as a close glyph.
"""

from typing import Optional

from PySide6.QtWidgets import QPushButton, QWidget

from opaque.view.theme import MINIMUM_HIT_TARGET, TypeScale


class CloseButton(QPushButton):
    """
    A small square button that closes the thing it sits on.

    It carries an accessible name, because a screen reader cannot read a
    glyph, and it is never smaller than the minimum hit target.
    """

    GLYPH = "×"

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(self.GLYPH, parent)

        self.setMinimumSize(MINIMUM_HIT_TARGET, MINIMUM_HIT_TARGET)
        self.setMaximumSize(MINIMUM_HIT_TARGET, MINIMUM_HIT_TARGET)
        self.setFont(TypeScale.body())
        self.setFlat(True)
        self.setAccessibleName(self.tr("Close"))
        self.setToolTip(self.tr("Close"))
