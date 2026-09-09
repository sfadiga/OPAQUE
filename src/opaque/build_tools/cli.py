"""
Command Line Interface for OPAQUE Framework Build Tools.

@copyright 2025 Sandro Fadiga
Licensed under MIT License
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

from .builder import BuildError
from .config import BuildConfig
from .nuitka_builder import NuitkaBuilder
from .pyinstaller_builder import PyInstallerBuilder


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the build command."""
    parser = argparse.ArgumentParser(
        prog="opaque-build",
        description=(
            "Build OPAQUE framework applications as standalone executables"))

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    build_parser = subparsers.add_parser(
        "build", help="Build an executable")
    add_build_args(build_parser)

    subparsers.add_parser("info", help="Show build tools information")

    return parser


def add_version_args(parser: argparse.ArgumentParser) -> None:
    """Add the arguments _prepare_version_info reads."""
    parser.add_argument(
        "--version", "-v",
        help="Version string to inject into executable"
    )
    parser.add_argument(
        "--version-from",
        choices=["VERSION", "git", "env", "pyproject"],
        help="Source to read version from (VERSION file, git tags, "
             "environment, pyproject.toml)"
    )
    parser.add_argument(
        "--build-number",
        help="Build number to include in version info"
    )


def add_build_args(parser: argparse.ArgumentParser) -> None:
    """
    Add every build option to the parser.

    One list, one place. There used to be two subcommands with two lists,
    which is how one option ended up with two spellings.
    """
    parser.add_argument(
        "entry_point",
        help="Path to the main Python file")
    parser.add_argument(
        "--backend", "-b",
        choices=["pyinstaller", "nuitka"],
        default="pyinstaller",
        help="Which build backend to use (default: pyinstaller)")
    parser.add_argument(
        "--name", "-n",
        help="Name for the executable (default: the entry point file name)")
    parser.add_argument(
        "--icon", "-i",
        help="Path to the application icon")
    parser.add_argument(
        "--onefile", "-F", action="store_true",
        help="Produce one single executable file")
    parser.add_argument(
        "--console", "-c", action="store_true",
        help="Keep a console window")
    parser.add_argument(
        "--debug", "-d", action="store_true",
        help="Build with debug output from the backend")
    parser.add_argument(
        "--upx", action="store_true",
        help="Compress with UPX (PyInstaller only)")
    parser.add_argument(
        "--hidden-import", action="append", default=[], dest="hidden_imports",
        metavar="MODULE",
        help="A module to include that no import statement names. Repeatable")
    parser.add_argument(
        "--exclude-module", action="append", default=[],
        dest="exclude_modules", metavar="MODULE",
        help="A module to leave out. Repeatable")
    parser.add_argument(
        "--add-data", action="append", default=[], dest="data_files",
        metavar="SRC:DEST",
        help="A data file to ship. Repeatable")
    parser.add_argument(
        "--include-package", action="append", default=[],
        dest="include_packages", metavar="PACKAGE",
        help="A whole package to compile in (Nuitka only). Repeatable")
    parser.add_argument(
        "--enable-plugin", action="append", default=[],
        dest="nuitka_plugins", metavar="PLUGIN",
        help="A Nuitka plug-in to switch on (Nuitka only). Repeatable")
    parser.add_argument(
        "--jobs", "-j", type=int, default=1,
        help="How many compiler processes to run at once (Nuitka only)")
    parser.add_argument(
        "--lto", action="store_true",
        help="Ask for link time optimisation (Nuitka only)")
    parser.add_argument(
        "--optimization", "-O", type=int, default=0,
        help="Python optimisation level, 0 to 2")
    parser.add_argument(
        "--no-standalone", action="store_false", dest="standalone",
        help="Do not produce a standalone build (Nuitka only)")
    parser.add_argument(
        "--no-follow-imports", action="store_false", dest="follow_imports",
        help="Do not compile the imported modules (Nuitka only)")
    parser.add_argument(
        "--work-dir", "-w",
        help="Working directory for the build process")

    add_version_args(parser)


def config_from_args(args: argparse.Namespace) -> BuildConfig:
    """
    Turn the parsed command line into one BuildConfig.

    This is the only place that reads the Namespace. Two functions used to do
    it, one per backend, so an option added to one was missing from the
    other.

    Args:
        args: The parsed arguments of the build command.

    Returns:
        The configuration for the build.

    Raises:
        ValueError: When a value is out of range. BuildConfig checks that.
    """
    return BuildConfig(
        name=args.name or Path(args.entry_point).stem,
        icon=args.icon,
        onefile=args.onefile,
        console=args.console,
        debug=args.debug,
        upx=args.upx,
        hidden_imports=list(args.hidden_imports),
        exclude_modules=list(args.exclude_modules),
        data_files=list(args.data_files),
        include_packages=list(args.include_packages),
        standalone=args.standalone,
        follow_imports=args.follow_imports,
        nuitka_plugins=list(args.nuitka_plugins),
        jobs=args.jobs,
        lto=args.lto,
        optimization=args.optimization,
        version_info=_prepare_version_info(args),
    )


def build(args: argparse.Namespace) -> int:
    """
    Run one build, and report a failure as a message and an exit code.

    Args:
        args: The parsed arguments of the build command.

    Returns:
        0 when the build succeeded, 1 when it did not.
    """
    try:
        config = config_from_args(args)
    except ValueError as error:
        print(f"That build cannot run: {error}")
        return 1

    builders = {
        "pyinstaller": PyInstallerBuilder,
        "nuitka": NuitkaBuilder,
    }
    builder = builders[args.backend](args.work_dir)

    try:
        executable = builder.build(args.entry_point, config)
    except BuildError as error:
        print(f"The build failed: {error}")
        return 1

    size = builder.format_size(builder.get_executable_size(executable))
    print(f"Built {executable} ({size})")
    return 0


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

    if args.command == "build":
        return build(args)
    if args.command == "info":
        return show_info()

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
