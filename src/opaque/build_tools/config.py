# This Python file uses the following encoding: utf-8
"""
OPAQUE Framework Build Tools

One configuration object for every build option.

@copyright 2025 Sandro Fadiga
Licensed under MIT License
"""

from dataclasses import dataclass, field, fields
from typing import Any, Dict, List, Optional

# The three values the "backend" metadata key may take. A field marked
# "pyinstaller" is ignored by the Nuitka builder and the other way round, and
# the build guide is generated from these marks.
BOTH = "both"
PYINSTALLER = "pyinstaller"
NUITKA = "nuitka"

# The highest optimisation level either backend accepts.
MAXIMUM_OPTIMIZATION = 2


@dataclass(frozen=True)
class BuildConfig:
    """
    Every option a build takes.

    Both builders used to read a **kwargs dictionary, with nineteen keys read
    by name in nine hundred lines of code. A misspelled key gave the default
    in silence, one option existed under two spellings, and nothing said
    which key belonged to which backend. Every field below carries a help
    text and the backend it applies to, and the build guide is generated from
    them.

    The object is frozen, so a builder cannot change the configuration it was
    given part way through a build.
    """

    name: str = field(
        metadata={"backend": BOTH,
                  "help": "The name of the executable, with no extension."})

    icon: Optional[str] = field(
        default=None,
        metadata={"backend": BOTH,
                  "help": "Path to the application icon, .ico on Windows "
                          "and .icns on macOS. None uses no icon."})

    onefile: bool = field(
        default=False,
        metadata={"backend": BOTH,
                  "help": "Produce one single executable file instead of a "
                          "folder. It starts more slowly, because it unpacks "
                          "itself on every start."})

    console: bool = field(
        default=False,
        metadata={"backend": BOTH,
                  "help": "Keep a console window. False is right for a "
                          "graphical application; True is how you read a "
                          "traceback from a packaged build."})

    debug: bool = field(
        default=False,
        metadata={"backend": BOTH,
                  "help": "Build with debug output from the backend."})

    upx: bool = field(
        default=False,
        metadata={"backend": PYINSTALLER,
                  "help": "Compress the executable with UPX, when UPX is "
                          "installed. It makes a smaller file that some "
                          "antivirus products dislike."})

    hidden_imports: List[str] = field(
        default_factory=list,
        metadata={"backend": BOTH,
                  "help": "Modules to include that no import statement "
                          "names, for example a plug-in loaded by name."})

    exclude_modules: List[str] = field(
        default_factory=list,
        metadata={"backend": BOTH,
                  "help": "Modules to leave out. This was two options, "
                          "exclude_module and exclude_modules, and only one "
                          "of them was ever passed."})

    data_files: List[str] = field(
        default_factory=list,
        metadata={"backend": BOTH,
                  "help": "Data files to ship, each written as "
                          "'source{separator}destination'."})

    include_packages: List[str] = field(
        default_factory=list,
        metadata={"backend": NUITKA,
                  "help": "Whole packages to compile in, by name."})

    standalone: bool = field(
        default=True,
        metadata={"backend": NUITKA,
                  "help": "Produce a build that needs no Python "
                          "installation. Leave this True."})

    follow_imports: bool = field(
        default=True,
        metadata={"backend": NUITKA,
                  "help": "Compile the modules the entry point imports, and "
                          "the modules those import."})

    nuitka_plugins: List[str] = field(
        default_factory=list,
        metadata={"backend": NUITKA,
                  "help": "Nuitka plug-ins to switch on. The pyside6 plug-in "
                          "is added for you."})

    jobs: int = field(
        default=1,
        metadata={"backend": NUITKA,
                  "help": "How many compiler processes to run at once. One "
                          "or more."})

    lto: bool = field(
        default=False,
        metadata={"backend": NUITKA,
                  "help": "Ask the compiler for link time optimisation. It "
                          "makes a smaller and faster build, slowly."})

    optimization: int = field(
        default=0,
        metadata={"backend": BOTH,
                  "help": f"Python optimisation level, 0 to "
                          f"{MAXIMUM_OPTIMIZATION}. 1 drops assert "
                          f"statements, 2 also drops docstrings."})

    version_info: Optional[Dict[str, Any]] = field(
        default=None,
        metadata={"backend": BOTH,
                  "help": "Version information for the Windows executable "
                          "properties. None writes none."})

    def __post_init__(self) -> None:
        """
        Check the values that have a range.

        A build takes minutes, so a value that cannot work has to be refused
        before the build starts and not by the backend half way through.
        """
        if not self.name:
            raise ValueError(
                "BuildConfig needs a name: it is the name of the executable.")

        if not 0 <= self.optimization <= MAXIMUM_OPTIMIZATION:
            raise ValueError(
                f"optimization must be between 0 and "
                f"{MAXIMUM_OPTIMIZATION}, not {self.optimization}.")

        if self.jobs < 1:
            raise ValueError(
                f"jobs must be one or more, not {self.jobs}.")

    def for_backend(self, backend: str) -> Dict[str, Any]:
        """
        Return the options this backend uses, as a dictionary.

        Args:
            backend: PYINSTALLER or NUITKA.

        Returns:
            The field name and value of every field marked for this backend
            or for both.
        """
        return {
            entry.name: getattr(self, entry.name)
            for entry in fields(self)
            if entry.metadata.get("backend") in (BOTH, backend)
        }
