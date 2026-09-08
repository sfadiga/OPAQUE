#!/usr/bin/env bash
# OPAQUE Framework developer tasks.
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.
#
# Every task goes through uv. uv owns the environment, the lock file and the
# interpreter, so there is no venv bootstrap here and no requirements.txt.
set -euo pipefail

ENTRYPOINT="examples/basic_example/main.py"

usage() {
    cat <<'USAGE'

~~~~~~~~ OPAQUE Framework developer tasks ~~~~~~~~

Usage: ./cicd.sh <task>

Tasks:
    setup       Create or update the environment from uv.lock
    test        Run the test suite
    check       Run mypy and pylint
    run         Run the reference example application
    dist        Build the wheel and the source distribution
    clean       Remove build output and __pycache__ directories
    build-exe   Build a standalone executable (see: uv run opaque-build --help)

USAGE
}

case "${1-}" in
    setup)     uv sync --all-extras ;;
    test)      uv run python -m pytest tests -q ;;
    check)
        # Run both tools and report both, then fail if either failed.
        # `mypy && pylint` hid pylint's output entirely while mypy was
        # dirty, and mypy is not clean yet.
        status=0
        uv run python -m mypy src/opaque || status=1
        uv run python -m pylint src/opaque || status=1
        exit "$status"
        ;;
    run)       uv run python "$ENTRYPOINT" ;;
    dist)      uv build ;;
    clean)
        rm -rf build dist ./*.egg-info
        # Prune the environments and the git directory first. Walking them
        # deletes the bytecode of every installed module for no benefit.
        find . -type d \( -name venv -o -name .venv -o -name .git \) -prune \
            -o -type d -name "__pycache__" -prune -exec rm -rf {} +
        ;;
    build-exe) shift; uv run opaque-build "$@" ;;
    -h|--help|"") usage ;;
    *) echo "ERROR: unknown task '${1}'" >&2; usage >&2; exit 1 ;;
esac
