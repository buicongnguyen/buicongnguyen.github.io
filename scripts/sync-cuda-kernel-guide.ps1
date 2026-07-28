param(
    [string]$Source,
    [string]$Destination = (Join-Path $PSScriptRoot '..\cuda_kernel\index.html')
)

if (-not $Source) {
    $candidates = @(
        (Join-Path $PSScriptRoot '..\..\Mercor_cuda\docs\index.html'),
        (Join-Path $PSScriptRoot '..\..\cuda_kernel\docs\index.html')
    )
    $Source = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if (-not $Source) {
        throw "CUDA guide source was not found. Pass -Source explicitly or place the sibling checkout at '..\Mercor_cuda' (preferred) or '..\cuda_kernel'."
    }
}

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
