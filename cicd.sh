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
    check)     uv run python -m mypy src/opaque && uv run python -m pylint src/opaque ;;
    run)       uv run python "$ENTRYPOINT" ;;
    dist)      uv build ;;
    clean)
        rm -rf build dist ./*.egg-info
        find . -type d -name "__pycache__" -prune -exec rm -rf {} +
        ;;
    build-exe) shift; uv run opaque-build "$@" ;;
    -h|--help|"") usage ;;
    *) echo "ERROR: unknown task '${1}'"; usage; exit 1 ;;
esac
