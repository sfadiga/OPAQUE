# Build Backends Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the two build backends one typed configuration object, one command line flag that chooses between them, a template application that runs, and a build guide generated from the real signatures.

**Architecture:** `Builder.build(entry_point, **kwargs)` is the whole contract, and both backends read that dictionary with `kwargs.get("name")` calls scattered through 900 lines. Nineteen different keys are read, two of them are the same option under two spellings (`exclude_module` and `exclude_modules`), no reader can tell which key belongs to which backend, and a caller who misspells one gets the default in silence. Decision D9 keeps `build_tools` and slims it: one `BuildConfig` dataclass carries every option with a type and a docstring, both backends take it, the CLI builds one from the parsed arguments, and `docs/BUILD_GUIDE.md` is written from the dataclass fields so it cannot drift.

**Tech Stack:** Python 3.11 (`dataclasses`, `argparse`), PyInstaller, Nuitka, pytest.

**Closes:** the remainder of review 2.3 (the template application), decision D9.

**Depends on:** Plan 01 Task 2, which is what makes `opaque.build_tools` importable at all. Task 1 to Task 4 and Task 6 need nothing else. **Task 5 also needs Plan 08**, because the template it writes uses `opaque.shell`, `FeatureContext` and `self.register(...)`; run Task 5 after Plan 08, or write the template against the API that exists when you run it and say which you did.

---

## Rules that apply to every task here

1. Read `docs/superpowers/plans/2026-09-08-techdebt-00-index.md` first. The rules there are binding.
2. Run every command from `C:\Users\sfadiga\sandro\opaque`.
3. Never run a real build in a test. A build takes minutes and needs PyInstaller or Nuitka installed. Every test here checks the command line, the spec file or the configuration file that the builder produces, and stops there.
4. `is_available()` is the one method that may touch the third-party tool, and it must answer `False` instead of raising when the tool is absent.
5. This plan does not publish anything. Building an executable locally is in scope; uploading one is not.
6. **Never interpolate a value into generated source with a bare
   placeholder.** The old code wrote `['{entry_path}']` and
   `f"('{data}', '.')"` into the spec file. That is a defect, and it was
   found while executing Plan 01 Task 2. On Windows the interpolated path
   keeps its backslashes, and Python reads them as escape sequences when
   PyInstaller executes the spec. `C:\new\app.py` is read back as
   `'C:\new\x07pp.py'`, with a real newline and a real bell character.
   `C:\venv\...` and `C:\temp\...` fail the same way, and those are
   ordinary paths. Use `{value!r}` instead, or call `repr(str(value))`,
   and let Python write the literal. This applies to the entry point,
   every data file, the icon, and the application name, in the PyInstaller
   backend and in the Nuitka backend.

   Task 2 and Task 3 must each carry a test that proves it. Use a path
   that contains an escape sequence, generate the artefact, and assert on
   the value that comes back, not on the text that went out.

   ```python
   def test_a_windows_path_survives_the_spec(tmp_path):
       # `C:\new\app.py` must not come back as a newline and a bell.
       import ast

       entry = tmp_path / 'new' / 'app.py'
       spec = _spec_content_for(entry)   # the task names the real call
       literals = [
           node.value
           for node in ast.walk(ast.parse(spec))
           if isinstance(node, ast.Constant) and isinstance(node.value, str)
       ]
       assert str(entry) in literals
   ```

   The assertion is on the parsed value. A test that only checks the
   generated text passes while the defect is still there.
7. **The builder modules must stop writing to stdout.** Counted while
   executing Plan 01: `src/opaque` holds 47 `print()` calls. Five are in
   the services and belong to Plan 10 Task 6. Twenty-two are in
   `build_tools/cli.py`, and those are correct, because a command line
   entry point is allowed to print. The remaining twenty are library
   code: `builder.py:78,142`, `nuitka_builder.py:168,169,177,178,263,`
   `367,368,376,377`, and `pyinstaller_builder.py:133,134,142,143,200,`
   `325,326,334,335`. A library that prints cannot be embedded, cannot
   be tested without capturing stdout, and gives the caller no way to
   choose a destination. Task 2 and Task 3 must route each one through
   `logging.getLogger(__name__)` or return the value to the caller, and
   Task 4 decides what `cli.py` prints. Do not simply delete the
   messages: a build that reports nothing is worse than one that prints.

---

## File structure

| File | Responsibility |
|---|---|
| Create: `src/opaque/build_tools/config.py` | `BuildConfig`: every build option, with a type and a docstring. |
| Create: `tests/build_tools/__init__.py`, `tests/build_tools/test_config.py` | The configuration contract. |
| Modify: `src/opaque/build_tools/builder.py:35-50` | `build(entry_point, config)`. |
| Modify: `src/opaque/build_tools/pyinstaller_builder.py` | Read the configuration, not a dictionary. |
| Modify: `src/opaque/build_tools/nuitka_builder.py` | The same. |
| Modify: `src/opaque/build_tools/cli.py` | One `--backend` flag, and one place that builds the configuration. |
| Modify: `src/opaque/build_tools/templates/basic_app_template/main.py` | A template that runs. |
| Create: `tests/build_tools/test_template.py` | The template imports and builds a window. |
| Modify: `docs/BUILD_GUIDE.md` | Written from the real fields. |
| Create: `tests/build_tools/test_build_guide.py` | The guide names every field. |

---

## Task 1: One configuration object

