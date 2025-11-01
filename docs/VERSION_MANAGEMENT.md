# Version Management System

The OPAQUE framework provides a comprehensive version management system that automatically detects, displays, and manages version information throughout your application lifecycle.

## Overview

The version management system consists of several components:

- **VersionManager Service**: Automatically detects version information from multiple sources
- **Version UI Components**: Displays version information in dialogs and status widgets
- **Build Tool Integration**: Injects version information into executables
- **Configuration Integration**: Seamlessly integrates with application configuration

## Version Detection

### Automatic Detection Sources

The `VersionManager` automatically detects version information from these sources (in priority order):

1. **pyproject.toml** - Project metadata and version
2. **setup.py** - Legacy Python packaging information  
3. ****init**.py** - Module-level version constants
4. **Git repository** - Commit hash and tag information
5. **Environment variables** - Build system injected values

### Version Information Structure

The system collects the following version attributes:

```python
{
    "version": "1.0.0",              # Main version number
    "product_name": "My Application", # Application name
    "description": "App description", # Brief description
    "company": "My Company",          # Organization/company
    "copyright": "© 2025 My Company", # Copyright notice
    "build_date": "2025-01-01",      # Build timestamp
    "build_number": "123",            # Build identifier
    "commit_hash": "abc123...",       # Git commit hash
    "build_tool": "PyInstaller"      # Tool used for building
}
```

## Configuration Integration

### Default Configuration

The framework automatically integrates version management into your application configuration:

```python
from opaque.models.configuration import DefaultApplicationConfiguration

class MyAppConfig(DefaultApplicationConfiguration):
    def __init__(self):
        super().__init__()
        # Version information is automatically available
        # via self.version_manager.get_version_info()
```

### Custom Version Configuration

You can override or supplement version information:

```python
from opaque.services.version_service import VersionManager

class CustomVersionManager(VersionManager):
    def get_version_info(self) -> Dict[str, Any]:
        # Get base version info
        info = super().get_version_info()
        
        # Add custom information
        info.update({
            "custom_field": "Custom Value",
            "license": "MIT License",
            "support_url": "https://myapp.com/support"
        })
        
        return info

# Use in your configuration
class MyAppConfig(DefaultApplicationConfiguration):
    def __init__(self):
        super().__init__()
        self.version_manager = CustomVersionManager()
```

## UI Components

### Version Information Dialog

Display comprehensive version information in a tabbed dialog:

```python
from opaque.view.dialogs.version_info import VersionInfoDialog

# Show version dialog
version_info = self.configuration.version_manager.get_version_info()
dialog = VersionInfoDialog(version_info, parent=self)
dialog.exec()
```

### Status Bar Version Widget

Add a clickable version display to your status bar:

```python
from opaque.view.dialogs.version_info import VersionStatusWidget

# Create status widget
version_widget = VersionStatusWidget(version_info)
self.status_bar.addPermanentWidget(version_widget)

# Widget shows "v1.0.0 (Build 123)" and opens dialog when clicked
```

### About Dialog

Create professional about dialogs with version information:

```python
from opaque.view.dialogs.version_info import AboutDialog

# Show about dialog
about_dialog = AboutDialog(
    version_info=version_info,
    app_icon=self.windowIcon(),
    parent=self
)
about_dialog.exec()
```

## Build Tool Integration

### Automatic Version Injection

The build tools automatically inject version information into executables:

```bash
# PyInstaller with version info
opaque-build pyinstaller src/my_app/main.py --name "MyApp" --version "1.2.0"

# Nuitka with version info  
opaque-build nuitka src/my_app/main.py --name "MyApp" --version "1.2.0"
```

### Version File Generation

Build tools create version resource files:

**PyInstaller version file (version_info.py):**

```python
VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=(1, 2, 0, 123),
        prodvers=(1, 2, 0, 123),
        # ... additional version information
    ),
    kids=[
        StringFileInfo([
            StringTable('040904B0', [
                StringStruct('CompanyName', 'My Company'),
                StringStruct('FileDescription', 'My Application'),
                StringStruct('FileVersion', '1.2.0.123'),
                StringStruct('ProductName', 'My Application'),
                StringStruct('ProductVersion', '1.2.0'),
            ])
        ]),
        VarFileInfo([VarStruct('Translation', [1033, 1200])])
    ]
)
```

**Nuitka version parameters:**

```
--windows-company-name="My Company"
--windows-product-name="My Application" 
--windows-file-version="1.2.0.123"
--windows-product-version="1.2.0"
--windows-file-description="My Application"
```

### CI/CD Integration

The version system integrates with CI/CD pipelines:

```bash
# Use build scripts with version detection
./cicd.sh build_pyinstaller_exe "MyApp" "auto"  # Auto-detects version
./cicd.sh build_nuitka_exe "MyApp" "1.2.0"      # Explicit version

# PowerShell equivalent
.\cicd.ps1 Build-PyInstallerExe -AppName "MyApp" -Version "auto"
.\cicd.ps1 Build-NuitkaExe -AppName "MyApp" -Version "1.2.0"
```

