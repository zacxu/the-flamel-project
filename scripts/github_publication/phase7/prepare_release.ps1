<# Build once and fully validate an immutable selected source in a disposable checkout.
No hosting upload, GitHub publication, scientific experiments or original evidence edits.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$CandidateRoot,
    [Parameter(Mandatory=$true)][string]$ToolchainRoot,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [Parameter(Mandatory=$true)][string]$SourceCommit,
    [Parameter(Mandatory=$true)][string]$PredecessorArchive
)
$ErrorActionPreference = 'Stop'
if ($SourceCommit -cnotmatch '^[a-f0-9]{40}$') { throw 'Use a complete immutable source commit.' }
$root = [IO.Path]::GetFullPath($CandidateRoot).TrimEnd('\')
$tools = [IO.Path]::GetFullPath($ToolchainRoot).TrimEnd('\')
$output = [IO.Path]::GetFullPath($OutputDirectory).TrimEnd('\')
function Assert-NoReparse([string]$Path) {
    $cursor = [IO.Path]::GetFullPath($Path)
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            if (((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Release paths cannot contain reparse points.' }
        }
        $parent = Split-Path -Parent $cursor
        if ($parent -eq $cursor) { break }
        $cursor = $parent
    }
}
foreach ($location in @($root,$tools,$output,$PredecessorArchive)) { Assert-NoReparse $location }
foreach ($location in @($tools,$output)) {
    if ($location.Equals($root,[StringComparison]::OrdinalIgnoreCase) -or $location.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Tools and release output must be outside candidate source.' }
    if (Test-Path -LiteralPath $location) { throw 'Toolchain and release output destinations must be new.' }
}
$git = (Get-Command git -CommandType Application | Select-Object -First 1).Source
function Invoke-Git([string[]]$Arguments) {
    $result = & $git -C $root @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'Release Git verification failed.' }
    return $result
}
if (@(Invoke-Git @('status','--porcelain=v1','--untracked-files=all')).Count -ne 0) { throw 'Disposable candidate must start clean.' }
if ((Invoke-Git @('rev-parse','HEAD')).Trim() -cne $SourceCommit) { throw 'Selected candidate commit differs.' }
foreach ($mode in @(Invoke-Git @('ls-tree','-r','--format=%(objectmode)','HEAD') | Sort-Object -Unique)) {
    if ($mode -notin @('100644','100755')) { throw 'Release source may contain only regular tracked files.' }
}
$before = @{}
$tracked = @(Invoke-Git @('ls-files'))
foreach ($relative in $tracked) { $before[$relative] = (Get-FileHash -LiteralPath (Join-Path $root $relative) -Algorithm SHA256).Hash }
$phase6 = Join-Path (Split-Path -Parent $PSScriptRoot) 'phase6'
$parsers = Join-Path $tools 'python-parsers'
& (Join-Path $phase6 'install_website_parsers.ps1') -ProjectRoot $root -Destination $parsers
$python = Join-Path $parsers 'envs\website-parsers\Scripts\python.exe'
& $python -I -B (Join-Path $PSScriptRoot 'website_predecessor.py') restore --root $root --archive $PredecessorArchive --report (Join-Path $tools 'predecessor-restoration.json')
if ($LASTEXITCODE -ne 0) { throw 'Pinned predecessor reconstruction failed.' }
$websiteTools = Join-Path $tools 'website'
# This performs exactly one build. Subsequent validators never rebuild dist.
& (Join-Path $root 'scripts/github_publication/install_website.ps1') -ProjectRoot $root -ToolchainRoot $websiteTools -PythonExe $python -ValidateSavedEvidence
if ($LASTEXITCODE -ne 0) { throw 'Fresh installation/full source validation failed.' }
$node = Join-Path $websiteTools 'node-v24.22.1-win-x64\node.exe'
$envBefore = @{}
foreach ($name in @('FLAMEL_NODE','FLAMEL_PYTHON','PYTHONDONTWRITEBYTECODE')) { $envBefore[$name] = [Environment]::GetEnvironmentVariable($name,'Process') }
try {
    $env:FLAMEL_NODE = $node
    $env:FLAMEL_PYTHON = $python
    $env:PYTHONDONTWRITEBYTECODE = '1'
    Push-Location -LiteralPath (Join-Path $root 'website')
    try {
        foreach ($arguments in @(
            @('.tooling/npm/bin/npm-cli.js','run','w6:downloads'),
            @('scripts/package-release.mjs'),
            @('scripts/verify-release.mjs')
        )) {
            & $node @arguments
            if ($LASTEXITCODE -ne 0) { throw ('Full release validation failed: '+($arguments -join ' ')) }
        }
        $stage = Join-Path $tools 'publication-stage'
        & $node (Join-Path $phase6 'manual_stage.mjs') "--website-root=$(Join-Path $root 'website')" "--stage-root=$stage" --package=reports/W6_RELEASE_PACKAGE.json --stage
        if ($LASTEXITCODE -ne 0) { throw 'Exact package publication guard failed.' }
    } finally { Pop-Location }
    & $python -I -B (Join-Path $phase6 'manual_ci.py') record-package --root $root --output $output --source-commit $SourceCommit --stage-root $stage
    if ($LASTEXITCODE -ne 0) { throw 'Independent exact ZIP/stage verifier failed.' }
} finally {
    foreach ($name in $envBefore.Keys) {
        if ($null -eq $envBefore[$name]) { Remove-Item -LiteralPath ('Env:\'+$name) -ErrorAction SilentlyContinue }
        else { Set-Item -LiteralPath ('Env:\'+$name) -Value $envBefore[$name] }
    }
}
$mutated = @()
foreach ($relative in $tracked) {
    if ((Get-FileHash -LiteralPath (Join-Path $root $relative) -Algorithm SHA256).Hash -cne $before[$relative]) {
        if ($relative -cne 'website/src/generated/uiRelease.ts' -and $relative -cnotlike 'website/reports/*') { throw ('Unexpected tracked input mutation: '+$relative) }
        $mutated += $relative
    }
}
if ((Invoke-Git @('rev-parse','HEAD')).Trim() -cne $SourceCommit) { throw 'Candidate commit changed.' }
$validation = Get-Content -LiteralPath (Join-Path $root 'website/reports/W6_RELEASE_VALIDATION.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($validation.status -ne 'passed' -or $validation.failed -ne 0) { throw 'Legacy release validation did not pass completely.' }
$record = Get-Content -LiteralPath (Join-Path $output 'package-record.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$installation = Get-Content -LiteralPath (Join-Path $websiteTools 'website-installation.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$builds = @($installation.commands | Where-Object { $_.label -eq 'build' })
if ($builds.Count -ne 1 -or $builds[0].exit_code -ne 0) { throw 'Release must have exactly one successful build.' }
$utf8 = New-Object Text.UTF8Encoding($false)
$receipt = [ordered]@{
    schema_version=1;status='VERIFIED_RELEASE_PACKAGE_NOT_DEPLOYED';source_commit=$SourceCommit;
    source_tree=(Invoke-Git @('rev-parse','HEAD^{tree}')).Trim();ui_build_id=$record.uiBuildId;
    payload_files=$record.fileCount;payload_bytes=$record.totalBytes;archive_sha256=$record.archive.sha256;archive_bytes=$record.archive.bytes;
    successful_builds=1;legacy_release_checks=$validation.checkCount;legacy_release_failed=$validation.failed;
    predecessor_files=$validation.cacheCoherence.predecessorFiles;loopback_http_responses=$validation.cacheCoherence.actualLoopbackHttpResponses;
    candidate_mutated_paths=$mutated;mutations_confined_to_disposable_reports_and_generated_identity=$true;
    scientific_experiments=0;hosting_changed=$false;browser_interactions_changed=$false;
    browser_scope='Existing frontend interactions preserved; no new live browser or production acceptance claimed.';
}
[IO.File]::WriteAllText((Join-Path $tools 'release-preparation.json'),($receipt | ConvertTo-Json -Depth 8)+[Environment]::NewLine,$utf8)
Write-Output ('Full release validation passed: '+$validation.checkCount+' checks; exact package preserved without rebuilding.')
