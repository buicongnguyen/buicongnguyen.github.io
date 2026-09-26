# Mirror the CUDA kernel guide from the private sibling checkout ..\cuda_kernel into
# cuda_kernel\. The guide is docs\index.html plus the files it loads (theme-toggle.js),
# so the whole docs folder is copied. ..\Mercor_cuda is a different project (a multi-page
# assessment book) and is not the source of this page.
param(
    [string]$Source = (Join-Path $PSScriptRoot '..\..\cuda_kernel\docs'),
    [string]$Destination = (Join-Path $PSScriptRoot '..\cuda_kernel')
)

$ErrorActionPreference = "Stop"

# Earlier usage passed the page itself; accept that and mirror its folder.
if (Test-Path -LiteralPath $Source -PathType Leaf) {
    $Source = Split-Path -Parent $Source
}
if (-not (Test-Path -LiteralPath (Join-Path $Source 'index.html') -PathType Leaf)) {
    throw "CUDA guide source not found at '$Source'. Clone the private cuda_kernel repo next to this one or pass -Source <docs folder>."
}

$sourceDir = (Resolve-Path -LiteralPath $Source).Path
$destinationDir = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Destination)
New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
$destinationDir = (Resolve-Path -LiteralPath $destinationDir).Path

function Get-RelativePath([string]$Root, [string]$FullName) {
    $FullName.Substring($Root.Length).TrimStart('\', '/')
}

$files = @(Get-ChildItem -LiteralPath $sourceDir -File -Recurse)
foreach ($file in $files) {
    $relative = Get-RelativePath $sourceDir $file.FullName
    $target = Join-Path $destinationDir $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $target -Force
    $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash
    $targetHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash
    if ($sourceHash -ne $targetHash) {
        throw "CUDA guide sync failed: $relative does not match the source."
    }
}

$sourceNames = $files | ForEach-Object { Get-RelativePath $sourceDir $_.FullName }
Get-ChildItem -LiteralPath $destinationDir -File -Recurse |
    Where-Object { (Get-RelativePath $destinationDir $_.FullName) -notin $sourceNames } |
    ForEach-Object { Write-Warning "Not in the source guide (left in place): $($_.FullName)" }

Write-Output "Synced $($files.Count) CUDA guide file(s) from $sourceDir to $destinationDir"
