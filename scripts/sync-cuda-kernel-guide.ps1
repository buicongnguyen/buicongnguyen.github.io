param(
    [string]$Source = (Join-Path $PSScriptRoot '..\..\cuda_kernel\docs\index.html'),
    [string]$Destination = (Join-Path $PSScriptRoot '..\cuda_kernel\index.html')
)

$sourcePath = Resolve-Path -LiteralPath $Source -ErrorAction Stop
$destinationPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Destination)
$destinationDir = Split-Path -Parent $destinationPath

New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
Copy-Item -LiteralPath $sourcePath.Path -Destination $destinationPath -Force

$sourceHash = Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePath.Path
$destinationHash = Get-FileHash -Algorithm SHA256 -LiteralPath $destinationPath

if ($sourceHash.Hash -ne $destinationHash.Hash) {
    throw "CUDA guide sync failed: copied file hash does not match source."
}

Write-Output "Synced CUDA guide to $destinationPath"