## Version Sources Configuration

### pyproject.toml

Configure version and metadata in your project file:

```toml
[project]
name = "my-application"
version = "1.2.0"
description = "My awesome application"
authors = [{name = "My Name", email = "my.name@example.com"}]

[project.urls]
Homepage = "https://myapp.com"
Repository = "https://github.com/myuser/myapp"
```

### setup.py (Legacy)

For legacy Python projects:

```python
from setuptools import setup

setup(
    name="my-application",
    version="1.2.0",
    description="My awesome application",
    author="My Name",
    author_email="my.name@example.com",
    # ... other setup parameters
)
```

### Module Version Constants

Define version in your package's `__init__.py`:

```python
# src/my_app/__init__.py
__version__ = "1.2.0"
__author__ = "My Name"
__email__ = "my.name@example.com"
__description__ = "My awesome application"
```

### Environment Variables

Set version information via environment variables (useful for CI/CD):

```bash
export APP_VERSION="1.2.0"
export APP_BUILD_NUMBER="123" 
export APP_BUILD_DATE="2025-01-01T10:00:00Z"
export APP_COMMIT_HASH="abc123def456"
```

## Advanced Usage

### Runtime Version Updates

Update version information at runtime:

```python
# Get current version manager
version_manager = self.configuration.version_manager

# Update version info
version_manager.update_version_info({
    "build_number": "456",
    "custom_status": "Production"
})

# Refresh UI components
version_widget.set_version_info(version_manager.get_version_info())
```

### Version Comparison

Compare versions programmatically:

```python
from opaque.services.version_service import VersionManager

version_manager = VersionManager()
current_version = version_manager.get_version_info()["version"]

def is_newer_version(version1: str, version2: str) -> bool:
    """Compare semantic versions."""
    v1_parts = [int(x) for x in version1.split('.')]
    v2_parts = [int(x) for x in version2.split('.')]
    
    # Pad with zeros if needed
    max_len = max(len(v1_parts), len(v2_parts))
    v1_parts.extend([0] * (max_len - len(v1_parts)))
    v2_parts.extend([0] * (max_len - len(v2_parts)))
    
    return v1_parts > v2_parts
```

### Custom Version Detection

Implement custom version detection logic:

```python
from opaque.services.version_service import VersionManager
from typing import Dict, Any
import requests

class CloudVersionManager(VersionManager):
    def __init__(self, api_url: str):
        super().__init__()
        self.api_url = api_url
    
    def get_version_info(self) -> Dict[str, Any]:
        # Get local version info
        info = super().get_version_info()
        
        try:
            # Fetch additional info from cloud service
            response = requests.get(f"{self.api_url}/version")
            if response.ok:
                cloud_info = response.json()
                info.update({
                    "latest_version": cloud_info.get("latest"),
                    "update_available": cloud_info.get("update_available"),
                    "release_notes_url": cloud_info.get("release_notes")
                })
        except Exception:
            pass  # Gracefully handle network errors
            
        return info
```

## Best Practices

### Version Numbering

Use semantic versioning (SemVer) for consistency:

- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- **MAJOR**: Breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

### Build Numbers

Use incremental build numbers for tracking:

- Increment automatically in CI/CD
- Include in executable resources
- Display in debug/support contexts

### Git Integration

Tag releases in Git for version tracking:

```bash
# Create version tag
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin v1.2.0

# Version manager will automatically detect tags
```

### Distribution

Include version information in all distributions:

- Executable files (via build tools)
- Python packages (via setup.py/pyproject.toml)
- Documentation and README files
- Release notes and changelogs

## Troubleshooting

### Version Not Detected

If version information isn't detected automatically:

1. Check that pyproject.toml or setup.py exists
2. Verify version format is valid (SemVer recommended)
3. Ensure Git repository is initialized if using Git detection
4. Check environment variables are set correctly

### Build Tool Issues

If version injection fails during building:

1. Verify the version string format is valid
2. Check file permissions for generated version files
3. Ensure required build dependencies are installed
4. Review build logs for specific error messages

### UI Display Problems

If version UI components don't show correctly:

1. Ensure version_info dictionary is properly formatted
2. Check that parent widgets are properly set
3. Verify Qt/PySide6 is correctly installed
4. Test with minimal version information first

## Examples

See the `examples/` directory for complete working examples:

- `examples/basic_example/` - Basic version management setup
- `examples/version_example/` - Advanced version configuration
- `build/` - Sample build configurations and scripts

## API Reference

For detailed API documentation, see:

- [VersionManager API](API_REFERENCE.md#versionmanager)
- [Version UI Components](API_REFERENCE.md#version-ui-components)
- [Build Tools API](API_REFERENCE.md#build-tools)
