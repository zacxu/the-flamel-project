<# Build source-bound package in a disposable Git checkout. No hosting access. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$CandidateRoot,
    [Parameter(Mandatory=$true)][string]$ToolchainRoot,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [Parameter(Mandatory=$true)][string]$SourceCommit,
    [Parameter(Mandatory=$true)][string]$PythonExe
)
$ErrorActionPreference = 'Stop'
if ($SourceCommit -cnotmatch '^[a-f0-9]{40}$') { throw 'Use full immutable commit SHA.' }
$root = [IO.Path]::GetFullPath($CandidateRoot)
$helper = Join-Path $PSScriptRoot 'manual_ci.py'
$stageRoot = Join-Path $ToolchainRoot 'publication-stage'
$stageHelper = Join-Path $PSScriptRoot 'manual_stage.mjs'
& git -C $root diff --exit-code
if ($LASTEXITCODE -ne 0) { throw 'Candidate must start clean.' }
& git -C $root diff --cached --exit-code
if ($LASTEXITCODE -ne 0) { throw 'Candidate index must start clean.' }
$actualHead = (& git -C $root rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $actualHead -cne $SourceCommit) { throw 'Candidate commit mismatch.' }
# Only the package report and deterministic generated UI module may change in
# this disposable checkout. The guard derives the module identity from source bytes.
$before = @{}
$tracked = & git -C $root ls-files
if ($LASTEXITCODE -ne 0) { throw 'Cannot enumerate candidate source.' }
foreach ($relative in $tracked) {
    $before[$relative] = (Get-FileHash -LiteralPath (Join-Path $root $relative) -Algorithm SHA256).Hash
}
$installer = Join-Path $root 'scripts/github_publication/install_website.ps1'
& $installer -ProjectRoot $root -ToolchainRoot $ToolchainRoot -PythonExe $PythonExe
if ($LASTEXITCODE -ne 0) { throw 'Pinned website installation failed.' }
$node = Join-Path $ToolchainRoot 'node-v24.22.1-win-x64/node.exe'
$oldPython = $env:FLAMEL_PYTHON
$oldNode = $env:FLAMEL_NODE
try {
    $env:FLAMEL_PYTHON = $PythonExe
    $env:FLAMEL_NODE = $node
    Push-Location -LiteralPath (Join-Path $root 'website')
    try {
        & $node scripts/package-release.mjs
        if ($LASTEXITCODE -ne 0) { throw 'Static packaging failed.' }
        & $node $stageHelper "--website-root=$(Join-Path $root 'website')" "--stage-root=$stageRoot" --package=reports/W6_RELEASE_PACKAGE.json --stage
        if ($LASTEXITCODE -ne 0) { throw 'Publication guard/staging failed.' }
    } finally { Pop-Location }
    & $PythonExe -I -B $helper record-package --root $root --output $OutputDirectory --source-commit $SourceCommit --stage-root $stageRoot
    if ($LASTEXITCODE -ne 0) { throw 'Independent package verification failed.' }
} finally {
    $env:FLAMEL_PYTHON = $oldPython
    $env:FLAMEL_NODE = $oldNode
}
foreach ($relative in $tracked) {
    if ($relative -cnotin @('website/reports/W6_RELEASE_PACKAGE.json','website/src/generated/uiRelease.ts')) {
        if ((Get-FileHash -LiteralPath (Join-Path $root $relative) -Algorithm SHA256).Hash -cne $before[$relative]) {
            throw "Unexpected candidate input mutation: $relative"
        }
    }
}
Write-Output 'Verified exact source-bound package. NOT_DEPLOYED. No GitHub Release created.'
