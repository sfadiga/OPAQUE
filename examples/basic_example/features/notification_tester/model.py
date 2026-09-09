"""
Notification Tester Model
"""
from typing import Optional
from PySide6.QtGui import QIcon

from opaque.features.context import FeatureContext
from opaque.models.model import BaseModel
from opaque.models.annotations import StringField


class NotificationTesterModel(BaseModel):
    """Model for the notification tester feature."""

    FEATURE_ID = "notification_tester"

    # --- Feature Interface ---
    FEATURE_NAME = "Notification Tester"
    FEATURE_TITLE = "Notification System Test"
    FEATURE_ICON = "format-justify-left"
    FEATURE_DESCRIPTION = "Test the notification system"
    FEATURE_MODAL = False
    # ----------------------------------
    
    selected_level = StringField(
        default="INFO",
        description="Selected notification level",
        workspace=True,
        binding=True
    )

    status_message = StringField(
        default="Ready to test notifications...",
        description="Current status message",
        binding=True
    )

    def __init__(self, context: FeatureContext):
        super().__init__(context)

    # --- Model Interface --------------------------------

    def feature_name(self) -> str:
        return self.FEATURE_NAME

    def feature_icon(self) -> QIcon:
        return QIcon.fromTheme(self.FEATURE_ICON)

    def feature_description(self) -> str:
        return self.FEATURE_DESCRIPTION
        
    def feature_modal(self) -> bool:
        return self.FEATURE_MODAL

    # ----------------------------------------------------

    def initialize(self):
        """Initialize the model."""
        pass
