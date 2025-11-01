"""
Base builder class for OPAQUE framework executable creation.

@copyright 2025 Sandro Fadiga
Licensed under MIT License
"""

import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Optional, Union


class BuildError(Exception):
    """Exception raised when build process fails."""
    pass


class Builder(ABC):
    """Abstract base class for executable builders."""

    def __init__(self, work_dir: Optional[Union[str, Path]] = None):
        """
        Initialize builder.

        Args:
            work_dir: Working directory for build process. Defaults to current directory.
        """
        self.work_dir = Path(work_dir) if work_dir else Path.cwd()
        self.output_dir = self.work_dir / "dist" / "executables"
        self.build_dir = self.work_dir / "build"

    @abstractmethod
    def build(self, entry_point: Union[str, Path], **kwargs: Any) -> Path:
        """
        Build executable from entry point.

        Args:
            entry_point: Path to main Python file
            **kwargs: Builder-specific options

        Returns:
            Path to built executable

        Raises:
            BuildError: If build process fails
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if builder tool is available.

        Returns:
            True if builder can be used, False otherwise
        """
        pass

    def _run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess[str]:
        """
        Run command and handle errors.

        Args:
            cmd: Command to run
            cwd: Working directory for command

        Returns:
            Completed process

        Raises:
            BuildError: If command fails
        """
        cwd = cwd or self.work_dir

        try:
            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=cwd,
                check=True,
                capture_output=True,
                text=True
            )
            return result
        except subprocess.CalledProcessError as e:
            raise BuildError(
                f"Command failed: {' '.join(cmd)}\n"
                f"Exit code: {e.returncode}\n"
                f"Stderr: {e.stderr}\n"
                f"Stdout: {e.stdout}"
            ) from e
        except FileNotFoundError as e:
            raise BuildError(f"Command not found: {cmd[0]}") from e

    def _ensure_directories(self) -> None:
        """Ensure output and build directories exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.build_dir.mkdir(parents=True, exist_ok=True)

    def _find_pyside6_path(self) -> Optional[Path]:
        """Find PySide6 installation path."""
        try:
            import PySide6
            return Path(PySide6.__file__).parent
        except ImportError:
            return None

    def _get_common_excludes(self) -> List[str]:
        """Get common modules to exclude from build."""
        return [
            'tkinter',
            'matplotlib',
            'numpy',
            'pandas',
            'scipy',
            'IPython',
            'jupyter',
            'notebook',
            'pytest',
            'sphinx',
            'docutils'
        ]

    def _get_pyside6_includes(self) -> List[str]:
        """Get PySide6 modules that should be included."""
        return [
            'PySide6.QtCore',
            'PySide6.QtGui',
            'PySide6.QtWidgets',
            'PySide6.QtSvg',
            'PySide6.QtPrintSupport'
        ]

    def clean(self) -> None:
        """Clean build artifacts."""
        dirs_to_clean = [self.build_dir, self.output_dir]

        for dir_path in dirs_to_clean:
            if dir_path.exists():
                print(f"Cleaning {dir_path}")
                shutil.rmtree(dir_path)

    def get_executable_size(self, exe_path: Path) -> int:
        """
        Get size of executable file in bytes.

        Args:
            exe_path: Path to executable

        Returns:
            File size in bytes
        """
        if exe_path.exists():
            return exe_path.stat().st_size
        return 0

    def format_size(self, size_bytes: int) -> str:
        """
        Format file size in human readable format.

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted size string
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes = int(size_bytes / 1024)
        return f"{size_bytes:.1f} TB"
