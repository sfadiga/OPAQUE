# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

OPAQUE — an opinionated PySide6 MDI application framework.

Import the framework contract from here, not from the deep module paths.
One feature is one MVP triple: a BaseModel, a BaseView, and a BasePresenter.

    from opaque import BaseApplication, BaseModel, BasePresenter, BaseView

The imports below are grouped by layer. No order is required between them.
The one real import cycle in this package is `view/view.py` to
`view/widgets/__init__.py` to `toolbar.py` to `presenters/presenter.py`,
which would then re-import `view.py`. It is already broken inside
`presenters/presenter.py`, which keeps its `BaseView` and `BaseApplication`
imports behind `TYPE_CHECKING`. That guard holds whatever order this file
uses, so do not treat this list as fragile.
"""

from importlib.metadata import (
    PackageNotFoundError as _PackageNotFoundError,
    version as _installed_version,
)

from opaque.models.annotations import (
    BoolField,
    ChoiceField,
    Field,
    FloatField,
    IntField,
    ListField,
    StringField,
    UIType,
)
from opaque.models.abstract_model import AbstractModel
from opaque.models.configuration import DefaultApplicationConfiguration
from opaque.services.service import BaseService, ServiceLocator
from opaque.features.context import FeatureContext
from opaque.view.application import BaseApplication
from opaque.models.model import BaseModel
from opaque.view.view import BaseView
from opaque.presenters.presenter import BasePresenter

try:
    __version__ = _installed_version("opaque-framework")
except _PackageNotFoundError:
    # Running from a source tree with no install. The metadata is the only
    # place a version lives, so say so instead of inventing a number.
    __version__ = "0.0.0+unknown"

__all__ = [
    "AbstractModel",
    "BaseApplication",
    "BaseModel",
    "BasePresenter",
    "BaseService",
    "BaseView",
    "BoolField",
    "ChoiceField",
    "DefaultApplicationConfiguration",
    "FeatureContext",
    "Field",
    "FloatField",
    "IntField",
    "ListField",
    "ServiceLocator",
    "StringField",
    "UIType",
    "__version__",
]