**Files:**
- Create: `src/opaque/build_tools/config.py`
- Create: `tests/build_tools/__init__.py`
- Test: `tests/build_tools/test_config.py`

Nineteen keys are read out of `**kwargs` across the two backends. Two of them, `exclude_module` and `exclude_modules`, are the same option spelled two ways, and only one of the two is ever passed by the CLI. A dataclass ends that: one name per option, a type for each, and a `TypeError` for a name that does not exist.

- [ ] **Step 1: Write the failing test**

```bash
uv run python -c "open('tests/build_tools/__init__.py', 'w').close()"
```

Create `tests/build_tools/test_config.py`:

```python
# This Python file uses the following encoding: utf-8
"""Tests for BuildConfig."""

import dataclasses

import pytest

from opaque.build_tools.config import BuildConfig


def test_a_name_is_required():
    with pytest.raises(TypeError):
        BuildConfig()


def test_the_defaults_build_a_windowed_one_folder_application():
    config = BuildConfig(name="demo")

    assert config.name == "demo"
    assert config.onefile is False
    assert config.console is False
    assert config.debug is False


def test_an_unknown_option_is_refused():
    with pytest.raises(TypeError):
        BuildConfig(name="demo", onfile=True)


def test_the_configuration_cannot_be_changed_after_it_is_built():
    config = BuildConfig(name="demo")

    with pytest.raises(dataclasses.FrozenInstanceError):
        config.name = "other"


def test_every_list_option_defaults_to_an_empty_list():
    config = BuildConfig(name="demo")

    assert config.hidden_imports == []
    assert config.exclude_modules == []
    assert config.data_files == []
    assert config.include_packages == []
    assert config.nuitka_plugins == []


def test_two_configurations_do_not_share_a_list():
    first = BuildConfig(name="one")
    second = BuildConfig(name="two")

    first.hidden_imports.append("something")

    assert second.hidden_imports == []


def test_the_version_information_defaults_to_nothing():
    assert BuildConfig(name="demo").version_info is None


def test_a_field_carries_its_own_help_text():
    for field in dataclasses.fields(BuildConfig):
        assert field.metadata.get("help"), f"{field.name} has no help text"


def test_a_field_says_which_backends_use_it():
    allowed = {"both", "pyinstaller", "nuitka"}
    for field in dataclasses.fields(BuildConfig):
        assert field.metadata.get("backend") in allowed, field.name


def test_the_optimisation_level_is_checked():
    with pytest.raises(ValueError):
        BuildConfig(name="demo", optimization=9)


def test_the_job_count_is_checked():
    with pytest.raises(ValueError):
        BuildConfig(name="demo", jobs=0)


def test_an_empty_name_is_refused():
    with pytest.raises(ValueError):
        BuildConfig(name="")
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/build_tools/test_config.py -q
```

Expected: a collection error, `ModuleNotFoundError: No module named 'opaque.build_tools.config'`.

- [ ] **Step 3: Write the implementation**

Create `src/opaque/build_tools/config.py`:

```python
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
```

The `{separator}` inside the `data_files` help text is a literal brace pair in a plain string, not an f-string, so it stays as written. It is there because PyInstaller uses `os.pathsep` and Nuitka uses `=`; each backend says which in its own message.

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/build_tools/test_config.py -q
```

Expected: `12 passed`.

- [ ] **Step 5: Fix the typing note in the help text**

Read back the `data_files` help text you just wrote. It must read exactly:

```
"Data files to ship, each written as 'source{separator}destination'."
```

and the module must contain no f-string that wraps it. Check with:

```bash
uv run python -c "
from dataclasses import fields
from opaque.build_tools.config import BuildConfig
for entry in fields(BuildConfig):
    print(entry.name, '|', entry.metadata['backend'], '|', entry.metadata['help'][:40])
"
```

Expected: seventeen lines, each with a backend mark and a help text. Count them; the number is used by Task 6.

- [ ] **Step 6: Export it**

In `src/opaque/build_tools/__init__.py`, add the import and the `__all__` entry:

```python
from .builder import Builder, BuildError
from .config import BuildConfig
from .pyinstaller_builder import PyInstallerBuilder
from .nuitka_builder import NuitkaBuilder

__all__ = ['Builder', 'BuildConfig', 'BuildError', 'PyInstallerBuilder',
           'NuitkaBuilder']
