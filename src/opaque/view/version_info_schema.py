# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

What the version dialogs show.

The dialogs used to read nine string keys out of a plain dictionary in five
places, with nothing declaring what the dictionary held, so a typo in a key
gave an empty value in the interface and no error anywhere. Each field keeps
the exact fallback the dialogs already used for that key, because some rows
are shown unconditionally with a placeholder and some are hidden entirely
when the source carries nothing for them; changing a fallback would change
what the user sees.
"""

from dataclasses import dataclass, fields
from typing import Any, Dict


@dataclass(frozen=True)
class VersionInfo:
    """
    One version record.

    Every field is a string, because every field is shown as text. A field
    the source does not carry keeps the default below, which is the same
    fallback the dialogs already passed to dict.get() for that key.
    """

    version: str = "Unknown"
    product_name: str = "OPAQUE Framework Application"
    company: str = ""
    description: str = ""
    copyright: str = ""
    build_date: str = ""
    build_number: str = ""
    commit_hash: str = ""
    build_tool: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VersionInfo":
        """
        Build a record from a dictionary, ignoring what it does not declare.

        Args:
            data: The dictionary to read. A key that is not a field is
                ignored, which is what stops a typo from becoming a silent
                attribute. A value of None is treated the same as a missing
                key, because the version detection this record reads from
                can store None for a field it could not determine.

        Returns:
            The record. Every missing field keeps its documented default.
        """
        known = {entry.name for entry in fields(cls)}
        return cls(**{
            name: str(value)
            for name, value in data.items()
            if name in known and value is not None
        })
