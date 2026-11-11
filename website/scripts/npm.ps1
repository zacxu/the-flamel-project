# Uses the bundled local runtime without changing system PATH or analysis Python.
$ErrorActionPreference = 'Stop'
$websiteRoot = Split-Path -Parent $PSScriptRoot
$bundledNode = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
if ($env:FLAMEL_NODE) {
    $nodeExe = $env:FLAMEL_NODE
} elseif (Test-Path -LiteralPath $bundledNode) {
    $nodeExe = $bundledNode
} else {
    $nodeCommand = Get-Command node -ErrorAction SilentlyContinue
    if (-not $nodeCommand) { throw 'Node 24.15+ required. Install Node 24 or set FLAMEL_NODE to its executable.' }
    $nodeExe = $nodeCommand.Source
}
$npmCli = Join-Path $websiteRoot '.tooling\npm\bin\npm-cli.js'
$npmArguments = @($args)
# PowerShell may consume the caller's -- separator. Preserve script arguments
# as arguments to the package script rather than npm's own option parser.
if ($npmArguments.Count -gt 2 -and $npmArguments[0] -in @('run', 'run-script') -and $npmArguments[2] -ne '--') {
    $npmArguments = @($npmArguments[0], $npmArguments[1], '--') + $npmArguments[2..($npmArguments.Count - 1)]
}
$previousPath = $env:PATH
Push-Location $websiteRoot
try {
    $env:PATH = (Split-Path -Parent $nodeExe) + [IO.Path]::PathSeparator + $previousPath
    & $nodeExe (Join-Path $PSScriptRoot 'bootstrap-npm.mjs')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $nodeExe $npmCli @npmArguments
    exit $LASTEXITCODE
} finally {
    $env:PATH = $previousPath
    Pop-Location
}