```

- [ ] **Step 7: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 8: Commit**

```bash
git add src/opaque/build_tools/config.py src/opaque/build_tools/__init__.py tests/build_tools
git commit -m "feat(build_tools): add one typed BuildConfig"
```

---

## Task 2: The PyInstaller backend takes the configuration

**Files:**
- Modify: `src/opaque/build_tools/builder.py:35-50`
- Modify: `src/opaque/build_tools/pyinstaller_builder.py:23-283`
- Test: `tests/build_tools/test_pyinstaller_builder.py`

- [ ] **Step 1: Write the failing test**

Create `tests/build_tools/test_pyinstaller_builder.py`:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the PyInstaller backend. No real build is ever run."""

import ast

import pytest

from opaque.build_tools.config import BuildConfig
from opaque.build_tools.pyinstaller_builder import PyInstallerBuilder


@pytest.fixture
def entry_point(tmp_path):
    path = tmp_path / "main.py"
    path.write_text("print('hello')\n", encoding="utf-8")
    return path


@pytest.fixture
def builder(tmp_path):
    return PyInstallerBuilder(work_dir=tmp_path)


def test_is_available_answers_without_raising(builder):
    assert builder.is_available() in (True, False)


def test_the_build_signature_takes_a_configuration():
    import inspect

    parameters = list(
        inspect.signature(PyInstallerBuilder.build).parameters)
    assert parameters == ["self", "entry_point", "config"]


def test_the_command_carries_the_name(builder, entry_point):
    command = builder.build_command(entry_point, BuildConfig(name="demo"))

    assert "--name" in command
    assert "demo" in command


def test_one_file_is_asked_for_only_when_it_is_wanted(builder, entry_point):
    with_onefile = builder.build_command(
        entry_point, BuildConfig(name="demo", onefile=True))
    without = builder.build_command(entry_point, BuildConfig(name="demo"))

    assert "--onefile" in with_onefile
    assert "--onefile" not in without


def test_a_windowed_build_asks_for_no_console(builder, entry_point):
    command = builder.build_command(entry_point, BuildConfig(name="demo"))

    assert "--windowed" in command
    assert "--console" not in command


def test_a_console_build_asks_for_a_console(builder, entry_point):
    command = builder.build_command(
        entry_point, BuildConfig(name="demo", console=True))

    assert "--console" in command
    assert "--windowed" not in command


def test_every_excluded_module_reaches_the_command(builder, entry_point):
    command = builder.build_command(
        entry_point,
        BuildConfig(name="demo", exclude_modules=["tkinter", "numpy"]))

    text = " ".join(command)
    assert "tkinter" in text
    assert "numpy" in text


def test_every_hidden_import_reaches_the_command(builder, entry_point):
    command = builder.build_command(
        entry_point, BuildConfig(name="demo", hidden_imports=["my_plugin"]))

    assert "my_plugin" in " ".join(command)


def test_the_entry_point_is_the_last_argument(builder, entry_point):
    command = builder.build_command(entry_point, BuildConfig(name="demo"))

    assert command[-1] == str(entry_point)


@pytest.mark.parametrize("onefile", [True, False])
@pytest.mark.parametrize("icon", [None, "app.ico"])
def test_the_generated_spec_file_is_valid_python(
        builder, entry_point, onefile, icon):
    config = BuildConfig(name="demo", onefile=onefile, icon=icon)

    spec = builder.create_spec_file(entry_point, config)

    ast.parse(spec.read_text(encoding="utf-8"))


def test_the_spec_file_names_the_executable(builder, entry_point):
    spec = builder.create_spec_file(entry_point, BuildConfig(name="demo"))

    assert "demo" in spec.read_text(encoding="utf-8")


def test_a_missing_entry_point_is_refused(builder, tmp_path):
    from opaque.build_tools.builder import BuildError

    with pytest.raises(BuildError) as error:
        builder.build_command(tmp_path / "nothing.py", BuildConfig(name="d"))

    assert "nothing.py" in str(error.value)
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/build_tools/test_pyinstaller_builder.py -q
```

Expected: most tests FAIL with `AttributeError: 'PyInstallerBuilder' object has no attribute 'build_command'`, and `test_the_build_signature_takes_a_configuration` FAILS on the parameter list.

- [ ] **Step 3: Change the base contract**

In `src/opaque/build_tools/builder.py`, replace the abstract `build`. Before:

```python
    @abstractmethod
    def build(self, entry_point: Union[str, Path], **kwargs: Any) -> Path:
```

After:

```python
    @abstractmethod
    def build(
            self,
            entry_point: Union[str, Path],
            config: "BuildConfig",
    ) -> Path:
        """
        Build one executable.

        Args:
            entry_point: The .py file that starts the application.
            config: Every build option. See BuildConfig.

        Returns:
            The path of the executable that was produced.

        Raises:
            BuildError: When the backend is not installed, the entry point
                does not exist, or the backend reports a failure.
        """
```

Add the import at the top of that file:

```python
from opaque.build_tools.config import BuildConfig
```

and remove the quotes from the annotation once the import is there. Keep the rest of the docstring the file already had if it says anything the new one does not.

- [ ] **Step 4: Split the PyInstaller build into a command and a run**

In `src/opaque/build_tools/pyinstaller_builder.py`, replace `build` with two methods. The first assembles the command and can be tested without PyInstaller; the second runs it.

```python
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
        self._run_command(command)

        executable = self._find_executable(config.name, config.onefile)
        if executable is None:
            raise BuildError(
                f"PyInstaller reported success but no executable named "
                f"{config.name} was found under {self.dist_dir}.")
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
            raise BuildError(f"The entry point {entry_path} does not exist.")

        command: List[str] = [
            "pyinstaller",
            "--noconfirm",
            "--clean",
            "--name", config.name,
            "--distpath", str(self.dist_dir),
            "--workpath", str(self.build_dir),
            "--specpath", str(self.work_dir),
        ]

        if config.onefile:
            command.append("--onefile")

        if config.console:
            command.append("--console")
        else:
            command.append("--windowed")

        if config.debug:
            command.extend(["--debug", "all"])

        if config.upx:
            command.append("--upx-dir")
            command.append(str(self.work_dir))
        else:
            command.append("--noupx")

        if config.icon:
            command.extend(["--icon", config.icon])

        for module in config.hidden_imports + self._get_pyside6_includes():
            command.extend(["--hidden-import", module])

        for module in config.exclude_modules + self._get_common_excludes():
            command.extend(["--exclude-module", module])

        for entry in config.data_files:
            command.extend(["--add-data", entry])

        if config.optimization:
            command.append("-" + "O" * config.optimization)

        version_file = self._create_version_info_file(config.version_info)
        if version_file is not None:
            command.extend(["--version-file", str(version_file)])

        command.append(str(entry_path))
        return command
```

