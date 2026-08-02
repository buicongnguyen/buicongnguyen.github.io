[CmdletBinding()]
param(
    [ValidateSet("verify", "build", "check", "zenoh", "sim", "headless", "ros2", "shell")]
    [string]$Action = "verify",

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ActionArguments
)

$ErrorActionPreference = "Stop"
$workspace = "C:\IsaacSim-ros_workspaces\jazzy_ws"
$pixi = "C:\Users\n\AppData\Local\pixi\bin\pixi.exe"

if (-not (Test-Path -LiteralPath $pixi)) {
    throw "Pixi was not found at $pixi. Open a new terminal or reinstall prefix-dev.pixi."
}
if (-not (Test-Path -LiteralPath (Join-Path $workspace "pixi.toml"))) {
    throw "The Jazzy workspace was not found at $workspace."
}

# This changes PATH only inside this launcher process and its children. Both directories
# were proven on this PC to shadow DLLs required by rclpy. Their installations are untouched.
$removed = @()
$cleanPath = foreach ($entry in ($env:PATH -split ";")) {
    if (-not $entry) { continue }
    if ($entry -like "*\miniconda3*") { $removed += $entry; continue }
    if ($entry -like "*\Cognex\VisionPro\bin*") { $removed += $entry; continue }
    $entry
}
$env:PATH = $cleanPath -join ";"
$env:CONDA_SHLVL = "0"
Remove-Item Env:CONDA_PREFIX -ErrorAction SilentlyContinue
Remove-Item Env:CONDA_DEFAULT_ENV -ErrorAction SilentlyContinue

Set-Location -LiteralPath $workspace
Write-Host "Isaac ROS workspace: $workspace" -ForegroundColor Cyan
Write-Host "Removed $($removed.Count) conflicting PATH entries for this process only." -ForegroundColor DarkGray

function Invoke-Pixi {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & $pixi @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "pixi $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

switch ($Action) {
    "verify" {
        Invoke-Pixi run python -c "import os; print({k: os.getenv(k) for k in ['ROS_DISTRO','RMW_IMPLEMENTATION','ROS_DOMAIN_ID','isaac_sim_package_path']})"
        Invoke-Pixi run ros2 pkg prefix rmw_zenoh_cpp
        Invoke-Pixi run ros2 pkg prefix isaac_ros2_messages
        Invoke-Pixi run ros2 pkg executables rmw_zenoh_cpp
        Write-Host "PASS: Jazzy, Zenoh, and NVIDIA custom interfaces load in a clean process." -ForegroundColor Green
    }
    "ros2" { Invoke-Pixi run ros2 @ActionArguments }
    "shell" { Invoke-Pixi shell }
    default { Invoke-Pixi run $Action @ActionArguments }
}
