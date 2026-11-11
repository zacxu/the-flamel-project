<#
.SYNOPSIS
Install the frozen website from a clean source copy using standalone pinned tools.
.DESCRIPTION
Windows x64 / Windows PowerShell 5.1+. No Codex or global Node/npm dependency.
The npm lock is preserved. Package lifecycle scripts are disabled.
Use -ValidateSavedEvidence only on a disposable source copy: existing validators
write their dated reports in that copy. This command never deploys a website.
#>
[CmdletBinding()]
param(
    [string]$ProjectRoot,
    [Parameter(Mandatory=$true)][string]$ToolchainRoot,
    [string]$PythonExe,
    [switch]$ValidateSavedEvidence
)
$ErrorActionPreference = 'Stop'
if (-not $ProjectRoot) { $ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot) }
$nodeVersion = '24.22.1'
$npmVersion = '12.2.1'
$zipName = "node-v$nodeVersion-win-x64.zip"
$nodeArchiveSha = 'd2046d28c2c3dcd211ac5145c0bf30e2047ef9dfb306693c8c6e2eccd8b95fa5'
# The canonical npm bootstrap uses this SHA-512 in base64; compare that form below.
$npmIntegrity = 'sha512-bKCmFRVT/BB+YPEYbZwQ1XUI3N5t4xKSpU1MxOjo7z3iWzKBJ0ZXRC1xFdEN+TC7N5TdywaBzf2dMXGJq/e2PQ=='
function Assert-NoReparse([string]$Candidate) {
    $item = [System.IO.Path]::GetFullPath($Candidate)
    while ($item) {
        if (Test-Path -LiteralPath $item) {
            $info = Get-Item -LiteralPath $item -Force
            if (($info.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse paths are not accepted for installation.' }
        }
        $next = Split-Path -Parent $item
        if ($next -eq $item) { break }
        $item = $next
    }
}
function File-Sha([string]$Path, [string]$Algorithm = 'SHA256') {
    return (Get-FileHash -LiteralPath $Path -Algorithm $Algorithm).Hash.ToLowerInvariant()
}
Assert-NoReparse $ProjectRoot
Assert-NoReparse $ToolchainRoot
$project = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\')
$tools = [System.IO.Path]::GetFullPath($ToolchainRoot).TrimEnd('\')
if ($tools -eq $project -or $tools.StartsWith($project + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'ToolchainRoot must be outside the project.' }
$website = Join-Path $project 'website'
$packagePath = Join-Path $website 'package.json'
$lockPath = Join-Path $website 'package-lock.json'
foreach ($inputPath in @($packagePath,$lockPath,(Join-Path $website 'scripts\bootstrap-npm.mjs'))) {
    Assert-NoReparse $inputPath
    if (-not (Test-Path -LiteralPath $inputPath -PathType Leaf)) { throw 'Expected website source files are missing.' }
}
$packageBefore = File-Sha $packagePath
$lockBefore = File-Sha $lockPath
$package = Get-Content -LiteralPath $packagePath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($package.packageManager -ne "npm@$npmVersion" -or $package.engines.npm -ne $npmVersion) { throw 'The source declares a different npm version; review the installer pins.' }
if ($ValidateSavedEvidence -and -not $PythonExe) { throw 'Saved-evidence validation requires an explicit standalone PythonExe.' }
if ($PythonExe) {
    Assert-NoReparse $PythonExe
    if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) { throw 'PythonExe does not exist.' }
}
New-Item -ItemType Directory -Path $tools -Force | Out-Null
$archive = Join-Path $tools $zipName
if (-not (Test-Path -LiteralPath $archive)) {
    $partial = $archive + '.partial'
    if (Test-Path -LiteralPath $partial) { throw 'A previous partial download exists; inspect/remove it before retrying.' }
    Invoke-WebRequest -UseBasicParsing -Uri "https://nodejs.org/dist/v$nodeVersion/$zipName" -OutFile $partial
    if ((File-Sha $partial) -ne $nodeArchiveSha) { throw 'Official Node archive checksum mismatch.' }
    Move-Item -LiteralPath $partial -Destination $archive
}
if ((File-Sha $archive) -ne $nodeArchiveSha) { throw 'Cached Node archive checksum mismatch.' }
$nodeFolder = Join-Path $tools "node-v$nodeVersion-win-x64"
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($archive)
try {
    foreach ($entry in $zip.Entries) {
        $name = $entry.FullName
        if ($name -notlike "node-v$nodeVersion-win-x64/*" -or $name.Contains('\') -or $name.Contains(':') -or $name.Split('/') -contains '..') { throw 'Unexpected Node archive path.' }
        if ((($entry.ExternalAttributes -shr 16) -band 61440) -eq 40960) { throw 'Archive symlinks are not accepted.' }
    }
} finally { $zip.Dispose() }
if (-not (Test-Path -LiteralPath $nodeFolder)) { Expand-Archive -LiteralPath $archive -DestinationPath $tools }
Assert-NoReparse $nodeFolder
# Reuse never trusts an executable's reported version alone: verify all files
# against the independently pinned release archive.
$zip = [System.IO.Compression.ZipFile]::OpenRead($archive)
$expectedFiles = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
try {
    foreach ($entry in $zip.Entries) {
        if ($entry.FullName.EndsWith('/')) { continue }
        $target = Join-Path $tools $entry.FullName.Replace('/', '\')
        Assert-NoReparse $target
        if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw 'Installed Node toolchain file is missing.' }
        $null = $expectedFiles.Add([System.IO.Path]::GetFullPath($target))
        $hasher = [Security.Cryptography.SHA256]::Create()
        $stream = $entry.Open()
        try { $entryHash = [BitConverter]::ToString($hasher.ComputeHash($stream)).Replace('-','').ToLowerInvariant() }
        finally { $stream.Dispose(); $hasher.Dispose() }
        if ((File-Sha $target) -ne $entryHash) { throw 'Installed Node toolchain bytes differ from the pinned archive.' }
    }
    foreach ($file in Get-ChildItem -LiteralPath $nodeFolder -File -Recurse -Force) {
        if (-not $expectedFiles.Contains($file.FullName)) { throw 'Unexpected file in the pinned Node toolchain.' }
    }
} finally { $zip.Dispose() }
$nodeExe = Join-Path $nodeFolder 'node.exe'
$settings = Join-Path $tools 'flamel-npm-settings'
New-Item -ItemType Directory -Path $settings -Force | Out-Null
foreach ($configName in @('empty-user.npmrc','empty-global.npmrc')) {
    $configPath = Join-Path $settings $configName
    if ((Test-Path -LiteralPath $configPath) -and (Get-Item -LiteralPath $configPath).Length -ne 0) { throw 'Expected empty npm config was changed.' }
    [IO.File]::WriteAllText($configPath,'')
}
# A version-matching old npm folder is insufficient without its pinned archive.
$npmArchive = Join-Path $website ".tooling\npm-$npmVersion.tgz"
$npmFolder = Join-Path $website '.tooling\npm'
if ((Test-Path -LiteralPath $npmFolder) -and -not (Test-Path -LiteralPath $npmArchive)) { throw 'Existing npm tooling lacks its verified source archive. Use a clean copy.' }
$environmentBefore = @{}
foreach ($item in Get-ChildItem Env:) { $environmentBefore[$item.Name] = $item.Value }
$keep = @('SYSTEMROOT','WINDIR','TEMP','TMP','USERPROFILE','COMSPEC','PATHEXT','NUMBER_OF_PROCESSORS','PROCESSOR_ARCHITECTURE')
$commands = New-Object 'System.Collections.Generic.List[object]'
function Invoke-PinnedNode([string]$Label, [string[]]$NodeArguments) {
    $timer = [Diagnostics.Stopwatch]::StartNew()
    & $nodeExe @NodeArguments
    $code = $LASTEXITCODE
    $timer.Stop()
    $commands.Add([pscustomobject]@{label=$Label; arguments=$NodeArguments; exit_code=$code; seconds=$timer.Elapsed.TotalSeconds})
    if ($code -ne 0) { throw "Pinned command failed: $Label (exit $code)." }
}
Push-Location $website
try {
    foreach ($item in Get-ChildItem Env:) { if ($keep -notcontains $item.Name) { Remove-Item -LiteralPath ("Env:" + $item.Name) } }
    $env:PATH = $nodeFolder + ';' + $env:SystemRoot + '\System32;' + $env:SystemRoot + ';' + $env:SystemRoot + '\System32\WindowsPowerShell\v1.0'
    $env:FLAMEL_NODE = $nodeExe
    if ($PythonExe) { $env:FLAMEL_PYTHON = [IO.Path]::GetFullPath($PythonExe) }
    $temporary = Join-Path $tools 'temporary'
    New-Item -ItemType Directory -Path $temporary -Force | Out-Null
    $env:TEMP = $temporary
    $env:TMP = $temporary
    $env:PYTHONUTF8 = '1'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:NPM_CONFIG_USERCONFIG = Join-Path $settings 'empty-user.npmrc'
    $env:NPM_CONFIG_GLOBALCONFIG = Join-Path $settings 'empty-global.npmrc'
    $env:NPM_CONFIG_REGISTRY = 'https://registry.npmjs.org/'
    $env:NPM_CONFIG_CACHE = Join-Path $tools 'npm-cache'
    $env:NPM_CONFIG_IGNORE_SCRIPTS = 'true'
    $env:NPM_CONFIG_AUDIT = 'false'
    Invoke-PinnedNode 'node-version' @('--version')
    Invoke-PinnedNode 'npm-bootstrap' @('scripts/bootstrap-npm.mjs')
    $hasher = [Security.Cryptography.SHA512]::Create()
    $stream = [IO.File]::OpenRead($npmArchive)
    try { $actualIntegrity = 'sha512-' + [Convert]::ToBase64String($hasher.ComputeHash($stream)) }
    finally { $stream.Dispose(); $hasher.Dispose() }
    if ($actualIntegrity -ne $npmIntegrity) { throw 'npm bootstrap archive integrity mismatch.' }
    Invoke-PinnedNode 'npm-tooling-integrity' @((Join-Path $PSScriptRoot 'verify_npm_tooling.mjs'),$website)
    $npmCli = Join-Path $npmFolder 'bin\npm-cli.js'
    Invoke-PinnedNode 'npm-version' @($npmCli,'--version')
    Invoke-PinnedNode 'npm-ci' @($npmCli,'ci','--ignore-scripts','--no-audit','--no-fund')
    Invoke-PinnedNode 'dependency-tree' @($npmCli,'ls','--all','--json')
    Invoke-PinnedNode 'typecheck' @($npmCli,'run','typecheck')
    Invoke-PinnedNode 'build' @($npmCli,'run','build')
    if ($ValidateSavedEvidence) {
        Invoke-PinnedNode 'saved-evidence-integration' @($npmCli,'run','w6:integration','--','--run')
        Invoke-PinnedNode 'tour' @($npmCli,'run','w6:tour')
        Invoke-PinnedNode 'short-urls' @('scripts/verify-short-urls.mjs')
        Invoke-PinnedNode 'orientation' @('scripts/verify-orientation.mjs')
        Invoke-PinnedNode 'publication-guard-tests' @('deployment/latest-link/test.mjs')
    }
    if ((File-Sha $packagePath) -ne $packageBefore -or (File-Sha $lockPath) -ne $lockBefore) { throw 'Source dependency specification changed during installation.' }
    $receipt = [pscustomobject]@{status='PASS'; node_version=$nodeVersion; npm_version=$npmVersion; node_archive_sha256=$nodeArchiveSha; node_executable=$nodeExe; source=$project; package_sha256=$packageBefore; package_lock_sha256=$lockBefore; codex_dependency=$false; npm_lifecycle_scripts_disabled=$true; saved_evidence_validated=[bool]$ValidateSavedEvidence; commands=$commands}
    $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $tools 'website-installation.json') -Encoding UTF8
} finally {
    foreach ($item in Get-ChildItem Env:) { Remove-Item -LiteralPath ("Env:" + $item.Name) }
    foreach ($name in $environmentBefore.Keys) { Set-Item -LiteralPath ("Env:" + $name) -Value $environmentBefore[$name] }
    Pop-Location
}
