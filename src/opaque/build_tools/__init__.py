"""
OPAQUE Framework Build Tools

This module provides utilities for building OPAQUE applications as standalone executables
using PyInstaller or Nuitka.

@copyright 2025 Sandro Fadiga
Licensed under MIT License
"""

from .builder import Builder, BuildError
from .pyinstaller_builder import PyInstallerBuilder
from .nuitka_builder import NuitkaBuilder

__all__ = ['Builder', 'BuildError', 'PyInstallerBuilder', 'NuitkaBuilder']

__version__ = '1.0.0'
