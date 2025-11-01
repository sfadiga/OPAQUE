# OPAQUE Framework - Executable Build Guide

This guide explains how to create standalone executables from your OPAQUE Framework applications using PyInstaller or Nuitka.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Build Methods](#build-methods)
- [Configuration Templates](#configuration-templates)
- [CI/CD Integration](#cicd-integration)
- [PyInstaller vs Nuitka](#pyinstaller-vs-nuitka)
- [Advanced Configuration](#advanced-configuration)
- [Troubleshooting](#troubleshooting)

## Overview

The OPAQUE Framework provides multiple ways to build standalone executables:

1. **CLI Tool** - `opaque-build` command-line interface
2. **CI/CD Scripts** - `./cicd.sh build-exe` or `.\cicd.ps1 build-exe`
3. **Configuration Templates** - Pre-configured build files
4. **Direct Builder APIs** - Programmatic building

### Supported Builders

- **PyInstaller** - Fast builds, larger executables, broad compatibility
- **Nuitka** - Slower builds, optimized executables, better performance

## Installation

### 1. Install OPAQUE Framework

```bash
# From source (development)
pip install -e .

# From PyPI (when available)
pip install opaque-framework
```

### 2. Install Build Dependencies

```bash
# For PyInstaller builds
pip install "opaque-framework[pyinstaller]"

# For Nuitka builds  
pip install "opaque-framework[nuitka]"

# For both builders
pip install "opaque-framework[build]"
```

## Quick Start

### Using CLI Tool

```bash
# Build with PyInstaller (recommended for beginners)
opaque-build pyinstaller main.py

# Build with Nuitka (recommended for production)
opaque-build nuitka main.py

# Build with custom options
opaque-build pyinstaller main.py --name MyApp --onefile --windowed
```

### Using CI/CD Scripts

```bash
# Linux/macOS
./cicd.sh build-exe pyinstaller
./cicd.sh build-exe nuitka examples/basic_example/main.py

# Windows PowerShell
.\cicd.ps1 build-exe pyinstaller
.\cicd.ps1 build-exe nuitka examples/basic_example/main.py
```

## Build Methods

### 1. CLI Tool (Recommended)

The `opaque-build` command provides the simplest interface:

```bash
# Basic usage
opaque-build <builder> <entry_point> [options]

# Examples
opaque-build pyinstaller main.py
opaque-build nuitka app.py --name "My OPAQUE App"
opaque-build pyinstaller main.py --debug --console
```

**Common Options:**

- `--name <name>` - Executable name
- `--onefile` - Single file executable
- `--windowed` - Hide console (GUI apps)
- `--debug` - Enable debug mode
- `--console` - Show console (override windowed)

### 2. Configuration Templates

Use pre-configured templates for complex builds:

```bash
# Copy templates to your project
cp src/opaque/build_tools/templates/pyinstaller_config.py .
cp src/opaque/build_tools/templates/nuitka_config.cfg .

# Customize the configuration files
# Edit APP_NAME, APP_ENTRY_POINT, etc.

# Build using templates
pyinstaller pyinstaller_config.py
nuitka @nuitka_config.cfg main.py
```

### 3. CI/CD Integration

The framework includes CI/CD scripts with build-exe commands:

```bash
# Setup environment and build
./cicd.sh setup
./cicd.sh build-exe pyinstaller

# Build specific application
./cicd.sh build-exe nuitka examples/my_example/main.py --name MyApp
```

### 4. Programmatic Building

Use the builder APIs directly in Python:

```python
from opaque.build_tools.pyinstaller_builder import PyInstallerBuilder
from opaque.build_tools.nuitka_builder import NuitkaBuilder

# PyInstaller build
builder = PyInstallerBuilder()
builder.build(
    entry_point="main.py",
    name="MyApp",
    onefile=True,
    windowed=True
)

# Nuitka build
builder = NuitkaBuilder()
builder.build(
    entry_point="main.py",
    standalone=True,
    onefile=True,
    enable_plugin=["pyside6"]
)
```

## Configuration Templates

### PyInstaller Template

The PyInstaller template (`pyinstaller_config.py`) provides comprehensive configuration:

```python
# Key configuration variables
APP_ENTRY_POINT = "main.py"      # Your main Python file
APP_NAME = "MyOpaqueApp"         # Executable name
APP_ICON = "assets/icon.ico"     # Application icon
ONEFILE = True                   # Single file executable
CONSOLE = False                  # Hide console for GUI apps
DEBUG = False                    # Debug mode

# Advanced options
ADD_DATA = [("config.json", ".")]  # Include data files
HIDDEN_IMPORTS = ["my_module"]      # Additional imports
EXCLUDE_MODULES = ["tkinter"]       # Exclude unused modules
```

### Nuitka Template

The Nuitka template (`nuitka_config.cfg`) uses command-line options:

```cfg
# Basic options
--standalone
--onefile
--windows-disable-console

# PySide6 support (required for OPAQUE)
--enable-plugin=pyside6

# Optimization
--optimization-level=1

# Include/exclude
--include-data-files=config.json=.
--nofollow-import-to=tkinter
```

## CI/CD Integration

### Available Commands

The CI/CD scripts support build-exe with the following syntax:

```bash
# Format
./cicd.sh build-exe <builder> [entry_point] [options]

# Examples
./cicd.sh build-exe pyinstaller                           # Default entry point
./cicd.sh build-exe nuitka examples/my_example/main.py    # Custom entry point
./cicd.sh build-exe pyinstaller main.py --name MyApp      # With options
```

### Automated Builds

Integrate into your CI/CD pipeline:

```yaml
# GitHub Actions example
- name: Build Executable
  run: |
    ./cicd.sh setup
    ./cicd.sh build-exe nuitka examples/basic_example/main.py --name MyOpaqueApp
```

## PyInstaller vs Nuitka

| Feature | PyInstaller | Nuitka |
|---------|-------------|---------|
| **Build Speed** | Fast (seconds to minutes) | Slow (minutes to hours) |
| **Executable Size** | Larger | Smaller |
| **Runtime Performance** | Standard Python | Optimized (faster) |
| **Startup Time** | Slower | Faster |
| **Compatibility** | Excellent | Good |
| **Learning Curve** | Easy | Moderate |
| **Best For** | Development, testing | Production, distribution |

### When to Use PyInstaller

- **Development builds** - Quick iteration
- **Testing** - Rapid prototyping
- **Complex dependencies** - Better compatibility
- **First-time builders** - Easier to use

### When to Use Nuitka

- **Production releases** - Optimized performance
- **Distribution** - Smaller file sizes
- **Performance-critical apps** - Runtime optimization
- **Professional deployment** - Better startup times

## Advanced Configuration

### Custom Icons

```bash
# PyInstaller
opaque-build pyinstaller main.py --icon assets/icon.ico

# Nuitka (in config file)
--windows-icon-from-ico=assets/icon.ico
--macos-app-icon=assets/icon.icns
```

### Including Data Files

```bash
# PyInstaller
opaque-build pyinstaller main.py --add-data "config.json:." --add-data "assets:assets"

# Nuitka (in config file)
--include-data-files=config.json=.
--include-data-files=assets/=assets/
```

### Excluding Modules

```bash
# PyInstaller
opaque-build pyinstaller main.py --exclude-module tkinter --exclude-module matplotlib

# Nuitka (in config file)
--nofollow-import-to=tkinter
--nofollow-import-to=matplotlib
```

### Debug Builds

```bash
# PyInstaller debug
opaque-build pyinstaller main.py --debug --console

# Nuitka debug (in config file)
--debug
```

## Troubleshooting

### Common Issues

#### 1. Missing Modules

**Error:** `ModuleNotFoundError` in built executable

**Solution:**

```bash
# Add hidden imports
opaque-build pyinstaller main.py --hidden-import my_module

# Or in config template
HIDDEN_IMPORTS = ["my_module", "another_module"]
```

#### 2. Missing Data Files

**Error:** `FileNotFoundError` for config/asset files

**Solution:**

```bash
# Include data files
opaque-build pyinstaller main.py --add-data "config.json:."

# Or in config template
ADD_DATA = [("config.json", "."), ("assets/", "assets/")]
```

#### 3. Large Executable Size

**Solution:**

```bash
# Exclude unnecessary modules
opaque-build pyinstaller main.py --exclude-module tkinter --exclude-module matplotlib

# Or use Nuitka for better optimization
opaque-build nuitka main.py
```

#### 4. Slow Startup

**Solution:**

- Use Nuitka instead of PyInstaller
- Enable `--onefile=False` for directory distribution
- Exclude unused modules

#### 5. PySide6 Issues

**Error:** Qt/PySide6 related errors

**Solution:**

```bash
# Ensure PySide6 plugin is enabled
# PyInstaller (automatic)
opaque-build pyinstaller main.py

# Nuitka (explicit)
opaque-build nuitka main.py --enable-plugin pyside6
```

### Debug Information

Enable debug output for troubleshooting:

```bash
# PyInstaller verbose output
pyinstaller --log-level DEBUG pyinstaller_config.py

# Nuitka debug mode
nuitka --debug @nuitka_config.cfg main.py
```

### Getting Help

1. Check the [OPAQUE Framework documentation](README.md)
2. Review example applications in `examples/`
3. Examine configuration templates in `src/opaque/build_tools/templates/`
4. Enable debug mode for detailed error messages

## Best Practices

1. **Start Simple** - Use basic CLI commands first
2. **Test Early** - Build executables during development
3. **Use Templates** - Customize configuration templates for complex builds
4. **Version Control** - Include build configurations in your repository
5. **Automate** - Integrate builds into CI/CD pipelines
6. **Document** - Document your build process and requirements

## Example Workflows

### Development Workflow

```bash
# 1. Setup environment
./cicd.sh setup

# 2. Develop your application
# Edit your Python files...

# 3. Test with Python
./cicd.sh run

# 4. Quick test build
opaque-build pyinstaller main.py --debug

# 5. Test executable
./dist/main
```

### Production Workflow

```bash
# 1. Setup environment
./cicd.sh setup

# 2. Create optimized build
opaque-build nuitka main.py --name ProductionApp

# 3. Test thoroughly
./dist/ProductionApp

# 4. Package for distribution
# Create installer, ZIP, etc.
```

This guide should help you get started with building executables for your OPAQUE Framework applications. Choose the method that best fits your workflow and requirements.
