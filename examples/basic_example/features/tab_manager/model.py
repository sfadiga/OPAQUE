# This Python file uses the following encoding: utf-8
from PySide6.QtGui import QIcon
from opaque.models.model import BaseModel
from PySide6.QtWidgets import QApplication, QStyle

class TabManagerModel(BaseModel):
    def feature_name(self) -> str:
        return "Tab Manager"

    def feature_icon(self) -> QIcon:
        return QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)

    def feature_description(self) -> str:
        return "Demonstrates CloseableTabWidget"
