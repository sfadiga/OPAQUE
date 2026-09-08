# OPAQUE Framework developer tasks.
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.
#
# Every task goes through uv. The old script shelled out to bash, which is not
# present on a plain Windows machine.
param(
    [string]$Task,
    [Parameter(ValueFromRemainingArguments)]
    [string[]]$Arguments
)

$EntryPoint = "examples/basic_example/main.py"

function Show-Usage {
    Write-Host ""
    Write-Host "~~~~~~~~ OPAQUE Framework developer tasks ~~~~~~~~"
    Write-Host ""
    Write-Host "Usage: .\cicd.ps1 <task>"
    Write-Host ""
    Write-Host "Tasks:"
    Write-Host "    setup       Create or update the environment from uv.lock"
    Write-Host "    test        Run the test suite"
    Write-Host "    check       Run mypy and pylint"
    Write-Host "    run         Run the reference example application"
    Write-Host "    dist        Build the wheel and the source distribution"
    Write-Host "    clean       Remove build output and __pycache__ directories"
    Write-Host "    build-exe   Build a standalone executable"
    Write-Host ""
}

switch ($Task) {
    "setup" { uv sync --all-extras }
    "test"  { uv run python -m pytest tests -q }
    "check" { uv run python -m mypy src/opaque; if ($LASTEXITCODE -eq 0) { uv run python -m pylint src/opaque } }
    "run"   { uv run python $EntryPoint }
    "dist"  { uv build }
    "clean" {
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist
        Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
    }
    "build-exe" { uv run opaque-build @Arguments }
    default { Show-Usage }
}
