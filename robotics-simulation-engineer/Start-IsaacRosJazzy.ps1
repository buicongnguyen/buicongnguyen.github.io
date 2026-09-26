# Launch Isaac Sim, Zenoh, and ROS 2 Jazzy commands from NVIDIA's Pixi workspace in a clean process.
#
#   pwsh -File Start-IsaacRosJazzy.ps1 <action> [arguments passed through unchanged]
#
# Actions: verify | build | check | zenoh | sim | headless | ros2 | python | shell
#
# This is a plain script on purpose: an advanced script ([CmdletBinding()]) would claim ROS
# short flags such as -o, -p, -v, and -a as PowerShell common parameters.
#
# Environment overrides:
#   ISAAC_ROS_WS  Pixi workspace (default C:\IsaacSim-ros_workspaces\jazzy_ws)
#   PIXI_EXE      pixi executable (default: pixi on PATH, then %LOCALAPPDATA%\pixi\bin\pixi.exe)

$ErrorActionPreference = "Stop"
$actions = "verify", "build", "check", "zenoh", "sim", "headless", "ros2", "python", "shell"
$Action = if ($args.Count) { [string]$args[0] } else { "verify" }
$ActionArguments = if ($args.Count -gt 1) { @($args[1..($args.Count - 1)]) } else { @() }
if ($actions -notcontains $Action) {
    throw "Unknown action '$Action'. Use one of: $($actions -join ', ')."
}

$workspace = if ($env:ISAAC_ROS_WS) { $env:ISAAC_ROS_WS } else { "C:\IsaacSim-ros_workspaces\jazzy_ws" }
$manifest = Join-Path $workspace "pixi.toml"
$pixi = $env:PIXI_EXE
if (-not $pixi) {
    $found = Get-Command pixi -ErrorAction SilentlyContinue
    $pixi = if ($found) { $found.Source } else { Join-Path $env:LOCALAPPDATA "pixi\bin\pixi.exe" }
}
if (-not (Test-Path -LiteralPath $pixi)) {
    throw "Pixi was not found at $pixi. Install prefix-dev.pixi, open a new terminal, or set PIXI_EXE."
}
if (-not (Test-Path -LiteralPath $manifest)) {
    throw "The Jazzy Pixi workspace was not found at $workspace. Clone IsaacSim-ros_workspaces or set ISAAC_ROS_WS."
}

# Conda-style Python installs and some vendor SDKs put DLLs on PATH that shadow the ones
# rclpy needs. Drop them for this process and its children only; nothing global changes.
$shadowing = "*\miniconda3*", "*\anaconda3*", "*\miniforge3*", "*\mambaforge*", "*\Cognex\VisionPro\bin*"
$removed = @()
$cleanPath = foreach ($entry in ($env:PATH -split ";")) {
    if (-not $entry) { continue }
    if ($shadowing | Where-Object { $entry -like $_ }) { $removed += $entry; continue }
    $entry
}
$env:PATH = $cleanPath -join ";"
$env:CONDA_SHLVL = "0"
Remove-Item Env:CONDA_PREFIX -ErrorAction SilentlyContinue
Remove-Item Env:CONDA_DEFAULT_ENV -ErrorAction SilentlyContinue

Write-Host "Isaac ROS workspace: $workspace" -ForegroundColor Cyan
Write-Host "Removed $($removed.Count) conflicting PATH entries for this process only." -ForegroundColor DarkGray

# --manifest-path keeps the caller's working directory, so relative paths such as a bag
# output directory land where the user ran the command, not inside NVIDIA's checkout.
function Invoke-Pixi {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & $pixi @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "pixi $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

switch ($Action) {
    "verify" {
        $probe = @'
import importlib.util, json, os
spec = importlib.util.find_spec("isaacsim")
print(json.dumps({
    "ROS_DISTRO": os.getenv("ROS_DISTRO"),
    "RMW_IMPLEMENTATION": os.getenv("RMW_IMPLEMENTATION"),
    "ROS_DOMAIN_ID": os.getenv("ROS_DOMAIN_ID"),
    "isaac_sim_package_path": os.getenv("isaac_sim_package_path"),
    "pixi_isaacsim_package": spec.origin if spec else None,
}))
'@
        $raw = & $pixi run --manifest-path $manifest python -c $probe
        if ($LASTEXITCODE -ne 0) { throw "Python did not start in the Pixi environment." }
        $identity = ($raw | Select-Object -Last 1) | ConvertFrom-Json
        $identity | Format-List | Out-Host
        $problems = @()
        if ($identity.ROS_DISTRO -ne "jazzy") { $problems += "ROS_DISTRO is '$($identity.ROS_DISTRO)', expected 'jazzy'" }
        if ($identity.RMW_IMPLEMENTATION -ne "rmw_zenoh_cpp") { $problems += "RMW_IMPLEMENTATION is '$($identity.RMW_IMPLEMENTATION)', expected 'rmw_zenoh_cpp'" }
        if ($identity.ROS_DOMAIN_ID -notmatch '^\d+$') { $problems += "ROS_DOMAIN_ID is not set to a number" }
        if ($problems) { throw ("FAIL: " + ($problems -join "; ")) }
        Invoke-Pixi run --manifest-path $manifest ros2 pkg prefix rmw_zenoh_cpp
        Invoke-Pixi run --manifest-path $manifest ros2 pkg prefix isaac_ros2_messages
        Invoke-Pixi run --manifest-path $manifest ros2 pkg executables rmw_zenoh_cpp
        if ($identity.pixi_isaacsim_package) {
            Write-Host "Note: 'sim' and 'headless' run the pip-installed Isaac Sim inside this Pixi environment:" -ForegroundColor Yellow
            Write-Host "      $($identity.pixi_isaacsim_package)" -ForegroundColor Yellow
            Write-Host "      Record this path in your run manifest; it is not the standalone install." -ForegroundColor Yellow
        }
        Write-Host "PASS: Jazzy, Zenoh (domain $($identity.ROS_DOMAIN_ID)), and NVIDIA custom interfaces load in a clean process." -ForegroundColor Green
    }
    "build" { Invoke-Pixi run --manifest-path $manifest build @ActionArguments }
    "check" { Invoke-Pixi run --manifest-path $manifest check @ActionArguments }
    "shell" { & $pixi shell --manifest-path $manifest; exit $LASTEXITCODE }
    default {
        # Long-running and interactive actions end with Ctrl+C, which is not a launcher
        # failure: pass the child's exit code through instead of throwing.
        & $pixi run --manifest-path $manifest $Action @ActionArguments
        exit $LASTEXITCODE
    }
}
