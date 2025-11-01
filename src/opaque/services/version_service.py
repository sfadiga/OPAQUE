"""
Version management service for OPAQUE Framework applications.

@copyright 2025 Sandro Fadiga
Licensed under MIT License
"""

import os
import importlib.util
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from .service import BaseService


class VersionManager(BaseService):
    """Service for managing application version information from multiple sources."""

    def __init__(self):
        super().__init__("version")
        self._cached_version: Optional[str] = None
        self._version_info: Dict[str, Any] = {}
        self._initialize()

    def _initialize(self):
        """Initialize version detection from available sources."""
        self._detect_version_info()

    def get_version(self) -> Optional[str]:
        """
        Get application version from the highest priority source.

        Priority order:
        1. Build-time injected _version module
        2. VERSION file in project root
        3. Environment variable APP_VERSION
        4. pyproject.toml version field
        5. None (fallback to configuration default)

        Returns:
            Version string or None if no version detected
        """
        if self._cached_version:
            return self._cached_version

        # Try build-time injected version first
        version = self._get_injected_version()
        if version:
            self._cached_version = version
            return version

        # Try VERSION file
        version = self._get_version_from_file()
        if version:
            self._cached_version = version
            return version

        # Try environment variable
        version = self._get_version_from_env()
        if version:
            self._cached_version = version
            return version

        # Try pyproject.toml
        version = self._get_version_from_pyproject()
        if version:
            self._cached_version = version
            return version

        return None

    def get_version_info(self) -> Dict[str, Any]:
        """
        Get comprehensive version information.

        Returns:
            Dictionary containing version, build date, commit hash, etc.
        """
        return self._version_info.copy()

    def get_build_date(self) -> Optional[str]:
        """Get build date if available."""
        return self._version_info.get("build_date")

    def get_build_number(self) -> Optional[str]:
        """Get build number if available."""
        return self._version_info.get("build_number")

    def get_commit_hash(self) -> Optional[str]:
        """Get git commit hash if available."""
        return self._version_info.get("commit_hash")

    def get_full_version_string(self) -> str:
        """
        Get a comprehensive version string including build info.

        Returns:
            Formatted version string like "1.2.3 (build 456, 2025-11-01, abc123)"
        """
        version = self.get_version()
        if not version:
            return "Unknown"

        parts = [version]

        build_info: List[str] = []
        if self._version_info.get("build_number"):
            build_info.append(f"build {self._version_info['build_number']}")

        if self._version_info.get("build_date"):
            build_info.append(str(self._version_info["build_date"]))

        if self._version_info.get("commit_hash"):
            commit = str(self._version_info["commit_hash"])[:7]  # Short hash
            build_info.append(commit)

        if build_info:
            parts.append(f"({', '.join(build_info)})")

        return " ".join(parts)

    def _detect_version_info(self):
        """Detect and cache version information from all sources."""
        # Try to get comprehensive info from injected version
        injected_info = self._get_injected_version_info()
        if injected_info:
            self._version_info.update(injected_info)

        # Add current timestamp if no build date
        if not self._version_info.get("build_date"):
            self._version_info["build_date"] = datetime.now().strftime(
                "%Y-%m-%d")

    def _get_injected_version(self) -> Optional[str]:
        """Get version from build-time injected _version module."""
        try:
            import _version  # type: ignore
            return getattr(_version, "__version__", None)
        except ImportError:
            pass

        # Try to find _version.py in current directory
        version_file = Path("_version.py")
        if version_file.exists():
            return self._load_version_from_module(version_file)

        return None

    def _get_injected_version_info(self) -> Dict[str, Any]:
        """Get comprehensive version info from injected module."""
        info: Dict[str, Any] = {}

        try:
            import _version  # type: ignore
            info["version"] = getattr(_version, "__version__", None)
            info["build_date"] = getattr(_version, "__build_date__", None)
            info["build_number"] = getattr(_version, "__build_number__", None)
            info["commit_hash"] = getattr(_version, "__commit_hash__", None)
            return info
        except ImportError:
            pass

        # Try to load from file
        version_file = Path("_version.py")
        if version_file.exists():
            try:
                spec = importlib.util.spec_from_file_location(
                    "_version", version_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    info["version"] = getattr(module, "__version__", None)
                    info["build_date"] = getattr(
                        module, "__build_date__", None)
                    info["build_number"] = getattr(
                        module, "__build_number__", None)
                    info["commit_hash"] = getattr(
                        module, "__commit_hash__", None)
                    return info
            except Exception:
                pass

        return {}

    def _load_version_from_module(self, module_path: Path) -> Optional[str]:
        """Load version from a Python module file."""
        try:
            spec = importlib.util.spec_from_file_location(
                "version_module", module_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return getattr(module, "__version__", None)
        except Exception:
            pass
        return None

    def _get_version_from_file(self) -> Optional[str]:
        """Get version from VERSION file."""
        for filename in ["VERSION", "VERSION.txt", "version", "version.txt"]:
            version_file = Path(filename)
            if version_file.exists():
                try:
                    version = version_file.read_text().strip()
                    if version:
                        return version
                except Exception:
                    continue
        return None

    def _get_version_from_env(self) -> Optional[str]:
        """Get version from environment variable."""
        return os.environ.get("APP_VERSION") or os.environ.get("APPLICATION_VERSION")

    def _get_version_from_pyproject(self) -> Optional[str]:
        """Get version from pyproject.toml file."""
        pyproject_file = Path("pyproject.toml")
        if pyproject_file.exists():
            try:
                content = pyproject_file.read_text()
                # Simple parsing - look for version = "x.y.z" line
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("version") and "=" in line:
                        # Extract version from 'version = "1.2.3"'
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            version_part = parts[1].strip()
                            # Remove quotes
                            if version_part.startswith('"') and version_part.endswith('"'):
                                return version_part[1:-1]
                            elif version_part.startswith("'") and version_part.endswith("'"):
                                return version_part[1:-1]
            except Exception:
                pass
        return None

    def set_version(self, version: str, **kwargs: Any) -> None:
        """
        Manually set version information (for testing or override).

        Args:
            version: Version string
            **kwargs: Additional version info (build_date, build_number, etc.)
        """
        self._cached_version = version
        self._version_info["version"] = version
        self._version_info.update(kwargs)

    def clear_cache(self) -> None:
        """Clear cached version information to force re-detection."""
        self._cached_version = None
        self._version_info.clear()
        self._initialize()
