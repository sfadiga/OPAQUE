# OPAQUE Framework CI/CD Script
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

PROJECT="opaque"
PROJECT_FILE="pyproject.toml"

# cmd line args
firstArg="${1}"
secondArg="${2}"

# paths
VENV_NAME="venv"
VENV_PATH=$VENV_NAME/Scripts
SOURCE_PATH="src"
FORMS_PATH=$SOURCE_PATH/"forms"
RESOURCES_PATH="resources"
RELEASE_PATH="dist"
TESTS_PATH="tests"
ENTRYPOINT="examples/basic_example/main.py"

function _read_version_from_file() 
{
    local version_file="${PROJECT}-VERSION.txt"
    if [ -f "$version_file" ]; then
        release_version=$(cat "$version_file" | tr -d '[:space:]')
        echo "INFO: Version read from $version_file: $release_version"
        # Set the environment variable
        export version="$release_version"        
    else
        echo "ERROR: Version file $version_file not found."
        exit 1
    fi
}

function project_setup()
{
    local force_recreate=false
    # Check if -f flag is passed
    if [[ "$1" == "-f" ]] || [[ "$secondArg" == "-f" ]]; then
        force_recreate=true
    fi
    echo "--- Bootstrap Python virtual environment ---"
    if [ -d "$VENV_NAME" ] && [ "$force_recreate" = true ]; then
        echo "INFO: Force flag detected. Removing existing virtual environment..."
        rm -rf "$VENV_NAME"
    fi
    if [ ! -d "$VENV_NAME" ]; then
        echo "INFO: Creating virtual environment..."
        echo python -m venv $VENV_NAME
        python -m venv $VENV_NAME
        echo "--- Installing Project Requirements ---"
        echo $VENV_PATH/pip install --force-reinstall -r requirements.txt
        $VENV_PATH/pip install --force-reinstall -r requirements.txt
    elif [ "$force_recreate" = false ]; then
        echo "INFO: Virtual environment already exists. Use 'setup -f' to force recreate."
    fi
    return 0
}

function activate_venv()
{
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        echo "INFO: --- $VENV_NAME is already active ---"
        INVENV=1
    else
        echo "INFO: --- Activate $VENV_NAME ---"
        source $VENV_PATH/activate
        ACTIVATE_EXIT_CODE=$?
        if [[ $ACTIVATE_EXIT_CODE != 0 ]]; then
            echo "INFO: --- No $VENV_NAME found, setup one ---"
            setup
            source $VENV_PATH/activate
        fi
    fi
    return 0
}