Read the current `build` before you delete it, and keep every flag it passed that the list above does not. Say which flags you carried over.

`_get_pyside6_includes` and `_get_common_excludes` are the methods `builder.py` already has.

- [ ] **Step 5: Change the spec file generator to take the configuration**

`create_spec_file(self, entry_point, **kwargs)` becomes `create_spec_file(self, entry_point, config)`, and `_generate_spec_content(self, entry_path, **kwargs)` becomes `_generate_spec_content(self, entry_path, config)`. Inside the generator, replace every `kwargs.get("x", default)` with `config.x`. Plan 01 Task 2 already rewrote that method so no nested f-string is left; keep that shape and change only where the values come from.

- [ ] **Step 6: Run the test to verify it passes**

```bash
uv run python -m pytest tests/build_tools/test_pyinstaller_builder.py -q
```

Expected: `15 passed`.

- [ ] **Step 7: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors. `tests/test_imports.py` from Plan 01 Task 2 imports every module of the package, so a syntax error in the spec generator fails there.

- [ ] **Step 8: Commit**

```bash
git add src/opaque/build_tools tests/build_tools
git commit -m "refactor(build_tools): give the PyInstaller backend a typed configuration"
```

---

## Task 3: The Nuitka backend takes the configuration

**Files:**
- Modify: `src/opaque/build_tools/nuitka_builder.py:23-343`
- Test: `tests/build_tools/test_nuitka_builder.py`

The same change as Task 2, on the other backend. The command is assembled by a method a test can call, and the configuration object replaces the dictionary.

- [ ] **Step 1: Write the failing test**

Create `tests/build_tools/test_nuitka_builder.py`:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the Nuitka backend. No real build is ever run."""

import inspect

import pytest

from opaque.build_tools.config import BuildConfig
from opaque.build_tools.nuitka_builder import NuitkaBuilder


@pytest.fixture
def entry_point(tmp_path):
    path = tmp_path / "main.py"
    path.write_text("print('hello')\n", encoding="utf-8")
    return path


@pytest.fixture
def builder(tmp_path):
    return NuitkaBuilder(work_dir=tmp_path)


def test_is_available_answers_without_raising(builder):
    assert builder.is_available() in (True, False)


def test_the_build_signature_takes_a_configuration():
    parameters = list(inspect.signature(NuitkaBuilder.build).parameters)
    assert parameters == ["self", "entry_point", "config"]


def test_the_command_carries_the_name(builder, entry_point):
    command = builder.build_command(entry_point, BuildConfig(name="demo"))

    assert any(argument.startswith("--output-filename=") and "demo" in argument
               for argument in command)


def test_the_pyside6_plugin_is_always_switched_on(builder, entry_point):
    command = builder.build_command(entry_point, BuildConfig(name="demo"))

    assert "--enable-plugin=pyside6" in command


def test_a_windowed_build_disables_the_console(builder, entry_point):
    command = builder.build_command(entry_point, BuildConfig(name="demo"))

    assert any("console" in argument for argument in command)


def test_one_file_is_asked_for_only_when_it_is_wanted(builder, entry_point):
    with_onefile = builder.build_command(
        entry_point, BuildConfig(name="demo", onefile=True))
    without = builder.build_command(entry_point, BuildConfig(name="demo"))

    assert "--onefile" in with_onefile
    assert "--onefile" not in without


def test_standalone_is_asked_for_by_default(builder, entry_point):
    command = builder.build_command(entry_point, BuildConfig(name="demo"))

    assert "--standalone" in command


def test_every_included_package_reaches_the_command(builder, entry_point):
    command = builder.build_command(
        entry_point, BuildConfig(name="demo", include_packages=["my_pkg"]))

    assert "--include-package=my_pkg" in command


def test_every_extra_plugin_reaches_the_command(builder, entry_point):
    command = builder.build_command(
        entry_point, BuildConfig(name="demo", nuitka_plugins=["numpy"]))

    assert "--enable-plugin=numpy" in command


def test_the_job_count_reaches_the_command(builder, entry_point):
    command = builder.build_command(
        entry_point, BuildConfig(name="demo", jobs=4))

    assert "--jobs=4" in command


def test_a_pyinstaller_only_option_is_ignored(builder, entry_point):
    command = builder.build_command(
        entry_point, BuildConfig(name="demo", upx=True))

    assert not any("upx" in argument.lower() for argument in command)


def test_the_entry_point_is_the_last_argument(builder, entry_point):
    command = builder.build_command(entry_point, BuildConfig(name="demo"))

    assert command[-1] == str(entry_point)


def test_a_missing_entry_point_is_refused(builder, tmp_path):
    from opaque.build_tools.builder import BuildError

    with pytest.raises(BuildError) as error:
        builder.build_command(tmp_path / "nothing.py", BuildConfig(name="d"))

    assert "nothing.py" in str(error.value)


def test_the_generated_config_file_names_the_executable(builder, entry_point):
    path = builder.create_config_file(entry_point, BuildConfig(name="demo"))

    assert "demo" in path.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/build_tools/test_nuitka_builder.py -q
```

Expected: most tests FAIL with `AttributeError: 'NuitkaBuilder' object has no attribute 'build_command'`.

- [ ] **Step 3: Write the implementation**

In `src/opaque/build_tools/nuitka_builder.py`, replace `build` with the same two-method shape Task 2 used:

```python
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

        command = self.build_command(entry_point, config)
        self._ensure_directories()
        self._run_command(command)

        executable = self._find_executable(
            Path(entry_point).stem, config.name, config.onefile)
        if executable is None:
            raise BuildError(
                f"Nuitka reported success but no executable named "
                f"{config.name} was found under {self.dist_dir}.")
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
            raise BuildError(f"The entry point {entry_path} does not exist.")

        command: List[str] = [
            sys.executable, "-m", "nuitka",
            "--assume-yes-for-downloads",
            f"--output-dir={self.dist_dir}",
            f"--output-filename={config.name}{self._executable_suffix()}",
        ]

        if config.standalone:
            command.append("--standalone")

        if config.onefile:
            command.append("--onefile")

        if config.follow_imports:
            command.append("--follow-imports")

        # The console flag is spelled as a mode by Nuitka, not as a switch.
        command.append(
            "--windows-console-mode=force" if config.console
            else "--windows-console-mode=disable")

        if config.debug:
            command.append("--debug")

        if config.icon:
            command.append(f"--windows-icon-from-ico={config.icon}")

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

        if config.optimization:
            command.append("--python-flag=" + "O" * config.optimization)

        self._add_windows_version_args(command, config.version_info or {})

        command.append(str(entry_path))
        return command

    @staticmethod
    def _executable_suffix() -> str:
        """Return the executable file extension for this platform."""
        return ".exe" if platform.system() == "Windows" else ""
```

Add `import sys` to the import block of that file if it is not there.

Read the current `build` before you delete it, and keep every flag it passed that the list above does not. Say which flags you carried over. `--windows-console-mode` and `--windows-icon-from-ico` are Windows-only flags; keep whatever platform guard the current code has around them and say what you kept.

- [ ] **Step 4: Change the configuration file generator**

`create_config_file(self, entry_point, **kwargs)` becomes `create_config_file(self, entry_point, config)`, and `_generate_config_content(self, **kwargs)` becomes `_generate_config_content(self, config)`. Replace every `kwargs.get(...)` inside with the matching field. `_add_windows_version_args` already takes a dictionary; leave its signature alone and pass `config.version_info or {}`.

- [ ] **Step 5: Run the test to verify it passes**

```bash
uv run python -m pytest tests/build_tools/test_nuitka_builder.py -q
```

Expected: `14 passed`.

- [ ] **Step 6: Prove no kwargs reader is left**

```bash
grep -rn "kwargs" --include=*.py src/opaque/build_tools
```

Expected: no output. Every option now arrives as a field of `BuildConfig`.

- [ ] **Step 7: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 8: Commit**

```bash
git add src/opaque/build_tools tests/build_tools
git commit -m "refactor(build_tools): give the Nuitka backend a typed configuration"
```

---

## Task 4: One command, one backend flag

**Files:**
- Modify: `src/opaque/build_tools/cli.py`
- Test: `tests/build_tools/test_cli.py`

The command line has two build subcommands, `pyinstaller` and `nuitka`, each with its own argument list, and two functions that read a `Namespace` and call a builder. Decision D9 asks for one command with a `--backend` flag, and one place that turns the parsed arguments into a `BuildConfig`.

- [ ] **Step 1: Write the failing test**

Create `tests/build_tools/test_cli.py`:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the build command line. No real build is ever run."""

