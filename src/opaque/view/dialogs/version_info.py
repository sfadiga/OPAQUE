"""
Version information dialog for OPAQUE framework applications.

@copyright 2025 Sandro Fadiga
Licensed under MIT License
"""

from typing import Dict, Any, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QTabWidget, QWidget, QGridLayout,
    QScrollArea, QGroupBox, QApplication
)
from PySide6.QtGui import QIcon, QMouseEvent

from opaque.view.theme import (
    TypeScale,
    interactive,
    muted_on_surface,
    outline,
    surface_variant,
)


class VersionInfoDialog(QDialog):
    """Dialog for displaying comprehensive version information."""

    def __init__(self, version_info: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.version_info = version_info or {}
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle(self.tr("Version Information"))
        self.setModal(True)
        self.setMinimumSize(480, 360)
        self.resize(500, 400)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Create tab widget
        tab_widget = QTabWidget()

        # Version tab
        version_tab = self._create_version_tab()
        tab_widget.addTab(version_tab, "Version")

        # Build info tab
        build_tab = self._create_build_tab()
        tab_widget.addTab(build_tab, "Build Information")

        # System info tab
        system_tab = self._create_system_tab()
        tab_widget.addTab(system_tab, "System Information")

        layout.addWidget(tab_widget)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        copy_button = QPushButton(self.tr("Copy to Clipboard"))
        copy_button.clicked.connect(self._copy_to_clipboard)
        button_layout.addWidget(copy_button)

        close_button = QPushButton(self.tr("Close"))
        close_button.clicked.connect(self.accept)
        close_button.setDefault(True)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _create_version_tab(self) -> QWidget:
        """Create the version information tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        # Main version info
        main_group = QGroupBox(self.tr("Application Version"))
        main_layout = QGridLayout(main_group)

        # Version
        version = self.version_info.get("version", "Unknown")
        main_layout.addWidget(QLabel(self.tr("Version:")), 0, 0)
        version_label = QLabel(version)
        version_font = version_label.font()
        version_font.setPointSize(version_font.pointSize() + 2)
        version_font.setBold(True)
        version_label.setFont(version_font)
        main_layout.addWidget(version_label, 0, 1)

        # Product name
        product_name = self.version_info.get(
            "product_name", "OPAQUE Framework Application")
        main_layout.addWidget(QLabel(self.tr("Product:")), 1, 0)
        main_layout.addWidget(QLabel(product_name), 1, 1)

        # Company
        company = self.version_info.get("company", "")
        if company:
            main_layout.addWidget(QLabel(self.tr("Company:")), 2, 0)
            main_layout.addWidget(QLabel(company), 2, 1)

        # Description
        description = self.version_info.get("description", "")
        if description:
            main_layout.addWidget(QLabel(self.tr("Description:")), 3, 0)
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            main_layout.addWidget(desc_label, 3, 1)

        # Copyright
        copyright_info = self.version_info.get("copyright", "")
        if copyright_info:
            main_layout.addWidget(QLabel(self.tr("Copyright:")), 4, 0)
            main_layout.addWidget(QLabel(copyright_info), 4, 1)

        layout.addWidget(main_group)
        layout.addStretch()

        return widget

    def _create_build_tab(self) -> QWidget:
        """Create the build information tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        # Build details
        build_group = QGroupBox(self.tr("Build Details"))
        build_layout = QGridLayout(build_group)

        row = 0

        # Build date
        build_date = self.version_info.get("build_date", "")
        if build_date:
            build_layout.addWidget(QLabel(self.tr("Build Date:")), row, 0)
            build_layout.addWidget(QLabel(build_date), row, 1)
            row += 1

        # Build number
        build_number = self.version_info.get("build_number", "")
        if build_number:
            build_layout.addWidget(QLabel(self.tr("Build Number:")), row, 0)
            build_layout.addWidget(QLabel(build_number), row, 1)
            row += 1

        # Commit hash
        commit_hash = self.version_info.get("commit_hash", "")
        if commit_hash:
            build_layout.addWidget(QLabel(self.tr("Commit Hash:")), row, 0)
            commit_label = QLabel(
                commit_hash[:16] + "..." if len(commit_hash) > 16 else commit_hash)
            commit_label.setToolTip(commit_hash)
            build_layout.addWidget(commit_label, row, 1)
            row += 1

        # Build tools
        build_tool = self.version_info.get("build_tool", "")
        if build_tool:
            build_layout.addWidget(QLabel(self.tr("Build Tool:")), row, 0)
            build_layout.addWidget(QLabel(build_tool), row, 1)
            row += 1

        # Framework version
        framework_version = self._get_framework_version()
        if framework_version:
            build_layout.addWidget(QLabel(self.tr("OPAQUE Framework:")), row, 0)
            build_layout.addWidget(QLabel(framework_version), row, 1)
            row += 1

        if row == 0:
            build_layout.addWidget(
                QLabel(self.tr("No build information available")), 0, 0, 1, 2)

        layout.addWidget(build_group)
        layout.addStretch()

        return widget

    def _create_system_tab(self) -> QWidget:
        """Create the system information tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Create scrollable text area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        text_widget = QTextEdit()
        text_widget.setReadOnly(True)
        # The platform fixed width font, at the size the user chose. A named
        # family is not installed everywhere and a fixed point size ignores
        # the operating system font scale.
        text_widget.setFont(TypeScale.mono())
        self.system_text = text_widget

        # Gather system information
        import platform as plt
        import sys
        from PySide6 import __version__ as pyside_version

        system_info = []
        system_info.append("=== System Information ===")
        system_info.append(
            f"Operating System: {plt.system()} {plt.release()} ({plt.machine()})")
        system_info.append(f"Platform: {plt.platform()}")
        system_info.append(f"Python Version: {sys.version}")
        system_info.append(f"PySide6 Version: {pyside_version}")
        system_info.append("")

        system_info.append("=== Application Information ===")
        app = QApplication.instance()
        if app:
            system_info.append(f"Application Name: {app.applicationName()}")
            system_info.append(
                f"Application Version: {app.applicationVersion()}")
            system_info.append(f"Organization: {app.organizationName()}")
            system_info.append("")

        # Add version info
        if self.version_info:
            system_info.append("=== Version Details ===")
            for key, value in sorted(self.version_info.items()):
                if value:
                    system_info.append(
                        f"{key.replace('_', ' ').title()}: {value}")

        text_widget.setText("\n".join(system_info))
        scroll.setWidget(text_widget)
        layout.addWidget(scroll)

        return widget

    def _get_framework_version(self) -> str:
        """Get OPAQUE framework version."""
        try:
            import opaque
            return getattr(opaque, '__version__', 'Unknown')
        except (ImportError, AttributeError):
            return "Unknown"

    def _copy_to_clipboard(self):
        """Copy version information to clipboard."""
        info_lines = []

        # Basic info
        info_lines.append("=== Version Information ===")
        version = self.version_info.get("version", "Unknown")
        product_name = self.version_info.get(
            "product_name", "OPAQUE Framework Application")
        info_lines.append(f"Product: {product_name}")
        info_lines.append(f"Version: {version}")

        company = self.version_info.get("company", "")
        if company:
            info_lines.append(f"Company: {company}")

        description = self.version_info.get("description", "")
        if description:
            info_lines.append(f"Description: {description}")

        copyright_info = self.version_info.get("copyright", "")
        if copyright_info:
            info_lines.append(f"Copyright: {copyright_info}")

        info_lines.append("")

        # Build info
        build_date = self.version_info.get("build_date", "")
        build_number = self.version_info.get("build_number", "")
        commit_hash = self.version_info.get("commit_hash", "")

        if any([build_date, build_number, commit_hash]):
            info_lines.append("=== Build Information ===")
            if build_date:
                info_lines.append(f"Build Date: {build_date}")
            if build_number:
                info_lines.append(f"Build Number: {build_number}")
            if commit_hash:
                info_lines.append(f"Commit Hash: {commit_hash}")
            info_lines.append("")

        # System info
        import platform as plt
        import sys
        info_lines.append("=== System Information ===")
        info_lines.append(f"OS: {plt.system()} {plt.release()}")
        info_lines.append(f"Python: {sys.version.split()[0]}")

        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(info_lines))

    def set_version_info(self, version_info: Dict[str, Any]):
        """Update the version information displayed."""
        self.version_info = version_info
        # Recreate UI with new information
        # For simplicity, we'll just close and reopen
        # In a real implementation, you might want to update existing widgets
        pass


class VersionStatusWidget(QPushButton):
    """
    A status bar control that opens the version information dialog.

    This was a QLabel with a mousePressEvent handler. A label cannot take the
    keyboard focus, shows no focus ring, and a screen reader reports it as
    static text. Anything the user can act on must be a real control.
    """

    # 24 pixels is the smallest target a pointer can hit reliably.
    MINIMUM_HEIGHT = 24

    def __init__(self, version_info: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.version_info = version_info or {}
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(self.MINIMUM_HEIGHT)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(self.tr("Version information"))
        self.clicked.connect(self._show_version_info)
        self._update_display()

        # The hover colours come from the palette. A black overlay is
        # invisible on a dark theme. The focus rule is the visible focus
        # indicator a keyboard user needs.
        self.setStyleSheet(f"""
            QPushButton {{
                padding: 2px 8px;
                border: 1px solid transparent;
                border-radius: 3px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {surface_variant()};
                border-color: {outline()};
            }}
            QPushButton:focus {{
                border: 2px solid {interactive()};
            }}
        """)

    def _update_display(self):
        """Update the status display."""
        version = self.version_info.get("version", "Unknown")
        build_number = self.version_info.get("build_number", "")

        text = f"v{version}"
        if build_number:
            text += f" (Build {build_number})"

        self.setText(text)

        # Set tooltip with more info
        tooltip_lines = [f"Version: {version}"]

        build_date = self.version_info.get("build_date", "")
        if build_date:
            tooltip_lines.append(f"Build Date: {build_date}")

        commit_hash = self.version_info.get("commit_hash", "")
        if commit_hash:
            short_hash = commit_hash[:8] if len(
                commit_hash) > 8 else commit_hash
            tooltip_lines.append(f"Commit: {short_hash}")

        self.setToolTip("\n".join(tooltip_lines))

    def _show_version_info(self) -> None:
        """Show the version information dialog."""
        VersionInfoDialog(self.version_info, self).exec()

    def set_version_info(self, version_info: Dict[str, Any]):
        """Update the version information."""
        self.version_info = version_info
        self._update_display()


class AboutDialog(QDialog):
    """About dialog that incorporates version information."""

    def __init__(self, version_info: Optional[Dict[str, Any]] = None,
                 app_icon: Optional[QIcon] = None, parent=None):
        super().__init__(parent)
        self.version_info = version_info or {}
        self.app_icon = app_icon
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle(self.tr("About"))
        self.setModal(True)
        # A minimum, not a fixed size. A translated string is often 30 to 40
        # per cent longer than the English source, and the operating system
        # font size can be set to Large. A fixed size cuts both off.
        self.setMinimumSize(400, 300)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Header with icon and title
        header_layout = QHBoxLayout()

        # Icon
        if self.app_icon:
            icon_label = QLabel()
            pixmap = self.app_icon.pixmap(64, 64)
            icon_label.setPixmap(pixmap)
            icon_label.setAlignment(Qt.AlignCenter)
            header_layout.addWidget(icon_label)

        # Title and version
        title_layout = QVBoxLayout()

        product_name = self.version_info.get(
            "product_name", "OPAQUE Framework Application")
        title_label = QLabel(product_name)
        title_font = title_label.font()
        title_font.setPointSize(title_font.pointSize() + 4)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(title_label)

        version = self.version_info.get("version", "Unknown")
        version_label = QLabel(f"Version {version}")
        version_font = version_label.font()
        version_font.setPointSize(version_font.pointSize() + 1)
        version_label.setFont(version_font)
        version_label.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(version_label)

        header_layout.addLayout(title_layout)
        layout.addLayout(header_layout)

        # Description
        description = self.version_info.get("description", "")
        if description:
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(desc_label)

        # Copyright
        copyright_info = self.version_info.get("copyright", "")
        if copyright_info:
            copyright_label = QLabel(copyright_info)
            copyright_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(copyright_label)

        # Built with OPAQUE Framework
        framework_label = QLabel(self.tr("Built with OPAQUE Framework"))
        framework_font = framework_label.font()
        framework_font.setPointSize(framework_font.pointSize() - 1)
        framework_label.setFont(framework_font)
        framework_label.setAlignment(Qt.AlignCenter)
        self.framework_label_colour = muted_on_surface()
        framework_label.setStyleSheet(f"color: {self.framework_label_colour};")
        layout.addWidget(framework_label)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()

        version_info_button = QPushButton(self.tr("Version Info..."))
        version_info_button.clicked.connect(self._show_version_info)
        button_layout.addWidget(version_info_button)

        button_layout.addStretch()

        close_button = QPushButton(self.tr("Close"))
        close_button.clicked.connect(self.accept)
        close_button.setDefault(True)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _show_version_info(self):
        """Show detailed version information dialog."""
        dialog = VersionInfoDialog(self.version_info, self)
        dialog.exec()
