<# Install only saved-data/CIF parser dependencies in a NEW external directory. #>
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Destination,[string]$ProjectRoot)
$ErrorActionPreference = 'Stop'
if (-not $ProjectRoot) { $ProjectRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) }
$project = [IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\')
$target = [IO.Path]::GetFullPath($Destination).TrimEnd('\')
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
if (-not [IO.Path]::IsPathRooted($Destination)) { throw 'Use an absolute parser destination.' }
Assert-NoReparse $project
Assert-NoReparse $target
if ($target.Equals($project,[StringComparison]::OrdinalIgnoreCase) -or $target.StartsWith($project+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Parser destination must be outside the source.' }
if (Test-Path -LiteralPath $target) { throw 'Parser destination must be new.' }
$bootstrap = Get-Content -LiteralPath (Join-Path $project 'requirements\phase4\bootstrap.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($bootstrap.python_version -ne '3.11.14' -or $bootstrap.uv.version -ne '0.13.7') { throw 'Review changed runtime pins before installation.' }
$lock = Join-Path $PSScriptRoot 'website-parsers-lock.txt'
$buildLock = Join-Path $project 'requirements\phase4\build-tools-lock.txt'
$utf8 = New-Object Text.UTF8Encoding($false)
function Invoke-Checked([string]$Label,[string]$Executable,[string[]]$NativeArguments) {
    & $Executable @NativeArguments | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Parser command failed: $Label ($LASTEXITCODE)." }
}
function Get-Verified([string]$Url,[string]$Path,[string]$Sha,[long]$Bytes) {
    Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $Path
    if ((Get-Item -LiteralPath $Path).Length -ne $Bytes -or (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Sha) { throw 'Parser bootstrap size/SHA256 mismatch.' }
}
$before = @{}
foreach ($item in Get-ChildItem Env:) { if ($item.Name -match '^(UV_|PIP_|PYTHON)' -or $item.Name -eq 'MPLCONFIGDIR') { $before[$item.Name] = $item.Value } }
try {
    foreach ($key in @($before.Keys)) { Remove-Item -LiteralPath ('Env:\'+$key) }
    New-Item -ItemType Directory -Path $target,(Join-Path $target 'tools'),(Join-Path $target 'runtime') -Force | Out-Null
    $env:UV_CACHE_DIR = Join-Path $target 'cache'
    $env:UV_PYTHON_INSTALL_DIR = Join-Path $target 'runtime'
    $env:UV_NO_CONFIG = '1'
    $env:UV_NO_PROGRESS = '1'
    $env:UV_KEYRING_PROVIDER = 'disabled'
    $env:UV_LINK_MODE = 'copy'
    $env:PYTHONNOUSERSITE = '1'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:MPLCONFIGDIR = Join-Path $target 'matplotlib'
    $uvWheel = Join-Path $target 'tools\uv.whl'
    Get-Verified $bootstrap.uv.url $uvWheel $bootstrap.uv.sha256 $bootstrap.uv.bytes
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead($uvWheel)
    try {
        $entry = $zip.GetEntry($bootstrap.uv.entry)
        if ($null -eq $entry) { throw 'Pinned uv wheel is missing its executable.' }
        $uv = Join-Path $target 'tools\uv.exe'
        [IO.Compression.ZipFileExtensions]::ExtractToFile($entry,$uv,$false)
    } finally { $zip.Dispose() }
    if ((Get-FileHash -LiteralPath $uv -Algorithm SHA256).Hash.ToLowerInvariant() -ne $bootstrap.uv.executable_sha256) { throw 'uv executable SHA256 mismatch.' }
    $pythonArchive = Join-Path $target 'tools\python.tar.gz'
    Get-Verified $bootstrap.python.url $pythonArchive $bootstrap.python.sha256 $bootstrap.python.bytes
    $tar = (Get-Command tar.exe -ErrorAction Stop).Source
    Invoke-Checked 'extract runtime' $tar @('-xzf',$pythonArchive,'-C',(Join-Path $target 'runtime'))
    $runtime = Join-Path $target 'runtime\python\python.exe'
    if ((Get-FileHash -LiteralPath $runtime -Algorithm SHA256).Hash.ToLowerInvariant() -ne $bootstrap.python.executable_sha256) { throw 'Python executable SHA256 mismatch.' }
    $environment = Join-Path $target 'envs\website-parsers'
    Invoke-Checked 'create environment' $uv @('--no-config','venv','--python',$runtime,$environment)
    $python = Join-Path $environment 'Scripts\python.exe'
    Invoke-Checked 'install hash-pinned parser subset' $uv @('--no-config','pip','install','--python',$python,'--default-index','https://pypi.org/simple','--index-strategy','first-index','--build-constraints',$buildLock,'--require-hashes','-r',$lock)
    Invoke-Checked 'dependency consistency' $uv @('--no-config','pip','check','--python',$python)
    $verify = "import importlib.util as u, importlib.metadata as m, json, sys; from pymatgen.core import Lattice, Structure; from pymatgen.io.cif import CifFile, CifParser; import numpy; assert sys.version_info[:3]==(3,11,14); assert numpy.__version__=='2.2.6'; assert m.version('pymatgen')=='2025.10.7'; assert all(u.find_spec(n) is None for n in ('torch','chgnet','jax','jaxlib')); print(json.dumps({'python':sys.version.split()[0],'numpy':numpy.__version__,'pymatgen':m.version('pymatgen'),'model_packages_installed':False}))"
    Invoke-Checked 'saved parser imports without model packages' $python @('-I','-B','-c',$verify)
    $receipt = [ordered]@{status='PASS'; runtime_python=$runtime; parser_python=$python; python_version='3.11.14'; uv_version='0.13.7'; lock_sha256=(Get-FileHash -LiteralPath $lock -Algorithm SHA256).Hash.ToLowerInvariant(); package_count=40; model_packages_installed=$false; model_experiments_run=$false}
    [IO.File]::WriteAllText((Join-Path $target 'website-parsers-installation.json'),($receipt | ConvertTo-Json -Depth 8)+[Environment]::NewLine,$utf8)
    Write-Output 'Saved-data/CIF parser environment installed without model packages.'
} finally {
    foreach ($item in @(Get-ChildItem Env:)) { if ($item.Name -match '^(UV_|PIP_|PYTHON)' -or $item.Name -eq 'MPLCONFIGDIR') { Remove-Item -LiteralPath ('Env:\'+$item.Name) } }
    foreach ($key in $before.Keys) { Set-Item -LiteralPath ('Env:\'+$key) -Value $before[$key] }
}
