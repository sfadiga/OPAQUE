"""
PyInstaller builder for OPAQUE framework applications.

@copyright 2025 Sandro Fadiga
Licensed under MIT License
"""

import logging
import platform
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .builder import Builder, BuildError
from .config import BuildConfig

logger = logging.getLogger(__name__)


class PyInstallerBuilder(Builder):
    """Builder using PyInstaller to create executables."""

    def is_available(self) -> bool:
        """Check if PyInstaller is available."""
        return shutil.which("pyinstaller") is not None

    def build(
            self,
            entry_point: Union[str, Path],
            config: BuildConfig,
    ) -> Path:
        """
        Build one executable with PyInstaller.

        Args:
            entry_point: The .py file that starts the application.
            config: Every build option. See BuildConfig.

        Returns:
            The path of the executable that was produced.

        Raises:
            BuildError: When PyInstaller is not installed, the entry point
                does not exist, or PyInstaller reports a failure.
        """
        if not self.is_available():
            raise BuildError(
                "PyInstaller is not installed. Install the build extra: "
                "uv sync --extra build")

        command = self.build_command(entry_point, config)
        self._ensure_directories()
        result = self._run_command(command)
        logger.info("PyInstaller output:\n%s", result.stdout)

        executable = self._find_executable(config.name, config.onefile)
        if executable is None or not executable.exists():
            raise BuildError(
                f"PyInstaller reported success but no executable named "
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
        Return the PyInstaller command line for one build.

        This is separate from build() so a test can check every option
        without installing PyInstaller and without waiting minutes for a
        real build.

        Args:
            entry_point: The .py file that starts the application.
            config: Every build option.

        Returns:
            The command, as a list of arguments, with the entry point last.

        Raises:
            BuildError: When the entry point does not exist.
        """
        entry_path = Path(entry_point)
        if not entry_path.exists():
            raise BuildError(f"Entry point not found: {entry_path}")

        command: List[str] = ["pyinstaller"]

        if config.onefile:
            command.append("--onefile")
        else:
            command.append("--onedir")

        if config.console:
            command.append("--console")
        else:
            command.append("--windowed")

        command.extend(["--name", config.name])

        command.extend(["--distpath", str(self.output_dir)])
        command.extend(["--workpath", str(self.build_dir)])
        command.extend(["--specpath", str(self.build_dir)])

        if config.icon:
            command.extend(["--icon", config.icon])

        command.append("--clean")

        pyside6_path = self._find_pyside6_path()
        if pyside6_path:
            command.extend(
                ["--add-binary",
                 f"{pyside6_path}/*{self._get_lib_extension()};PySide6"])

        for module in self._get_pyside6_includes() + config.hidden_imports:
            command.extend(["--hidden-import", module])

        for module in self._get_common_excludes() + config.exclude_modules:
            command.extend(["--exclude-module", module])

        for data in config.data_files:
            command.extend(["--add-data", data])

        if config.upx:
            command.append("--upx-dir")

        if config.debug:
            command.append("--debug=all")
        else:
            command.append("--log-level=WARN")

        version_info_file = self._create_version_info_file(
            config.version_info)
        if version_info_file:
            command.extend(["--version-file", str(version_info_file)])

        command.append(str(entry_path))
        return command

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

    def create_spec_file(
            self,
            entry_point: Union[str, Path],
            config: BuildConfig,
    ) -> Path:
        """
        Create a PyInstaller spec file for advanced customization.

        Args:
            entry_point: The .py file that starts the application.
            config: Every build option.

        Returns:
            Path to created spec file
        """
        entry_path = Path(entry_point)
        spec_path = self.build_dir / f"{config.name}.spec"

        self._ensure_directories()

        spec_content = self._generate_spec_content(entry_path, config)

        with open(spec_path, 'w', encoding='utf-8') as f:
            f.write(spec_content)

        logger.info("Spec file created: %s", spec_path)
        return spec_path

    def _generate_spec_content(
            self,
            entry_path: Path,
            config: BuildConfig,
    ) -> str:
        """
        Generate PyInstaller spec file content.

        Every variable part is built before the template. The template holds
        no nested f-string, because nesting a same-quote f-string needs
        PEP 701, which is Python 3.12 and above. This module must parse on
        the declared floor, 3.11.

        Every value that reaches the template goes through `repr()` first, so
        Python writes the literal instead of a bare placeholder. A bare
        placeholder reads a Windows path's backslashes as escape sequences:
        `C:\\new\\app.py` comes back as a real newline and a real bell.
        """
        name = config.name
        onefile = config.onefile
        console = config.console

        # Build data files list
        data_files = [f"({data!r}, '.')" for data in config.data_files]
        data_files_str = ", ".join(data_files)

        # Build hidden imports list
        hidden_imports = self._get_pyside6_includes() + config.hidden_imports
        hidden_imports_str = ", ".join(repr(imp) for imp in hidden_imports)

        # Build excludes list
        excludes = self._get_common_excludes() + config.exclude_modules
        excludes_str = ", ".join(repr(exc) for exc in excludes)

        # A onefile build hands the binaries, the zipfiles and the datas to
        # EXE. A onedir build hands them to COLLECT instead, and EXE gets
        # empty lists.
        bundle_lines = "a.binaries," if onefile else "[],"
        zip_lines = "a.zipfiles," if onefile else "[],"
        data_lines = "a.datas," if onefile else "[],"

        debug_flag = str(config.debug).lower()
        upx_flag = str(config.upx).lower()
        console_flag = str(console).lower()

        icon_line = f"    icon={config.icon!r}," if config.icon else ""

        collect_block = ""
        if not onefile:
            collect_block = (
                "\n\ncoll = COLLECT(\n"
                "    exe,\n"
                "    a.binaries,\n"
                "    a.zipfiles,\n"
                "    a.datas,\n"
                "    strip=False,\n"
                f"    upx={upx_flag},\n"
                "    upx_exclude=[],\n"
                f"    name={name!r},\n"
                ")\n"
            )

        entry_path_repr = repr(str(entry_path))

        spec_template = f'''# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for {name}
# Generated by OPAQUE Framework Build Tools

block_cipher = None

a = Analysis(
    [{entry_path_repr}],
    pathex=[],
    binaries=[],
    datas=[{data_files_str}],
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

exe = EXE(
    pyz,
    a.scripts,
    {bundle_lines}
    {zip_lines}
    {data_lines}
    name={name!r},
    debug={debug_flag},
    bootloader_ignore_signals=False,
    strip=False,
    upx={upx_flag},
    upx_exclude=[],
    runtime_tmpdir=None,
    console={console_flag},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
{icon_line}
)
{collect_block}'''
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
            logger.info("PyInstaller output:\n%s", result.stdout)

            # Try to find the executable
            name = spec_path.stem
            for onefile in [True, False]:
                exe_path = self._find_executable(name, onefile)
                if exe_path and exe_path.exists():
                    size = self.get_executable_size(exe_path)
                    logger.info("Build successful! Executable: %s (%s)",
                                 exe_path, self.format_size(size))
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