import pytest

from opaque.build_tools.cli import config_from_args, create_parser, main


def _parse(*arguments):
    return create_parser().parse_args(list(arguments))


def test_the_default_backend_is_pyinstaller():
    arguments = _parse("build", "main.py")
    assert arguments.backend == "pyinstaller"


def test_the_backend_can_be_chosen():
    arguments = _parse("build", "main.py", "--backend", "nuitka")
    assert arguments.backend == "nuitka"


def test_an_unknown_backend_is_refused():
    with pytest.raises(SystemExit):
        _parse("build", "main.py", "--backend", "cython")


def test_the_name_defaults_to_the_entry_point_stem():
    config = config_from_args(_parse("build", "some/app.py"))
    assert config.name == "app"


def test_the_name_can_be_given():
    config = config_from_args(_parse("build", "app.py", "--name", "Bench"))
    assert config.name == "Bench"


def test_a_repeated_option_collects_every_value():
    config = config_from_args(_parse(
        "build", "app.py",
        "--hidden-import", "one",
        "--hidden-import", "two"))
    assert config.hidden_imports == ["one", "two"]


def test_the_flags_reach_the_configuration():
    config = config_from_args(_parse(
        "build", "app.py", "--onefile", "--console", "--debug"))
    assert config.onefile is True
    assert config.console is True
    assert config.debug is True


def test_the_defaults_are_the_configuration_defaults():
    config = config_from_args(_parse("build", "app.py"))
    assert config.onefile is False
    assert config.console is False
    assert config.jobs == 1


def test_a_bad_optimisation_level_is_reported_and_not_a_traceback(capsys):
    exit_code = main(["build", "app.py", "--optimization", "9"])

    assert exit_code != 0
    assert "optimization" in capsys.readouterr().out.lower()


def test_no_command_prints_the_help(capsys):
    exit_code = main([])

    assert exit_code == 1
    assert "usage" in capsys.readouterr().out.lower()


