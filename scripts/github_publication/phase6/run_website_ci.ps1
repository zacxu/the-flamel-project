<# Run the installer and saved-source regressions in a NEW external copy. No hosting access. #>
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$AuditRoot,[string]$ProjectRoot)
$ErrorActionPreference = 'Stop'
if (-not $ProjectRoot) { $ProjectRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) }
$project = [IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\')
$audit = [IO.Path]::GetFullPath($AuditRoot).TrimEnd('\')
function Assert-NoReparse([string]$Path) {
    $cursor = [IO.Path]::GetFullPath($Path)
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            if (((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse paths are not supported.' }
        }
        $parent = Split-Path -Parent $cursor
        if ($parent -eq $cursor) { break }
        $cursor = $parent
    }
}
if (-not [IO.Path]::IsPathRooted($AuditRoot)) { throw 'Use an absolute audit path.' }
Assert-NoReparse $project
Assert-NoReparse $audit
if ($audit.Equals($project,[StringComparison]::OrdinalIgnoreCase) -or $audit.StartsWith($project+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'AuditRoot must be outside the checkout.' }
if (Test-Path -LiteralPath $audit) { throw 'AuditRoot must be new; prior evidence is never overwritten.' }
$git = (Get-Command git -ErrorAction Stop).Source
function Invoke-Git([string[]]$GitArguments) {
    $result = & $git -C $project @GitArguments
    if ($LASTEXITCODE -ne 0) { throw 'Git operation failed.' }
    return $result
}
if (@(Invoke-Git @('status','--porcelain=v1','--untracked-files=all')).Count -ne 0) { throw 'Website CI requires a clean source checkout.' }
$sourceCommit = (Invoke-Git @('rev-parse','HEAD')).Trim()
$modes = @(Invoke-Git @('ls-tree','-r','--format=%(objectmode)','HEAD') | Sort-Object -Unique)
foreach ($mode in $modes) { if ($mode -notin @('100644','100755')) { throw 'Only regular source files may enter the CI export.' } }
New-Item -ItemType Directory -Path $audit,(Join-Path $audit 'source') -Force | Out-Null
$archive = Join-Path $audit 'source.tar'
$null = Invoke-Git @('archive','--format=tar',('--output='+$archive),'HEAD')
$tar = (Get-Command tar.exe -ErrorAction Stop).Source
& $tar '-xf' $archive '-C' (Join-Path $audit 'source')
if ($LASTEXITCODE -ne 0) { throw 'Source export extraction failed.' }
# Only this newly-created, non-recursive temporary export file is removed.
Remove-Item -LiteralPath $archive
$copy = Join-Path $audit 'source'
$parsers = Join-Path $audit 'python-parsers'
& (Join-Path $PSScriptRoot 'install_website_parsers.ps1') -ProjectRoot $copy -Destination $parsers
$python = Join-Path $parsers 'envs\website-parsers\Scripts\python.exe'
$tools = Join-Path $audit 'website-tools'
# The frozen installer sets FLAMEL_NODE/FLAMEL_PYTHON and checks every child exit.
# Validator report replacements occur only in this disposable source export.
& (Join-Path $copy 'scripts\github_publication\install_website.ps1') -ProjectRoot $copy -ToolchainRoot $tools -PythonExe $python -ValidateSavedEvidence
if ($LASTEXITCODE -ne 0) { throw 'Website installation/regression failed.' }
$node = Join-Path $tools 'node-v24.22.1-win-x64\node.exe'
$oldNode = $env:FLAMEL_NODE
$oldPython = $env:FLAMEL_PYTHON
$oldDontWrite = $env:PYTHONDONTWRITEBYTECODE
try {
    $env:FLAMEL_NODE = $node
    $env:FLAMEL_PYTHON = $python
    $env:PYTHONDONTWRITEBYTECODE = '1'
    Push-Location (Join-Path $copy 'website')
    try {
        # Retained actual browser files vs freshly validated projection logic.
        # This does not open a new browser session.
        & $node '.tooling/npm/bin/npm-cli.js' 'run' 'w6:downloads'
        if ($LASTEXITCODE -ne 0) { throw 'Retained download projection validation failed.' }
    } finally { Pop-Location }
} finally {
    if ($null -eq $oldNode) { Remove-Item Env:FLAMEL_NODE -ErrorAction SilentlyContinue } else { $env:FLAMEL_NODE = $oldNode }
    if ($null -eq $oldPython) { Remove-Item Env:FLAMEL_PYTHON -ErrorAction SilentlyContinue } else { $env:FLAMEL_PYTHON = $oldPython }
    if ($null -eq $oldDontWrite) { Remove-Item Env:PYTHONDONTWRITEBYTECODE -ErrorAction SilentlyContinue } else { $env:PYTHONDONTWRITEBYTECODE = $oldDontWrite }
}
if ((Invoke-Git @('rev-parse','HEAD')).Trim() -ne $sourceCommit -or @(Invoke-Git @('status','--porcelain=v1','--untracked-files=all')).Count -ne 0) { throw 'Original source checkout changed during website CI.' }
$installation = Get-Content -LiteralPath (Join-Path $tools 'website-installation.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($installation.status -ne 'PASS' -or -not $installation.saved_evidence_validated) { throw 'Installer receipt does not establish completed saved-source regressions.' }
$integration = Get-Content -LiteralPath (Join-Path $copy 'website\reports\W6_INTEGRATION_VALIDATION.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$tour = Get-Content -LiteralPath (Join-Path $copy 'website\reports\W6_TOUR_VALIDATION.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$downloads = Get-Content -LiteralPath (Join-Path $copy 'website\reports\W6_DOWNLOAD_VALIDATION.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($record in @($integration,$tour,$downloads)) { if ($record.status -ne 'passed') { throw 'A required website validation receipt did not pass.' } }
$receipt = [ordered]@{
    schema_version=1; status='PASS'; source_commit=$sourceCommit; disposable_source=$copy;
    original_checkout_unchanged=$true; toolchain_root=$tools; runtime_python=(Join-Path $parsers 'runtime\python\python.exe'); parser_python=$python;
    node='24.22.1'; npm='12.2.1'; python='3.11.14'; integration_checks=$integration.checksPassed;
    source_regression_checks=$integration.sourceRegressionChecks; tour_checks=$tour.checkCount; retained_download_checks=$downloads.checksPassed;
    regression_reports_replaced_only_in_disposable_copy=$true; research_archives_downloaded=$false; model_packages_installed=$false; scientific_experiments=0; hosting_accessed=$false;
    limits='Source/lifecycle/CIF and retained browser-file checks; no fresh browser session or production acceptance is asserted.'
}
$utf8 = New-Object Text.UTF8Encoding($false)
[IO.File]::WriteAllText((Join-Path $audit 'website-ci.json'),($receipt | ConvertTo-Json -Depth 8)+[Environment]::NewLine,$utf8)
Write-Output 'Website CI completed; original checkout and accepted evidence are unchanged.'
