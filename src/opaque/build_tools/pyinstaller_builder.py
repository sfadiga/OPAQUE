"""
PyInstaller builder for OPAQUE framework applications.

@copyright 2025 Sandro Fadiga
Licensed under MIT License
"""

import platform
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .builder import Builder, BuildError


class PyInstallerBuilder(Builder):
    """Builder using PyInstaller to create executables."""

    def is_available(self) -> bool:
        """Check if PyInstaller is available."""
        return shutil.which("pyinstaller") is not None

    def build(self, entry_point: Union[str, Path], **kwargs: Any) -> Path:
        """
        Build executable using PyInstaller.

        Args:
            entry_point: Path to main Python file
            **kwargs: PyInstaller options:
                - onefile (bool): Create single executable file
                - console (bool): Show console window (default: False for GUI apps)
                - name (str): Name for the executable
                - icon (str): Path to icon file
                - distpath (str): Output directory
                - workpath (str): Build directory
                - add_data (List[str]): Additional data files to include
                - hidden_imports (List[str]): Modules to force import
                - exclude_modules (List[str]): Modules to exclude
                - upx (bool): Use UPX compression
                - debug (bool): Enable debug mode

        Returns:
            Path to built executable

        Raises:
            BuildError: If build process fails
        """
        if not self.is_available():
            raise BuildError(
                "PyInstaller is not available. Install with: pip install pyinstaller")

        entry_path = Path(entry_point)
        if not entry_path.exists():
            raise BuildError(f"Entry point not found: {entry_path}")

        self._ensure_directories()

        # Build command
        cmd = ["pyinstaller"]

        # Basic options
        if kwargs.get("onefile", False):
            cmd.append("--onefile")
        else:
            cmd.append("--onedir")

        # Console/GUI mode
        if not kwargs.get("console", False):
            cmd.append("--noconsole")

        # Name
        name = kwargs.get("name", entry_path.stem)
        cmd.extend(["--name", name])

        # Directories
        cmd.extend(["--distpath", str(self.output_dir)])
        cmd.extend(["--workpath", str(self.build_dir)])
        cmd.extend(["--specpath", str(self.build_dir)])

        # Icon
        icon = kwargs.get("icon")
        if icon and Path(icon).exists():
            cmd.extend(["--icon", str(icon)])

        # Clean previous builds
        cmd.append("--clean")

        # PySide6 specific options
        pyside6_path = self._find_pyside6_path()
        if pyside6_path:
            cmd.extend(
                ["--add-binary", f"{pyside6_path}/*{self._get_lib_extension()};PySide6"])

        # Hidden imports for PySide6
        for module in self._get_pyside6_includes():
            cmd.extend(["--hidden-import", module])

        # Additional hidden imports
        for module in kwargs.get("hidden_imports", []):
            cmd.extend(["--hidden-import", module])

        # Exclude modules
        exclude_modules = self._get_common_excludes() + kwargs.get("exclude_modules", [])
        for module in exclude_modules:
            cmd.extend(["--exclude-module", module])

        # Additional data files
        for data in kwargs.get("add_data", []):
            cmd.extend(["--add-data", data])

        # UPX compression
        if kwargs.get("upx", False):
            cmd.append("--upx-dir")

        # Debug mode
        if kwargs.get("debug", False):
            cmd.append("--debug=all")
        else:
            cmd.append("--log-level=WARN")

        # Version info
        version_info_file = self._create_version_info_file(
            kwargs.get("version_info"))
        if version_info_file:
            cmd.extend(["--version-file", str(version_info_file)])

        # Entry point
        cmd.append(str(entry_path))

        # Run PyInstaller
        try:
            result = self._run_command(cmd)
            print("PyInstaller output:")
            print(result.stdout)

            # Find the executable
            exe_path = self._find_executable(
                name, kwargs.get("onefile", False))

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
            raise BuildError(f"PyInstaller build failed: {str(e)}") from e

    def _find_executable(self, name: str, onefile: bool) -> Optional[Path]:
        """Find the built executable."""
        if onefile:
            # Single file executable
            exe_name = f"{name}.exe" if platform.system(
            ) == "Windows" else name
            return self.output_dir / exe_name
        else:
            # Directory distribution
            exe_dir = self.output_dir / name
            exe_name = f"{name}.exe" if platform.system(
            ) == "Windows" else name
            return exe_dir / exe_name

    def _get_lib_extension(self) -> str:
        """Get library file extension for current platform."""
        system = platform.system()
        if system == "Windows":
            return ".dll"
        elif system == "Darwin":
            return ".dylib"
        else:
            return ".so"

    def create_spec_file(self, entry_point: Union[str, Path], **kwargs: Any) -> Path:
        """
        Create a PyInstaller spec file for advanced customization.

        Args:
            entry_point: Path to main Python file
            **kwargs: Same options as build method

        Returns:
            Path to created spec file
        """
        entry_path = Path(entry_point)
        name = kwargs.get("name", entry_path.stem)
        spec_path = self.build_dir / f"{name}.spec"

        self._ensure_directories()

        # Generate spec file content
        spec_content = self._generate_spec_content(entry_path, **kwargs)

        with open(spec_path, 'w', encoding='utf-8') as f:
            f.write(spec_content)

        print(f"Spec file created: {spec_path}")
        return spec_path

    def _generate_spec_content(self, entry_path: Path, **kwargs: Any) -> str:
        """Generate PyInstaller spec file content."""
        name = kwargs.get("name", entry_path.stem)
        onefile = kwargs.get("onefile", False)
        console = kwargs.get("console", False)

        # Build data files list
        data_files: List[str] = []
        for data in kwargs.get("add_data", []):
            data_files.append(f"('{data}', '.')")

        # Build hidden imports list
        hidden_imports = self._get_pyside6_includes() + kwargs.get("hidden_imports", [])
        hidden_imports_str = ", ".join([f"'{imp}'" for imp in hidden_imports])

        # Build excludes list
        excludes = self._get_common_excludes() + kwargs.get("exclude_modules", [])
        excludes_str = ", ".join([f"'{exc}'" for exc in excludes])

        spec_template = f'''# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for {name}
# Generated by OPAQUE Framework Build Tools

block_cipher = None

a = Analysis(
    ['{entry_path}'],
    pathex=[],
    binaries=[],
    datas=[{', '.join(data_files)}],
    hiddenimports=[{hidden_imports_str}],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[{excludes_str}],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

{"exe = EXE(" if onefile else "exe = EXE("}
    pyz,
    a.scripts,
    {'a.binaries,' if onefile else '[],'}
    {'a.zipfiles,' if onefile else '[],'}
    {'a.datas,' if onefile else '[],'}
    name='{name}',
    debug={str(kwargs.get("debug", False)).lower()},
    bootloader_ignore_signals=False,
    strip=False,
    upx={str(kwargs.get("upx", False)).lower()},
    upx_exclude=[],
    runtime_tmpdir=None,
    console={str(console).lower()},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    {f"icon='{kwargs.get('icon', '')}'," if kwargs.get("icon") else ""}
)

{'' if onefile else f'''


coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx={str(kwargs.get("upx", False)).lower()},
    upx_exclude=[],
    name='{name}',
)
'''}
'''
        return spec_template

    def build_from_spec(self, spec_file: Union[str, Path]) -> Path:
        """
        Build executable from existing spec file.
        
        Args:
            spec_file: Path to PyInstaller spec file
            
        Returns:
            Path to built executable
        """
        spec_path = Path(spec_file)
        if not spec_path.exists():
            raise BuildError(f"Spec file not found: {spec_path}")
            
        cmd = ["pyinstaller", "--clean", str(spec_path)]
        
        try:
            result = self._run_command(cmd)
            print("PyInstaller output:")
            print(result.stdout)
            
            # Try to find the executable
            name = spec_path.stem
            for onefile in [True, False]:
                exe_path = self._find_executable(name, onefile)
                if exe_path and exe_path.exists():
                    size = self.get_executable_size(exe_path)
                    print(f"Build successful! Executable: {exe_path}")
                    print(f"Size: {self.format_size(size)}")
                    return exe_path
                    
            raise BuildError("Executable not found after build")
            
        except BuildError:
            raise
        except Exception as e:
            raise BuildError(f"PyInstaller build from spec failed: {str(e)}") from e

    def _create_version_info_file(self, version_info: Optional[Dict[str, Any]]) -> Optional[Path]:
        """Create version info file for Windows executables."""
        if not version_info or platform.system() != "Windows":
            return None

        version = version_info.get("version", "0.0.1")
        build_number = version_info.get("build_number", "0")
        
        # Parse version string to get numeric components
        version_parts = version.replace("-", ".").replace("+", ".").split(".")
        major = int(version_parts[0]) if len(version_parts) > 0 and version_parts[0].isdigit() else 0
        minor = int(version_parts[1]) if len(version_parts) > 1 and version_parts[1].isdigit() else 0
        micro = int(version_parts[2]) if len(version_parts) > 2 and version_parts[2].isdigit() else 0
        build = int(build_number) if build_number.isdigit() else 0

        company = version_info.get("company", "OPAQUE Framework Application")
        description = version_info.get("description", "OPAQUE Framework Application")
        internal_name = version_info.get("internal_name", "app.exe")
        copyright_info = version_info.get("copyright", "Copyright © 2025")
        original_filename = version_info.get("original_filename", "app.exe")
        product_name = version_info.get("product_name", "OPAQUE Framework Application")

        version_file_content = f'''# UTF-8
#
# Version information for Windows executable
# Generated by OPAQUE Framework Build Tools
#

VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {micro}, {build}),
    prodvers=({major}, {minor}, {micro}, {build}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'{company}'),
        StringStruct(u'FileDescription', u'{description}'),
        StringStruct(u'FileVersion', u'{version}'),
        StringStruct(u'InternalName', u'{internal_name}'),
        StringStruct(u'LegalCopyright', u'{copyright_info}'),
        StringStruct(u'OriginalFilename', u'{original_filename}'),
        StringStruct(u'ProductName', u'{product_name}'),
        StringStruct(u'ProductVersion', u'{version}')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''

        version_file_path = self.build_dir / "version_info.txt"
        with open(version_file_path, 'w', encoding='utf-8') as f:
            f.write(version_file_content)

        return version_file_path