function clean()
{
    # cleanup ui_*.py from source folder, they will be generated later
    echo "INFO: Clean-up ui_*.py files"
    rm -f ./$UI_PATH/ui_*.py
    rm -f rc_qresource.py
    rm -f rc_qresource.pyd
    echo "INFO: Clean-up logs"
    rm -f ./logs/*.log
    echo "INFO: Clean-up __pycache__ files"
    find . -type d -name "__pycache__" -exec rm -rf {} +
    echo "INFO: Egg info files"
    rm -rf ./*.egg-info
    echo "INFO: build"
    rm -rf ./build
    echo "INFO: dist"
    rm -rf ./dist
    return 0
}

function build()
{
    project_setup
    activate_venv
    clean

    # Resource building is optional for OPAQUE framework
    if [ -f "./$RESOURCES_PATH/qresource.qrc" ]; then
        echo "INFO: Building Resource file..."
        echo "$VENV_PATH"/pyside6-rcc ./$RESOURCES_PATH/qresource.qrc -o rc_qresource.py
        $VENV_PATH/pyside6-rcc ./$RESOURCES_PATH/qresource.qrc -o rc_qresource.py
    fi
    
    echo "INFO: Building ${PROJECT} framework..."
    # For a Python package, we typically don't need pyside6-project
    # Just ensure the package is properly structured
    echo "INFO: Framework is ready for use"

}

function run()
{
    local force_build=false
    # Check if -f flag is passed
    if [[ "$1" == "-b" ]] || [[ "$secondArg" == "-b" ]]; then
        force_build=true
    fi
 
    if [ "$force_build" = true ]; then
        echo "INFO: Force build detected. Performing a build before run..."
        build
    else
        project_setup
        activate_venv
    fi

    echo "INFO: Running OPAQUE example"
    echo "$VENV_PATH"/python $ENTRYPOINT
    $VENV_PATH/python $ENTRYPOINT
}

function dist()
{
    project_setup
    activate_venv
    clean

    echo "INFO: Building Python wheel package..."
    python -m build
}

function build_exe_pyinstaller()
{
    local entry_point="${1:-$ENTRYPOINT}"
    local extra_args="${@:2}"
    
    project_setup
    activate_venv
    
    echo "INFO: Building executable with PyInstaller..."
    echo "INFO: Entry point: $entry_point"
    
    # Check if PyInstaller is available
    if ! python -c "import PyInstaller" 2>/dev/null; then
        echo "INFO: PyInstaller not found, installing..."
        $VENV_PATH/pip install pyinstaller
    fi
    
    # Use opaque-build CLI if available, otherwise use PyInstaller directly
    if python -c "from opaque.build_tools.cli import main" 2>/dev/null; then
        echo "INFO: Using OPAQUE build tools..."
        python -m opaque.build_tools.cli pyinstaller "$entry_point" $extra_args
    else
        echo "INFO: Using PyInstaller directly..."
        $VENV_PATH/pyinstaller --onefile --windowed "$entry_point" $extra_args
    fi
    
    echo "INFO: PyInstaller build completed!"
}

function build_exe_nuitka()
{
    local entry_point="${1:-$ENTRYPOINT}"
    local extra_args="${@:2}"
    
    project_setup
    activate_venv
    
    echo "INFO: Building executable with Nuitka..."
    echo "INFO: Entry point: $entry_point"
    
    # Check if Nuitka is available
    if ! python -c "import nuitka" 2>/dev/null; then
        echo "INFO: Nuitka not found, installing..."
        $VENV_PATH/pip install nuitka
    fi
    
    # Use opaque-build CLI if available, otherwise use Nuitka directly
    if python -c "from opaque.build_tools.cli import main" 2>/dev/null; then
        echo "INFO: Using OPAQUE build tools..."
        python -m opaque.build_tools.cli nuitka "$entry_point" $extra_args
    else
        echo "INFO: Using Nuitka directly..."
        $VENV_PATH/nuitka --standalone --onefile --enable-plugin=pyside6 --windows-disable-console "$entry_point" $extra_args
    fi
    
    echo "INFO: Nuitka build completed!"
}

function build_exe()
{
    local builder="${1}"
    local entry_point="${2:-$ENTRYPOINT}"
    local extra_args="${@:3}"
    
    case $builder in
        pyinstaller)
            build_exe_pyinstaller "$entry_point" $extra_args
            ;;
        nuitka)
            build_exe_nuitka "$entry_point" $extra_args
            ;;
        *)
            echo "ERROR: Unknown builder '$builder'. Use 'pyinstaller' or 'nuitka'"
            echo ""
            echo "Available builders:"
            echo "  pyinstaller  - Build with PyInstaller (fast build, larger executable)"
            echo "  nuitka       - Build with Nuitka (slower build, optimized executable)"
            echo ""
            echo "Usage examples:"
            echo "  $0 build-exe pyinstaller"
            echo "  $0 build-exe nuitka"
            echo "  $0 build-exe pyinstaller examples/my_example/main.py"
            echo "  $0 build-exe nuitka examples/my_example/main.py --name MyApp"
            exit 1
            ;;
    esac
}

function usage()
{
    echo ""
    echo "~~~~~~~~ OPAQUE Framework scripts ~~~~~~~~"
    echo ""
    echo "Usage: $0 [task] [options]"
    echo ""
    echo "Tasks:"
    echo ""
    echo "    setup [-f]           Setup Python virtual environment"
    echo "                         -f: Force recreate venv and reinstall requirements"
    echo "    clean                Clean build artifacts and cache files"
    echo "    build                Build the application"
    echo "    run   [-b]           Run the application"
    echo "                         -b: Force build befor run"
    echo "    test                 Run tests"
    echo "    dist                 Build the Python wheel package"
    echo "    build-exe <builder> [entry_point] [options]"
    echo "                         Build standalone executable"
    echo "                         builder: pyinstaller or nuitka"
    echo "                         entry_point: Python file to build (default: $ENTRYPOINT)"
    echo "    venv                 Activate virtual environment"
    echo ""
    echo "   -h, --help            Display this usage message"
    echo ""
    echo "Examples:"
    echo "    $0 setup             # Setup project for first time (skip if venv exists)"
    echo "    $0 setup -f          # Force recreate venv and reinstall requirements"
    echo "    $0 build             # Build the application"
    echo "    $0 run               # Run application"
    echo "    $0 run -b            # Force a build before Run application"
    echo "    $0 dist              # Build the Python wheel package"
    echo "    $0 build-exe pyinstaller"
    echo "                         # Build executable with PyInstaller (default entry point)"
    echo "    $0 build-exe nuitka examples/my_example/main.py"
    echo "                         # Build specific example with Nuitka"
    echo "    $0 build-exe pyinstaller examples/my_example/main.py --name MyApp"
    echo "                         # Build with custom name and options"
    echo ""
    exit 0
}


if [ -z $firstArg ]
then
    echo "error: invalid usage."
    usage
    exit 1
fi

case $firstArg in
    
    -h|--help)
        usage
        ;;
    setup)
        project_setup $secondArg
        ;;
    venv)
        activate_venv
        ;;
    clean)
        clean
        ;;
    build)
        build
        ;;
    run)
        run $secondArg
        ;;
    test)
        test
        ;;
    dist)
        dist
        ;;
    build-exe)
        build_exe $secondArg "${@:3}"
        ;;
    upload)
        upload $secondArg
        ;;
    *)
        echo ""
        echo "ERROR: Unknown build type $firstArg"
        echo ""
        exit 1
        ;;
esac
