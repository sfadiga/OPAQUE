"""
Nuitka builder for OPAQUE framework applications.

@copyright 2025 Sandro Fadiga
Licensed under MIT License
"""

import platform
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .builder import Builder, BuildError


class NuitkaBuilder(Builder):
    """Builder using Nuitka to create executables."""

    def is_available(self) -> bool:
        """Check if Nuitka is available."""
        return shutil.which("nuitka") is not None

    def build(self, entry_point: Union[str, Path], **kwargs: Any) -> Path:
        """
        Build executable using Nuitka.

        Args:
            entry_point: Path to main Python file
            **kwargs: Nuitka options:
                - standalone (bool): Create standalone executable (default: True)
                - onefile (bool): Create single executable file
                - console (bool): Show console window (default: False for GUI apps) 
                - name (str): Name for the executable
                - icon (str): Path to icon file
                - output_dir (str): Output directory
                - optimization (str): Optimization level ('0', '1', '2')
                - include_data_files (List[str]): Data files to include
                - include_package (List[str]): Packages to include
                - exclude_module (List[str]): Modules to exclude
                - follow_imports (bool): Follow all imports
                - plugin_enable (List[str]): Nuitka plugins to enable
                - debug (bool): Enable debug mode
                - lto (bool): Enable Link Time Optimization
                - jobs (int): Number of parallel compilation jobs

        Returns:
            Path to built executable

        Raises:
            BuildError: If build process fails
        """
        if not self.is_available():
            raise BuildError(
                "Nuitka is not available. Install with: pip install nuitka")

        entry_path = Path(entry_point)
        if not entry_path.exists():
            raise BuildError(f"Entry point not found: {entry_path}")

        self._ensure_directories()

        # Build command
        cmd = ["nuitka"]

        # Basic mode
        if kwargs.get("standalone", True):
            cmd.append("--standalone")
        else:
            cmd.append("--module")

        # Single file mode
        if kwargs.get("onefile", False):
            cmd.append("--onefile")

        # Console/GUI mode
        if not kwargs.get("console", False):
            if platform.system() == "Windows":
                cmd.append("--windows-disable-console")
            else:
                cmd.append("--disable-console")

        # Output directory
        cmd.extend(["--output-dir", str(self.output_dir)])

        # Name
        name = kwargs.get("name")
        if name:
            cmd.extend(["--output-filename", name])

        # Icon
        icon = kwargs.get("icon")
        if icon and Path(icon).exists():
            if platform.system() == "Windows":
                cmd.extend(["--windows-icon-from-ico", str(icon)])
            elif platform.system() == "Darwin":
                cmd.extend(["--macos-app-icon", str(icon)])

        # Optimization
        optimization = kwargs.get("optimization", "1")
        if optimization in ["0", "1", "2"]:
            cmd.extend([f"--optimization-level={optimization}"])

        # PySide6 plugin
        pyside6_path = self._find_pyside6_path()
        if pyside6_path:
            cmd.append("--enable-plugin=pyside6")

        # Additional plugins
        for plugin in kwargs.get("plugin_enable", []):
            cmd.extend(["--enable-plugin", plugin])

        # Include packages
        for package in kwargs.get("include_package", []):
            cmd.extend(["--include-package", package])

        # Exclude modules
        exclude_modules = self._get_common_excludes() + kwargs.get("exclude_module", [])
        for module in exclude_modules:
            cmd.extend(["--nofollow-import-to", module])

        # Data files
        for data_file in kwargs.get("include_data_files", []):
            cmd.extend(["--include-data-files", data_file])

        # Follow imports
        if kwargs.get("follow_imports", True):
            cmd.append("--follow-imports")
        else:
            cmd.append("--nofollow-imports")

        # Performance options
        jobs = kwargs.get("jobs", 0)
        if jobs > 0:
            cmd.extend([f"--jobs={jobs}"])

        if kwargs.get("lto", False):
            cmd.append("--lto=yes")

        # Version info for Windows
        if platform.system() == "Windows":
            version_info = kwargs.get("version_info")
            if version_info:
                self._add_windows_version_args(cmd, version_info)

        # Debug mode
        if kwargs.get("debug", False):
            cmd.append("--debug")
        else:
            cmd.append("--no-progressbar")

        # Remove build files
        cmd.append("--remove-output")

        # Create version module if needed
        version_module_path = self._create_version_module(
            kwargs.get("version_info"))
        if version_module_path:
            # Include the version module directory
            cmd.extend(["--include-data-files",
                       f"{version_module_path}=_opaque_version.py"])

        # Entry point
        cmd.append(str(entry_path))

        # Run Nuitka
        try:
            result = self._run_command(cmd)
            print("Nuitka output:")
            print(result.stdout)

            # Find the executable
            exe_path = self._find_executable(
                entry_path.stem, name, kwargs.get("onefile", False))

            if exe_path and exe_path.exists():
                size = self.get_executable_size(exe_path)
                print(f"Build successful! Executable: {exe_path}")
                print(f"Size: {self.format_size(size)}")
                return exe_path
            else:
                raise BuildError("Executable not found after build")

        except BuildError:
            raise
        except Exception as e:
            raise BuildError(f"Nuitka build failed: {str(e)}") from e

    def _find_executable(self, default_name: str, custom_name: Optional[str] = None, onefile: bool = False) -> Optional[Path]:
        """Find the built executable."""
        name = custom_name or default_name

        if onefile:
            # Single file executable
            exe_name = f"{name}.exe" if platform.system(
            ) == "Windows" else name
            return self.output_dir / exe_name
        else:
            # Standalone distribution
            # Nuitka creates a directory with the app name
            exe_dir = self.output_dir / f"{default_name}.dist"
            exe_name = f"{name}.exe" if platform.system(
            ) == "Windows" else name
            exe_path = exe_dir / exe_name

            # If custom name was used, also check for that
            if custom_name and custom_name != default_name:
                alt_exe_name = f"{custom_name}.exe" if platform.system(
                ) == "Windows" else custom_name
                alt_exe_path = exe_dir / alt_exe_name
                if alt_exe_path.exists():
                    return alt_exe_path

            return exe_path if exe_path.exists() else None

    def get_nuitka_version(self) -> Optional[str]:
        """Get Nuitka version."""
        try:
            result = self._run_command(["nuitka", "--version"])
            return result.stdout.strip()
        except BuildError:
            return None

    def list_plugins(self) -> List[str]:
        """List available Nuitka plugins."""
        try:
            result = self._run_command(["nuitka", "--plugin-list"])
            lines = result.stdout.split('\n')
            plugins: List[str] = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('Available plugins:'):
                    # Extract plugin name (usually the first word)
                    plugin_name = line.split()[0] if line.split() else ""
                    if plugin_name and not plugin_name.startswith('-'):
                        plugins.append(plugin_name)
            return plugins
        except BuildError:
            return []

    def create_config_file(self, entry_point: Union[str, Path], **kwargs: Any) -> Path:
        """
        Create a Nuitka configuration file for reproducible builds.

        Args:
            entry_point: Path to main Python file
            **kwargs: Same options as build method

        Returns:
            Path to created config file
        """
        entry_path = Path(entry_point)
        name = kwargs.get("name", entry_path.stem)
        config_path = self.build_dir / f"{name}-nuitka.cfg"

        self._ensure_directories()

        # Generate config content
        config_content = self._generate_config_content(**kwargs)

        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)

        print(f"Nuitka config file created: {config_path}")
        return config_path

    def _generate_config_content(self, **kwargs: Any) -> str:
        """Generate Nuitka configuration file content."""
        lines = [
            "# Nuitka Configuration File",
            "# Generated by OPAQUE Framework Build Tools",
            "",
        ]

        # Basic options
        if kwargs.get("standalone", True):
            lines.append("--standalone")

        if kwargs.get("onefile", False):
            lines.append("--onefile")

        if not kwargs.get("console", False):
            if platform.system() == "Windows":
                lines.append("--windows-disable-console")
            else:
                lines.append("--disable-console")

        # Output
        lines.append(f"--output-dir={self.output_dir}")

        name = kwargs.get("name")
        if name:
            lines.append(f"--output-filename={name}")

        # Icon
        icon = kwargs.get("icon")
        if icon and Path(icon).exists():
            if platform.system() == "Windows":
                lines.append(f"--windows-icon-from-ico={icon}")
            elif platform.system() == "Darwin":
                lines.append(f"--macos-app-icon={icon}")

        # Optimization
        optimization = kwargs.get("optimization", "1")
        if optimization in ["0", "1", "2"]:
            lines.append(f"--optimization-level={optimization}")

        # PySide6
        if self._find_pyside6_path():
            lines.append("--enable-plugin=pyside6")

        # Additional plugins
        for plugin in kwargs.get("plugin_enable", []):
            lines.append(f"--enable-plugin={plugin}")

        # Include packages
        for package in kwargs.get("include_package", []):
            lines.append(f"--include-package={package}")

        # Exclude modules
        exclude_modules = self._get_common_excludes() + kwargs.get("exclude_module", [])
        for module in exclude_modules:
            lines.append(f"--nofollow-import-to={module}")

        # Data files
        for data_file in kwargs.get("include_data_files", []):
            lines.append(f"--include-data-files={data_file}")

        # Performance
        jobs = kwargs.get("jobs", 0)
        if jobs > 0:
            lines.append(f"--jobs={jobs}")

        if kwargs.get("lto", False):
            lines.append("--lto=yes")

        # Other options
        if not kwargs.get("debug", False):
            lines.append("--no-progressbar")

        lines.append("--remove-output")

        return '\n'.join(lines) + '\n'

    def build_from_config(self, config_file: Union[str, Path], entry_point: Union[str, Path]) -> Path:
        """
        Build executable from existing config file.

        Args:
            config_file: Path to Nuitka config file
            entry_point: Path to main Python file

        Returns:
            Path to built executable
        """
        config_path = Path(config_file)
        entry_path = Path(entry_point)

        if not config_path.exists():
            raise BuildError(f"Config file not found: {config_path}")
        if not entry_path.exists():
            raise BuildError(f"Entry point not found: {entry_path}")

        cmd = ["nuitka", f"@{config_path}", str(entry_path)]

        try:
            result = self._run_command(cmd)
            print("Nuitka output:")
            print(result.stdout)

            # Try to find the executable
            name = entry_path.stem
            for onefile in [True, False]:
                exe_path = self._find_executable(name, None, onefile)
                if exe_path and exe_path.exists():
                    size = self.get_executable_size(exe_path)
                    print(f"Build successful! Executable: {exe_path}")
                    print(f"Size: {self.format_size(size)}")
                    return exe_path

            raise BuildError("Executable not found after build")

        except BuildError:
            raise
        except Exception as e:
            raise BuildError(
                f"Nuitka build from config failed: {str(e)}") from e

    def _add_windows_version_args(self, cmd: List[str], version_info: Dict[str, Any]) -> None:
        """Add Windows version information arguments to Nuitka command."""
        version = version_info.get("version", "0.0.1")
        build_number = version_info.get("build_number", "0")

        # Parse version string to get numeric components
        version_parts = version.replace("-", ".").replace("+", ".").split(".")
        major = int(version_parts[0]) if len(
            version_parts) > 0 and version_parts[0].isdigit() else 0
        minor = int(version_parts[1]) if len(
            version_parts) > 1 and version_parts[1].isdigit() else 0
        micro = int(version_parts[2]) if len(
            version_parts) > 2 and version_parts[2].isdigit() else 0
        build = int(build_number) if build_number.isdigit() else 0

        # Add version arguments
        cmd.extend([f"--windows-file-version={major}.{minor}.{micro}.{build}"])
        cmd.extend([f"--windows-product-version={version}"])

        # Add other version info
        company = version_info.get("company", "OPAQUE Framework Application")
        description = version_info.get(
            "description", "OPAQUE Framework Application")
        copyright_info = version_info.get("copyright", "Copyright © 2025")
        product_name = version_info.get(
            "product_name", "OPAQUE Framework Application")

        cmd.extend([f"--windows-company-name={company}"])
        cmd.extend([f"--windows-file-description={description}"])
        cmd.extend([f"--windows-product-name={product_name}"])

        # Note: Nuitka doesn't have a direct copyright argument,
        # but we store it in the version module for runtime access

    def _create_version_module(self, version_info: Optional[Dict[str, Any]]) -> Optional[Path]:
        """Create a version module file that can be imported at runtime."""
        if not version_info:
            return None

        version = version_info.get("version", "0.0.1")
        build_date = version_info.get("build_date", "")
        build_number = version_info.get("build_number", "")
        commit_hash = version_info.get("commit_hash", "")

        version_module_content = f'''"""
Version information for OPAQUE Framework application.
Generated by OPAQUE Framework Build Tools.
"""

__version__ = "{version}"
__build_date__ = "{build_date}"
__build_number__ = "{build_number}"
__commit_hash__ = "{commit_hash}"

# Additional version info
VERSION_INFO = {{
    "version": "{version}",
    "build_date": "{build_date}",
    "build_number": "{build_number}",
    "commit_hash": "{commit_hash}",
    "company": "{version_info.get('company', '')}",
    "description": "{version_info.get('description', '')}",
    "copyright": "{version_info.get('copyright', '')}",
    "product_name": "{version_info.get('product_name', '')}"
}}

def get_version_info():
    """Get version information dictionary."""
    return VERSION_INFO.copy()

def get_version():
    """Get version string."""
    return __version__

def get_build_info():
    """Get build information as formatted string."""
    info = []
    if __version__:
        info.append(f"Version: {{__version__}}")
    if __build_date__:
        info.append(f"Built: {{__build_date__}}")
    if __build_number__:
        info.append(f"Build: {{__build_number__}}")
    if __commit_hash__:
        info.append(f"Commit: {{__commit_hash__[:8]}}")
    return " | ".join(info) if info else "No build information available"
'''

        version_module_path = self.build_dir / "_opaque_version.py"
        with open(version_module_path, 'w', encoding='utf-8') as f:
            f.write(version_module_content)

        return version_module_path