def test_the_info_command_still_works():
    assert main(["info"]) == 0


def test_the_two_old_subcommands_are_gone():
    with pytest.raises(SystemExit):
        _parse("pyinstaller", "app.py")
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/build_tools/test_cli.py -q
```

Expected: a collection error, `ImportError: cannot import name 'config_from_args'`.

- [ ] **Step 3: Write the implementation**

In `src/opaque/build_tools/cli.py`, replace `create_parser`, `add_pyinstaller_args`, `add_nuitka_args`, `build_with_pyinstaller`, `build_with_nuitka` and `main` with this. Keep `show_info` and `_prepare_version_info` as they are, and keep every option name the two old parsers offered so no existing command line breaks meaning.

```python
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
        "--onefile", action="store_true",
        help="Produce one single executable file")
    parser.add_argument(
        "--console", action="store_true",
        help="Keep a console window")
    parser.add_argument(
        "--debug", action="store_true",
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
    builder = builders[args.backend]()

    try:
        executable = builder.build(args.entry_point, config)
    except BuildError as error:
        print(f"The build failed: {error}")
        return 1

    size = builder.format_size(builder.get_executable_size(executable))
    print(f"Built {executable} ({size})")
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
```

`add_version_args` is whatever the current file calls the block of `--version-*` arguments that `_prepare_version_info` reads. Find it, and if the two old parsers each added those arguments inline, move them into one function with that name and call it once.

Add the imports the new code needs at the top of the file:

```python
from pathlib import Path

from .builder import BuildError
from .config import BuildConfig
from .nuitka_builder import NuitkaBuilder
from .pyinstaller_builder import PyInstallerBuilder
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/build_tools/test_cli.py -q
```

Expected: `12 passed`.

- [ ] **Step 5: Check the command by hand**

```bash
uv run opaque-build info
uv run opaque-build build --help
```

Expected: `info` prints which backends are installed and exits 0. `--help` prints one option list that names every option in Step 3, with `--backend` among them. Record whether both backends report as installed.

- [ ] **Step 6: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/build_tools/cli.py tests/build_tools/test_cli.py
git commit -m "refactor(build_tools): one build command with a backend flag"
```

---

## Task 5: A template application that runs

**Files:**
- Modify: `src/opaque/build_tools/templates/basic_app_template/main.py`
- Modify: `src/opaque/build_tools/templates/basic_app_template/requirements.txt`
- Test: `tests/build_tools/test_template.py`

**This task needs Plan 08.** The template below uses `opaque.shell`, `FeatureContext` and `self.register(...)`, none of which exists before it. If Plan 08 has not run, stop here, do Task 6, and come back.

The template a user starts from imports `Application`, `AppModel`, `AppPresenter` and `AppView`. None of those four names exists anywhere in the framework. This is the last piece of review 2.3: the file that is meant to be the first thing a new user runs cannot be imported. `examples/quickstart/main.py`, created by Plan 02 Task 2 and kept correct by `tests/test_quickstart.py`, is the shape that does work; the template becomes that shape with a placeholder name.

- [ ] **Step 1: Write the failing test**

Create `tests/build_tools/test_template.py`:

```python
# This Python file uses the following encoding: utf-8
"""The application template must import and build a window."""

import ast
import importlib
import importlib.util
from pathlib import Path

import pytest

TEMPLATE = (Path("src/opaque/build_tools/templates/basic_app_template")
            / "main.py")


def _opaque_imports(path: Path):
    """Return every (module, name) the file imports from opaque."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                "opaque"):
            for alias in node.names:
                found.append((node.module, alias.name))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("opaque"):
                    found.append((alias.name, None))
    return found


def test_the_template_is_valid_python():
    ast.parse(TEMPLATE.read_text(encoding="utf-8"))


def test_the_template_imports_only_names_that_exist():
    missing = []
    for module_name, name in _opaque_imports(TEMPLATE):
        module = importlib.import_module(module_name)
        if name is not None and not hasattr(module, name):
            missing.append(f"{module_name}.{name}")
    assert missing == []


def test_the_template_names_no_ghost_class():
    text = TEMPLATE.read_text(encoding="utf-8")
    for ghost in ("Application(", "AppModel", "AppPresenter", "AppView",
                  "opaque.core"):
        assert ghost not in text, ghost


def test_the_template_builds_a_window(qapp, qtbot, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    specification = importlib.util.spec_from_file_location(
        "template_main", TEMPLATE)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)

    window = module.TemplateApplication()
    qtbot.addWidget(window)

    assert window.windowTitle()


def test_the_template_registers_one_feature(qapp, qtbot, tmp_path,
                                            monkeypatch):
    monkeypatch.chdir(tmp_path)

    specification = importlib.util.spec_from_file_location(
        "template_main2", TEMPLATE)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)

    window = module.TemplateApplication()
    qtbot.addWidget(window)

    assert "template" in window._registered_features


def test_the_requirements_name_the_package_that_is_published():
    text = (TEMPLATE.parent / "requirements.txt").read_text(encoding="utf-8")
    assert "opaque-framework" in text
```

`monkeypatch.chdir(tmp_path)` is there because the template writes a log file, and a test must not leave one in the repository.

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/build_tools/test_template.py -q
```

Expected: `test_the_template_imports_only_names_that_exist` FAILS with a list holding `opaque.view.application.Application` and the other three. `test_the_template_names_no_ghost_class` FAILS. Both window tests FAIL with an `ImportError` while the module executes.

- [ ] **Step 3: Write the template**

Replace the whole of `src/opaque/build_tools/templates/basic_app_template/main.py` with:

```python
#!/usr/bin/env python3
"""
Basic OPAQUE Framework Application Template

The smallest application that runs. Copy this file, rename
TemplateApplication and TemplateModel, and add your own features with
self.register(YourModel, YourView, YourPresenter).

Build it into an executable with:
    opaque-build build main.py --name MyApplication

@copyright 2025 Your Name
Licensed under MIT License
"""

import sys
from typing import Any

from PySide6.QtWidgets import QApplication, QLabel

from opaque.features.context import FeatureContext
from opaque.models.configuration import DefaultApplicationConfiguration
from opaque.models.model import BaseModel
from opaque.presenters.presenter import BasePresenter
from opaque.shell import BaseApplication
from opaque.view.view import BaseView


class TemplateConfiguration(DefaultApplicationConfiguration):
    """What the shell needs to know about this application."""

    def get_application_name(self) -> str:
        return "MyApplication"

    def get_application_title(self) -> str:
        return "My Application"

    def get_application_organization(self) -> str:
        return "My Organization"


class TemplateModel(BaseModel):
    """The state of the one feature this template ships."""

    FEATURE_ID = "template"

    def feature_name(self) -> str:
        return self.tr("Welcome")


class TemplateView(BaseView):
    """The window of the one feature this template ships."""

    def __init__(self, context: FeatureContext) -> None:
        super().__init__(context)
        self.label = QLabel(self.tr("Your application starts here."))
        self.setWidget(self.label)


class TemplatePresenter(BasePresenter):
    """The presenter of the one feature this template ships."""

    def bind_events(self) -> None:
        """Connect the view to this presenter. Nothing to connect yet."""

    def update(
            self,
            field_name: str,
            new_value: Any,
            old_value: Any = None,
            model: Any = None,
    ) -> None:
        """Called when a model field changes. Nothing to show yet."""

    def on_view_show(self) -> None:
        """Called when the window is shown."""


class TemplateApplication(BaseApplication):
    """The application shell."""

    def __init__(self) -> None:
        super().__init__(TemplateConfiguration())
        self.register(TemplateModel, TemplateView, TemplatePresenter)


def main() -> int:
    """Start the application."""
    application = QApplication(sys.argv)
    window = TemplateApplication()

    if not window.try_acquire_lock():
        window.show_already_running_message()
        return 1

    window.show()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
```

Compare this against `examples/quickstart/main.py`. Every class and every method signature must match what that file uses, because `tests/test_quickstart.py` keeps that file true against the README. If the quickstart uses a different configuration method set, copy that set here and say what differed.

- [ ] **Step 4: Write the requirements file**

Replace `src/opaque/build_tools/templates/basic_app_template/requirements.txt` with:

```
# The framework, and the build backend you choose.
opaque-framework
opaque-framework[build]
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
uv run python -m pytest tests/build_tools/test_template.py -q
```

Expected: `6 passed`.

- [ ] **Step 6: Run the template by hand**

```bash
uv run python src/opaque/build_tools/templates/basic_app_template/main.py
```

Expected: a window opens with one sub-window reading "Your application starts here.". Close it. Record what you saw, and delete any file the run left in the repository root.

- [ ] **Step 7: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors. `tests/test_localisation.py` also reads this file, so both `tr()` calls must hold literals.

- [ ] **Step 8: Commit**

```bash
git add src/opaque/build_tools/templates tests/build_tools/test_template.py
git commit -m "fix(build_tools): make the application template import and run"
```

---

## Task 6: A build guide written from the real fields

**Files:**
- Modify: `docs/BUILD_GUIDE.md`
- Create: `tests/build_tools/test_build_guide.py`

Decision D9 asks for documentation generated from the real signatures. `BuildConfig` carries a help text and a backend mark on every field, so the guide can be checked against them, and a field added later without a line in the guide fails the suite.

- [ ] **Step 1: Write the failing test**

Create `tests/build_tools/test_build_guide.py`:

```python
# This Python file uses the following encoding: utf-8
"""The build guide must describe the real build options."""

import dataclasses
from pathlib import Path

import pytest

from opaque.build_tools.config import BuildConfig

GUIDE = Path("docs/BUILD_GUIDE.md")
FIELDS = list(dataclasses.fields(BuildConfig))


@pytest.fixture(scope="module")
def guide_text():
    return GUIDE.read_text(encoding="utf-8")


@pytest.mark.parametrize("field", FIELDS, ids=lambda entry: entry.name)
def test_every_option_is_documented(field, guide_text):
    assert field.name in guide_text


@pytest.mark.parametrize("field", FIELDS, ids=lambda entry: entry.name)
def test_every_option_says_which_backend_uses_it(field, guide_text):
    # The row for the field must be on one line with its backend mark.
    for line in guide_text.splitlines():
        if field.name in line:
            assert field.metadata["backend"] in line
            return
    pytest.fail(f"{field.name} has no row")


def test_the_guide_names_the_one_build_command(guide_text):
    assert "opaque-build build" in guide_text


def test_the_guide_names_the_backend_flag(guide_text):
    assert "--backend" in guide_text


def test_the_guide_names_no_removed_subcommand(guide_text):
    assert "opaque-build pyinstaller" not in guide_text
    assert "opaque-build nuitka" not in guide_text


def test_the_guide_names_no_ghost_function(guide_text):
    for ghost in ("build_executable", "opaque.core"):
        assert ghost not in guide_text
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/build_tools/test_build_guide.py -q
```

Expected: many FAIL. The guide describes the two old subcommands and none of the field names.

- [ ] **Step 3: Print the table**

```bash
uv run python -c "
import dataclasses
from opaque.build_tools.config import BuildConfig
print('| Option | Backend | Default | What it does |')
print('|---|---|---|---|')
for entry in dataclasses.fields(BuildConfig):
    default = entry.default
    if default is dataclasses.MISSING:
        default = 'required'
    if entry.default_factory is not dataclasses.MISSING:
        default = 'empty list'
    print(f'| \`{entry.name}\` | {entry.metadata[\"backend\"]} | \`{default}\` | {entry.metadata[\"help\"]} |')
"
```

Expected: seventeen table rows plus the two header rows. Copy the output; it goes into the guide unchanged.

- [ ] **Step 4: Write the guide**

Replace the whole of `docs/BUILD_GUIDE.md` with this, pasting the table from Step 3 where it says so:

````markdown
# Build Guide

How to turn an OPAQUE application into an executable.

## Install a backend

Neither backend is installed by default.

```bash
uv sync --extra build
```

That installs PyInstaller and Nuitka. Check what is available:

```bash
uv run opaque-build info
```

## Build

```bash
uv run opaque-build build path/to/main.py --name MyApplication
```

PyInstaller is used unless you ask for the other backend:

```bash
uv run opaque-build build path/to/main.py --name MyApplication --backend nuitka
```

PyInstaller packs the interpreter and the byte code, so a build takes
seconds to minutes. Nuitka compiles to C first, so a build takes minutes to
tens of minutes and starts faster afterwards. Start with PyInstaller.

## Every option

An option marked `pyinstaller` is ignored by the Nuitka backend, and an
option marked `nuitka` is ignored by the PyInstaller backend. This table is
generated from `BuildConfig` in `src/opaque/build_tools/config.py`, and
`tests/build_tools/test_build_guide.py` fails when a field is added without a
row here.

<!-- paste the table from Step 3 here -->

## From Python

The command line is a thin layer over one call:

```python
from opaque.build_tools import BuildConfig, PyInstallerBuilder

config = BuildConfig(
    name="MyApplication",
    onefile=True,
    hidden_imports=["my_plugin"],
)

builder = PyInstallerBuilder()
if builder.is_available():
    executable = builder.build("main.py", config)
    print(executable)
```

`build()` raises `BuildError` when the backend is missing, when the entry
point does not exist, or when the backend reports a failure. Use
`builder.build_command("main.py", config)` to see the command line without
running it.

## Start from the template

`src/opaque/build_tools/templates/basic_app_template/main.py` is the smallest
application that runs and builds. Copy it, rename the four `Template`
classes, and add your features.

## What this guide does not cover

Publishing. Building an executable on your own machine is one thing;
uploading it anywhere is a separate decision with its own approvals.
````

- [ ] **Step 5: Run the test to verify it passes**

```bash
uv run python -m pytest tests/build_tools/test_build_guide.py -q
```

Expected: `38 passed`. That is seventeen fields times two parametrized tests, plus four.

- [ ] **Step 6: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors. `tests/test_documentation.py` from Plan 02 Task 1 imports every `opaque` name this guide shows, so a wrong class name fails there.

- [ ] **Step 7: Commit**

```bash
git add docs/BUILD_GUIDE.md tests/build_tools/test_build_guide.py
git commit -m "docs(build_tools): write the build guide from the real options"
```

---

## Verification of the whole plan

- [ ] **Check 1: no option is read out of a dictionary**

```bash
grep -rn "kwargs" --include=*.py src/opaque/build_tools
```

Expected: no output.

- [ ] **Check 2: both backends answer the same contract**

```bash
uv run python -c "
import inspect
from opaque.build_tools import NuitkaBuilder, PyInstallerBuilder
for builder in (PyInstallerBuilder, NuitkaBuilder):
    print(builder.__name__, inspect.signature(builder.build))
    print(builder.__name__, inspect.signature(builder.build_command))
"
```

Expected: four identical signatures apart from the class name.

- [ ] **Check 3: one real build, by hand**

This is the only place a real build is run, and it is not a test.

```bash
uv run opaque-build build examples/quickstart/main.py --name QuickStart
```

Expected: PyInstaller runs and the command prints the path and the size of the executable. Start it and check that the window opens. Record the size. If PyInstaller is not installed, record that instead and skip this check.

Delete the `build/` and `dist/` folders afterwards, and check `git status --short` is clean.

- [ ] **Check 4: the whole suite, the type check and the lint**

```bash
uv run python -m pytest tests -q
uv run python -m mypy src/opaque/build_tools
uv run python -m pylint src/opaque/build_tools
```

Expected: the suite reports zero failures. `build_tools` was never type-checked before, because the module could not be imported; report every message it now produces.

---

## What this plan does not do

| Left open | Owner |
|---|---|
| `templates/pyinstaller_config.py` and `templates/nuitka_config.cfg` still hold hand-written option lists that nothing reads. Delete them or generate them from `BuildConfig`. | Plan 10 Task 3 |
| No build runs in CI. A build takes minutes and needs a backend installed, so the CI file Plan 01 Task 7 wrote does not do one. | Not scheduled. |
| Publishing an executable or a wheel anywhere. Out of scope by decision. | Not scheduled. |
