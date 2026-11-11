param([ValidateSet('all','analysis','generator')][string]$Environment = 'all')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$env:UV_CACHE_DIR = Join-Path $projectRoot '.cache\uv'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $projectRoot '.runtime\python'
$env:UV_PYTHON_BIN_DIR = Join-Path $projectRoot '.runtime\bin'
$env:PIP_CACHE_DIR = Join-Path $projectRoot '.cache\pip'
$env:MPLCONFIGDIR = Join-Path $projectRoot '.cache\matplotlib'
$env:PYTHONNOUSERSITE = '1'
$uvExecutable = Join-Path $projectRoot '.runtime\uv\bin\uv.exe'
if (-not (Test-Path -LiteralPath $uvExecutable)) {
    python -m pip install --target '.runtime\uv' 'uv==0.9.7' --no-warn-script-location --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) { throw 'Workspace uv bootstrap failed' }
}
& $uvExecutable python install 3.11.14 --no-bin --no-registry
if ($LASTEXITCODE -ne 0) { throw 'Python bootstrap failed' }
$runtimePython = Join-Path $projectRoot '.runtime\python\cpython-3.11.14-windows-x86_64-none\python.exe'
foreach ($environmentName in @('analysis','generator')) {
    if ($Environment -ne 'all' -and $Environment -ne $environmentName) { continue }
    $environmentPath = Join-Path $projectRoot ".envs\$environmentName"
    $environmentPython = Join-Path $environmentPath 'Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $environmentPython)) {
        & $uvExecutable venv --python $runtimePython $environmentPath
        if ($LASTEXITCODE -ne 0) { throw "Failed to create $environmentName environment" }
    }
    $lockFile = Join-Path $projectRoot "requirements\$environmentName-lock.txt"
    if (-not (Test-Path -LiteralPath $lockFile)) { throw "Missing tested package lock: $lockFile" }
    if ($environmentName -eq 'analysis') {
        & $uvExecutable pip install --python $environmentPython --extra-index-url 'https://download.pytorch.org/whl/cu124' --index-strategy unsafe-best-match -r $lockFile
    } else {
        & $uvExecutable pip install --python $environmentPython -r $lockFile
    }
    if ($LASTEXITCODE -ne 0) { throw "Failed to install $environmentName lock" }
    & $uvExecutable pip check --python $environmentPython
    if ($LASTEXITCODE -ne 0) { throw "$environmentName dependency check failed" }
}
Write-Output 'Workspace environments are installed. This command does not rerun scientific pilots.'
