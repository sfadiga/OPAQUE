"""
Nuitka builder for OPAQUE framework applications.

@copyright 2025 Sandro Fadiga
Licensed under MIT License
"""

import logging
import platform
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .builder import Builder, BuildError
from .config import BuildConfig

logger = logging.getLogger(__name__)


class NuitkaBuilder(Builder):
    """Builder using Nuitka to create executables."""

    def is_available(self) -> bool:
        """Check if Nuitka is available."""
        return shutil.which("nuitka") is not None

    def build(
            self,
            entry_point: Union[str, Path],
            config: BuildConfig,
    ) -> Path:
        """
        Build one executable with Nuitka.

        Args:
            entry_point: The .py file that starts the application.
            config: Every build option. See BuildConfig.

        Returns:
            The path of the executable that was produced.

        Raises:
            BuildError: When Nuitka is not installed, the entry point does
                not exist, or Nuitka reports a failure.
        """
        if not self.is_available():
            raise BuildError(
                "Nuitka is not installed. Install the build extra: "
                "uv sync --extra build")

        entry_path = Path(entry_point)
        self._ensure_directories()
        command = self.build_command(entry_point, config)
        result = self._run_command(command)
        logger.info("Nuitka output:\n%s", result.stdout)

        executable = self._find_executable(
            entry_path.stem, config.name, config.onefile)
        if executable is None or not executable.exists():
            raise BuildError(
                f"Nuitka reported success but no executable named "
                f"{config.name} was found under {self.output_dir}.")

        size = self.get_executable_size(executable)
        logger.info("Build successful! Executable: %s (%s)",
                     executable, self.format_size(size))
        return executable

    def build_command(
            self,
            entry_point: Union[str, Path],
            config: BuildConfig,
    ) -> List[str]:
        """
        Return the Nuitka command line for one build.

        This is separate from build() so a test can check every option
        without installing Nuitka and without waiting minutes for a real
        compile.

        Args:
            entry_point: The .py file that starts the application.
            config: Every build option. The fields marked pyinstaller in
                BuildConfig are ignored here.

        Returns:
            The command, as a list of arguments, with the entry point last.

        Raises:
            BuildError: When the entry point does not exist.
        """
        entry_path = Path(entry_point)
        if not entry_path.exists():
            raise BuildError(f"Entry point not found: {entry_path}")

        command: List[str] = [
            sys.executable, "-m", "nuitka",
            "--assume-yes-for-downloads",
            f"--output-dir={self.output_dir}",
            f"--output-filename={config.name}{self._executable_suffix()}",
        ]

        if config.standalone:
            command.append("--standalone")
        else:
            command.append("--module")

        if config.onefile:
            command.append("--onefile")

        if config.follow_imports:
            command.append("--follow-imports")
        else:
            command.append("--nofollow-imports")

        # `--windows-console-mode` is a Windows-only flag, and
        # `--disable-console` is the equivalent everywhere else. Guarded
        # exactly as the code they replace guarded them.
        if platform.system() == "Windows":
            command.append(
                "--windows-console-mode=force" if config.console
                else "--windows-console-mode=disable")
        elif not config.console:
            command.append("--disable-console")

        if config.debug:
            command.append("--debug")
        else:
            command.append("--no-progressbar")

        # `--windows-icon-from-ico` and `--macos-app-icon` are each
        # platform-specific, guarded exactly as the code they replace
        # guarded them.
        if config.icon:
            if platform.system() == "Windows":
                command.append(f"--windows-icon-from-ico={config.icon}")
            elif platform.system() == "Darwin":
                command.append(f"--macos-app-icon={config.icon}")

        # PySide6 always needs its own plug-in, so the caller never has to
        # remember it.
        for plugin in ["pyside6"] + config.nuitka_plugins:
            command.append(f"--enable-plugin={plugin}")

        for package in config.include_packages:
            command.append(f"--include-package={package}")

        for module in config.hidden_imports:
            command.append(f"--include-module={module}")

        for module in config.exclude_modules + self._get_common_excludes():
            command.append(f"--nofollow-import-to={module}")

        for entry in config.data_files:
            command.append(f"--include-data-files={entry}")

        if config.jobs > 1:
            command.append(f"--jobs={config.jobs}")
        elif config.jobs == 1:
            command.append("--jobs=1")

        if config.lto:
            command.append("--lto=yes")

        # BuildConfig.optimization is the Python optimisation level (assert
        # and docstring stripping), not Nuitka's own compiler optimisation
        # level, so it is spelled as a Python flag.
        if config.optimization:
            command.append("--python-flag=" + "O" * config.optimization)

        # `_add_windows_version_args` writes Windows resource-version flags,
        # so it is guarded exactly as the code it replaces guarded it: only
        # on Windows, and only when there is version information to write.
        if platform.system() == "Windows" and config.version_info:
            self._add_windows_version_args(command, config.version_info)

        command.append("--remove-output")

        version_module_path = self._create_version_module(
            config.version_info)
        if version_module_path:
            command.append(
                f"--include-data-files={version_module_path}="
                f"_opaque_version.py")

        command.append(str(entry_path))
        return command

    @staticmethod
    def _executable_suffix() -> str:
        """Return the executable file extension for this platform."""
        return ".exe" if platform.system() == "Windows" else ""

    def _find_executable(
            self, default_name: str, custom_name: Optional[str] = None,
            onefile: bool = False,
    ) -> Optional[Path]:
        """Find the built executable."""
        name = custom_name or default_name

        if onefile:
            # Single file executable
            exe_name = f"{name}.exe" if platform.system(
            ) == "Windows" else name
            return self.output_dir / exe_name

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

    def create_config_file(
            self,
            entry_point: Union[str, Path],  # pylint: disable=unused-argument
            config: BuildConfig,
    ) -> Path:
        """
        Create a Nuitka configuration file for reproducible builds.

        Args:
            entry_point: The .py file that starts the application. Not read
                here; kept so this method's signature matches build() and
                build_command(), which do read it.
            config: Every build option.

        Returns:
            Path to created config file
        """
        config_path = self.build_dir / f"{config.name}-nuitka.cfg"

        self._ensure_directories()

        config_content = self._generate_config_content(config)

        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)

        logger.info("Nuitka config file created: %s", config_path)
        return config_path

    def _generate_config_content(self, config: BuildConfig) -> str:
        """Generate Nuitka configuration file content."""
        lines = [
            "# Nuitka Configuration File",
            "# Generated by OPAQUE Framework Build Tools",
            "",
        ]

        if config.standalone:
            lines.append("--standalone")

        if config.onefile:
            lines.append("--onefile")

        if config.follow_imports:
            lines.append("--follow-imports")
        else:
            lines.append("--nofollow-imports")

        # `--windows-console-mode` is a Windows-only flag, and
        # `--disable-console` is the equivalent everywhere else. Guarded
        # exactly as the code they replace guarded them.
        if platform.system() == "Windows":
            lines.append(
                "--windows-console-mode=force" if config.console
                else "--windows-console-mode=disable")
        elif not config.console:
            lines.append("--disable-console")

        if config.debug:
            lines.append("--debug")
        else:
            lines.append("--no-progressbar")

        lines.append(f"--output-dir={self.output_dir}")
        lines.append(
            f"--output-filename={config.name}{self._executable_suffix()}")

        # `--windows-icon-from-ico` and `--macos-app-icon` are each
        # platform-specific, guarded exactly as the code they replace
        # guarded them.
        if config.icon:
            if platform.system() == "Windows":
                lines.append(f"--windows-icon-from-ico={config.icon}")
            elif platform.system() == "Darwin":
                lines.append(f"--macos-app-icon={config.icon}")

        # PySide6 always needs its own plug-in, so the caller never has to
        # remember it.
        for plugin in ["pyside6"] + config.nuitka_plugins:
            lines.append(f"--enable-plugin={plugin}")

        for package in config.include_packages:
            lines.append(f"--include-package={package}")

        for module in config.hidden_imports:
            lines.append(f"--include-module={module}")

        for module in config.exclude_modules + self._get_common_excludes():
            lines.append(f"--nofollow-import-to={module}")

        for data_file in config.data_files:
            lines.append(f"--include-data-files={data_file}")

        if config.jobs > 1:
            lines.append(f"--jobs={config.jobs}")
        elif config.jobs == 1:
            lines.append("--jobs=1")

        if config.lto:
            lines.append("--lto=yes")

        # BuildConfig.optimization is the Python optimisation level (assert
        # and docstring stripping), not Nuitka's own compiler optimisation
        # level, so it is spelled as a Python flag.
        if config.optimization:
            lines.append("--python-flag=" + "O" * config.optimization)

        # `_add_windows_version_args` writes Windows resource-version flags,
        # so it is guarded exactly as the code it replaces guarded it: only
        # on Windows, and only when there is version information to write.
        if platform.system() == "Windows" and config.version_info:
            args: List[str] = []
            self._add_windows_version_args(args, config.version_info)
            lines.extend(args)

        lines.append("--remove-output")

        version_module_path = self._create_version_module(
            config.version_info)
        if version_module_path:
            lines.append(
                f"--include-data-files={version_module_path}="
                f"_opaque_version.py")

        return '\n'.join(lines) + '\n'

    def build_from_config(
            self, config_file: Union[str, Path],
            entry_point: Union[str, Path],
    ) -> Path:
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
            logger.info("Nuitka output:\n%s", result.stdout)

            # Try to find the executable
            name = entry_path.stem
            for onefile in [True, False]:
                exe_path = self._find_executable(name, None, onefile)
                if exe_path and exe_path.exists():
                    size = self.get_executable_size(exe_path)
                    logger.info("Build successful! Executable: %s (%s)",
                                 exe_path, self.format_size(size))
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
        product_name = version_info.get(
            "product_name", "OPAQUE Framework Application")

        cmd.extend([f"--windows-company-name={company}"])
        cmd.extend([f"--windows-file-description={description}"])
        cmd.extend([f"--windows-product-name={product_name}"])

        # Note: Nuitka doesn't have a direct copyright argument. The
        # version module _create_version_module() writes separately does
        # carry it, for runtime access.

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
