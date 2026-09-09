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

| Option | Backend | Default | What it does |
|---|---|---|---|
| `name` | both | `required` | The name of the executable, with no extension. |
| `icon` | both | `None` | Path to the application icon, .ico on Windows and .icns on macOS. None uses no icon. |
| `onefile` | both | `False` | Produce one single executable file instead of a folder. It starts more slowly, because it unpacks itself on every start. |
| `console` | both | `False` | Keep a console window. False is right for a graphical application; True is how you read a traceback from a packaged build. |
| `debug` | both | `False` | Build with debug output from the backend. |
| `upx` | pyinstaller | `False` | Compress the executable with UPX, when UPX is installed. It makes a smaller file that some antivirus products dislike. |
| `hidden_imports` | both | `empty list` | Modules to include that no import statement names, for example a plug-in loaded by name. |
| `exclude_modules` | both | `empty list` | Modules to leave out. This was two options, exclude_module and exclude_modules, and only one of them was ever passed. |
| `data_files` | both | `empty list` | Data files to ship, each written as 'source{separator}destination'. |
| `include_packages` | nuitka | `empty list` | Whole packages to compile in, by name. |
| `standalone` | nuitka | `True` | Produce a build that needs no Python installation. Leave this True. |
| `follow_imports` | nuitka | `True` | Compile the modules the entry point imports, and the modules those import. |
| `nuitka_plugins` | nuitka | `empty list` | Nuitka plug-ins to switch on. The pyside6 plug-in is added for you. |
| `jobs` | nuitka | `1` | How many compiler processes to run at once. One or more. |
| `lto` | nuitka | `False` | Ask the compiler for link time optimisation. It makes a smaller and faster build, slowly. |
| `optimization` | both | `0` | Python optimisation level, 0 to 2. 1 drops assert statements, 2 also drops docstrings. |
| `version_info` | both | `None` | Version information for the Windows executable properties. None writes none. |

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
