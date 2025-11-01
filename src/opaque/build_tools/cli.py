"""
Command Line Interface for OPAQUE Framework Build Tools.

@copyright 2025 Sandro Fadiga
Licensed under MIT License
"""

import argparse
import sys
from typing import Dict, List, Optional, Any

from .builder import BuildError
from .nuitka_builder import NuitkaBuilder
from .pyinstaller_builder import PyInstallerBuilder


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for build commands."""
    parser = argparse.ArgumentParser(
        prog="opaque-build",
        description="Build OPAQUE framework applications as standalone executables"
    )

    subparsers = parser.add_subparsers(dest="command", help="Build commands")

    # PyInstaller command
    pyinstaller_parser = subparsers.add_parser(
        "pyinstaller",
        help="Build executable using PyInstaller"
    )
    add_pyinstaller_args(pyinstaller_parser)

    # Nuitka command
    nuitka_parser = subparsers.add_parser(
        "nuitka",
        help="Build executable using Nuitka"
    )
    add_nuitka_args(nuitka_parser)

    # Info command
    subparsers.add_parser(
        "info",
        help="Show build tools information"
    )

    return parser


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add common arguments to parser."""
    parser.add_argument(
        "entry_point",
        help="Path to main Python file"
    )
    parser.add_argument(
        "--name", "-n",
        help="Name for the executable"
    )
    parser.add_argument(
        "--icon", "-i",
        help="Path to icon file"
    )
    parser.add_argument(
        "--version", "-v",
        help="Version string to inject into executable"
    )
    parser.add_argument(
        "--version-from",
        choices=["VERSION", "git", "env", "pyproject"],
        help="Source to read version from (VERSION file, git tags, environment, pyproject.toml)"
    )
    parser.add_argument(
        "--build-number",
        help="Build number to include in version info"
    )
    parser.add_argument(
        "--console", "-c",
        action="store_true",
        help="Show console window"
    )
    parser.add_argument(
        "--onefile", "-F",
        action="store_true",
        help="Create single executable file"
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug mode"
    )
    parser.add_argument(
        "--work-dir", "-w",
        help="Working directory for build process"
    )


def add_pyinstaller_args(parser: argparse.ArgumentParser) -> None:
    """Add PyInstaller specific arguments."""
    add_common_args(parser)

    parser.add_argument(
        "--add-data",
        action="append",
        help="Additional data files to include (format: source:dest)"
    )
    parser.add_argument(
        "--hidden-import",
        action="append",
        help="Modules to force import"
    )
    parser.add_argument(
        "--exclude-module",
        action="append",
        help="Modules to exclude"
    )
    parser.add_argument(
        "--upx",
        action="store_true",
        help="Use UPX compression"
    )
    parser.add_argument(
        "--spec-only",
        action="store_true",
        help="Create spec file only, don't build"
    )


def add_nuitka_args(parser: argparse.ArgumentParser) -> None:
    """Add Nuitka specific arguments."""
    add_common_args(parser)

    parser.add_argument(
        "--optimization",
        choices=["0", "1", "2"],
        default="1",
        help="Optimization level"
    )
    parser.add_argument(
        "--include-data-file",
        action="append",
        help="Data files to include"
    )
    parser.add_argument(
        "--include-package",
        action="append",
        help="Packages to include"
    )
    parser.add_argument(
        "--exclude-module",
        action="append",
        help="Modules to exclude"
    )
    parser.add_argument(
        "--plugin-enable",
        action="append",
        help="Nuitka plugins to enable"
    )
    parser.add_argument(
        "--lto",
        action="store_true",
        help="Enable Link Time Optimization"
    )
    parser.add_argument(
        "--jobs", "-j",
        type=int,
        help="Number of parallel compilation jobs"
    )
    parser.add_argument(
        "--config-only",
        action="store_true",
        help="Create config file only, don't build"
    )


