# OPAQUE Framework CI/CD Script
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

# cicd.ps1
param(
    [string]$Task,
    [Parameter(ValueFromRemainingArguments)]
    [string[]]$Arguments
)

$VENV_NAME = "venv"
$VENV_PATH = "$VENV_NAME\Scripts"

function Activate-Venv {
    if ($env:VIRTUAL_ENV) {
        Write-Host "INFO: --- $VENV_NAME is already active ---"
    } else {
        Write-Host "INFO: --- Activate $VENV_NAME ---"
        $activateScript = "$VENV_PATH\Activate.ps1"
        if (Test-Path $activateScript) {
            & $activateScript
        } else {
            Write-Host "INFO: --- No $VENV_NAME found, setting up one ---"
            Project-Setup
            & $activateScript
        }
    }
}

# Build the command arguments
$bashArgs = @("cicd.sh")
if ($Task) {
    $bashArgs += $Task
}
if ($Arguments) {
    $bashArgs += $Arguments
}

# Execute based on task type
switch ($Task) {
    "venv" {
        Activate-Venv
    }
    { $_ -in @("run", "setup", "build", "clean", "dist", "test") } {
        & bash @bashArgs
    }
    default {
        if (-not $Task) {
            Write-Host ""
            Write-Host "~~~~~~~~ OPAQUE Framework scripts ~~~~~~~~"
            Write-Host ""
            Write-Host "Usage: .\cicd.ps1 [task] [options]"
            Write-Host ""
            Write-Host "Tasks:"
            Write-Host "    setup [-f]     Setup Python virtual environment"
            Write-Host "    clean          Clean build artifacts"
            Write-Host "    build          Build the framework"
            Write-Host "    run            Run the example application"
            Write-Host "    dist           Build Python wheel package"
            Write-Host "    venv           Activate virtual environment"
            Write-Host ""
        } else {
            & bash @bashArgs
        }
    }
}
