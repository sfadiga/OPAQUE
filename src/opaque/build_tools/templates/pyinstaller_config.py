"""
PyInstaller build configuration template for OPAQUE applications.

This template provides a starting point for building OPAQUE framework
applications with PyInstaller. Customize the configuration as needed
for your specific application.

Usage:
    1. Copy this file to your project
    2. Modify the configuration variables below
    3. Run: pyinstaller pyinstaller_config.py

@copyright 2025 Sandro Fadiga
Licensed under MIT License
"""

# ===== BUILD CONFIGURATION =====

# Application entry point - REQUIRED
# Path to your main Python file that starts the application
from pathlib import Path
APP_ENTRY_POINT = "main.py"

# Application name - will be used for executable name
APP_NAME = "MyOpaqueApp"

# Application version
APP_VERSION = "1.0.0"

# Application description
APP_DESCRIPTION = "My OPAQUE Framework Application"

# Application icon (optional)
# Path to .ico file on Windows, .icns on macOS, .png on Linux
APP_ICON = None  # "assets/icon.ico"

# ===== BUILD OPTIONS =====

# Create single file executable (True) or directory distribution (False)
ONEFILE = True

# Show console window (useful for debugging)
CONSOLE = False

# Enable debug mode (larger executable but better error messages)
DEBUG = False

# Use UPX compression (requires UPX to be installed)
USE_UPX = False

# ===== ADVANCED OPTIONS =====

# Additional data files to include
# Format: [(source, destination), ...]
# Example: [("config.json", "."), ("assets/", "assets/")]
ADD_DATA = [
    # Add your data files here
]

# Hidden imports (modules that PyInstaller might miss)
# Add any modules that are imported dynamically
HIDDEN_IMPORTS = [
    # OPAQUE framework modules (usually auto-detected)
    # Add additional imports if needed
]

# Modules to exclude (reduce executable size)
EXCLUDE_MODULES = [
    # Common modules to exclude for smaller size
    "tkinter",
    "matplotlib",
    "scipy",
    "pandas",
    "numpy",
    "PIL",
    # Add modules you don't need
]

# PyInstaller paths (usually auto-detected)
PATHS = []

# Runtime hooks (advanced users only)
RUNTIME_HOOKS = []

# ===== IMPLEMENTATION - DO NOT MODIFY BELOW THIS LINE =====
# Note: Analysis, PYZ, EXE, COLLECT are PyInstaller classes available when running this spec file


# Convert relative paths to absolute
script_dir = Path(__file__).parent
if not Path(APP_ENTRY_POINT).is_absolute():
    entry_point = script_dir / APP_ENTRY_POINT
else:
    entry_point = Path(APP_ENTRY_POINT)

# Build analysis
a = Analysis(
    [str(entry_point)],
    pathex=PATHS,
    binaries=[],
    datas=ADD_DATA,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=RUNTIME_HOOKS,
    excludes=EXCLUDE_MODULES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Remove duplicate files
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Build executable
if ONEFILE:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name=APP_NAME,
        debug=DEBUG,
        bootloader_ignore_signals=False,
        strip=False,
        upx=USE_UPX,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=CONSOLE,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=APP_ICON,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=APP_NAME,
        debug=DEBUG,
        bootloader_ignore_signals=False,
        strip=False,
        upx=USE_UPX,
        console=CONSOLE,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=APP_ICON,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=USE_UPX,
        upx_exclude=[],
        name=APP_NAME,
    )