def build_with_pyinstaller(args: argparse.Namespace) -> int:
    """Build executable with PyInstaller."""
    try:
        builder = PyInstallerBuilder(args.work_dir)

        if not builder.is_available():
            print(
                "Error: PyInstaller is not available. Install with: pip install pyinstaller")
            return 1

        # Handle version injection
        version_info = _prepare_version_info(args)

        build_kwargs = {
            "onefile": args.onefile,
            "console": args.console,
            "debug": args.debug
        }

        if version_info:
            build_kwargs["version_info"] = version_info

        if args.name:
            build_kwargs["name"] = args.name
        if args.icon:
            build_kwargs["icon"] = args.icon
        if args.add_data:
            build_kwargs["add_data"] = args.add_data
        if args.hidden_import:
            build_kwargs["hidden_imports"] = args.hidden_import
        if args.exclude_module:
            build_kwargs["exclude_modules"] = args.exclude_module
        if args.upx:
            build_kwargs["upx"] = True

        if args.spec_only:
            spec_path = builder.create_spec_file(
                args.entry_point, **build_kwargs)
            print(f"Spec file created: {spec_path}")
            print("Use 'pyinstaller spec_file.spec' to build from spec file")
            return 0
        else:
            exe_path = builder.build(args.entry_point, **build_kwargs)
            print(f"Build completed: {exe_path}")
            return 0

    except BuildError as e:
        print(f"Build failed: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


def build_with_nuitka(args: argparse.Namespace) -> int:
    """Build executable with Nuitka."""
    try:
        builder = NuitkaBuilder(args.work_dir)

        if not builder.is_available():
            print("Error: Nuitka is not available. Install with: pip install nuitka")
            return 1

        # Handle version injection
        version_info = _prepare_version_info(args)

        build_kwargs = {
            "onefile": args.onefile,
            "console": args.console,
            "debug": args.debug,
            "optimization": args.optimization
        }

        if version_info:
            build_kwargs["version_info"] = version_info

        if args.name:
            build_kwargs["name"] = args.name
        if args.icon:
            build_kwargs["icon"] = args.icon
        if args.include_data_file:
            build_kwargs["include_data_files"] = args.include_data_file
        if args.include_package:
            build_kwargs["include_package"] = args.include_package
        if args.exclude_module:
            build_kwargs["exclude_module"] = args.exclude_module
        if args.plugin_enable:
            build_kwargs["plugin_enable"] = args.plugin_enable
        if args.lto:
            build_kwargs["lto"] = True
        if args.jobs:
            build_kwargs["jobs"] = args.jobs

        if args.config_only:
            config_path = builder.create_config_file(
                args.entry_point, **build_kwargs)
            print(f"Config file created: {config_path}")
            print("Use 'nuitka @config_file.cfg entry_point.py' to build from config")
            return 0
        else:
            exe_path = builder.build(args.entry_point, **build_kwargs)
            print(f"Build completed: {exe_path}")
            return 0

    except BuildError as e:
        print(f"Build failed: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


def _prepare_version_info(args: argparse.Namespace) -> Optional[Dict[str, Any]]:
    """Prepare version information from various sources."""
    from ..services.version_service import VersionManager
    
    version_manager = VersionManager()
    version_info: Dict[str, Any] = {}
    
    # Get version from command line arg or auto-detect
    if hasattr(args, 'version') and args.version:
        version_info["version"] = args.version
    else:
        # Use auto-detection which handles all sources with proper priority
        version = version_manager.get_version()
        if version:
            version_info["version"] = version
    
    # Add build number if provided
    if hasattr(args, 'build_number') and args.build_number:
        version_info["build_number"] = args.build_number
    
    # Get additional version info
    version_manager_info = version_manager.get_version_info()
    if version_manager_info:
        # Add build date, commit hash, etc. from version manager
        for key, value in version_manager_info.items():
            if key not in version_info and value:
                version_info[key] = value
    
    return version_info if version_info else None


def show_info() -> int:
    """Show build tools information."""
    print("OPAQUE Framework Build Tools")
    print("=" * 40)

    # Check PyInstaller
    pyinstaller_builder = PyInstallerBuilder()
    if pyinstaller_builder.is_available():
        print("✓ PyInstaller: Available")
    else:
        print("✗ PyInstaller: Not available (install with: pip install pyinstaller)")

    # Check Nuitka
    nuitka_builder = NuitkaBuilder()
    if nuitka_builder.is_available():
        print("✓ Nuitka: Available")
        version = nuitka_builder.get_nuitka_version()
        if version:
            print(f"  Version: {version}")

        plugins = nuitka_builder.list_plugins()
        if plugins:
            print(f"  Available plugins: {', '.join(plugins[:5])}")
            if len(plugins) > 5:
                print(f"    ... and {len(plugins) - 5} more")
    else:
        print("✗ Nuitka: Not available (install with: pip install nuitka)")

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "pyinstaller":
        return build_with_pyinstaller(args)
    elif args.command == "nuitka":
        return build_with_nuitka(args)
    elif args.command == "info":
        return show_info()
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
