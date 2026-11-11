param(
    [Parameter(Mandatory=$true)][string]$Destination,
    [ValidateSet('all','analysis-historical','generator-historical','analysis-maintenance-cpu')]
    [string]$Environment = 'analysis-maintenance-cpu',
    [string]$CacheDirectory
)
$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
function Assert-NoReparseAncestor([string]$Path) {
    $cursor = [System.IO.Path]::GetFullPath($Path)
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            $item = Get-Item -LiteralPath $cursor -Force
            if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse destinations are not supported' }
        }
        $parent = Split-Path -Parent $cursor
        if ($parent -eq $cursor) { break }
        $cursor = $parent
    }
}
function Assert-External([string]$Path) {
    if (-not [System.IO.Path]::IsPathRooted($Path)) { throw 'Use an absolute destination/cache path' }
    $resolved = [System.IO.Path]::GetFullPath($Path)
    if ($resolved.TrimEnd('\').Equals($projectRoot.TrimEnd('\'),[StringComparison]::OrdinalIgnoreCase) -or
        $resolved.StartsWith($projectRoot.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Runtime and cache must be outside the source checkout' }
    Assert-NoReparseAncestor $resolved
    return $resolved
}
$targetRoot = Assert-External $Destination
if (Test-Path -LiteralPath $targetRoot) { throw 'Destination must be new; existing environments are never modified' }
if ($CacheDirectory) { $cacheRoot = Assert-External $CacheDirectory } else { $cacheRoot = Join-Path $targetRoot 'cache' }
if (-not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { throw 'This specification is tested for Windows x64' }
$bootstrap = Get-Content -LiteralPath (Join-Path $projectRoot 'requirements\phase4\bootstrap.json') -Raw | ConvertFrom-Json
$profiles = @($Environment)
if ($Environment -eq 'all') { $profiles = @('analysis-historical','generator-historical','analysis-maintenance-cpu') }
$utf8 = New-Object System.Text.UTF8Encoding($false)
function Write-Json([string]$Path,$Value) { [IO.File]::WriteAllText($Path,($Value | ConvertTo-Json -Depth 30)+[Environment]::NewLine,$utf8) }
function Invoke-Checked([string]$Label,[string]$Executable,[string[]]$NativeArguments) {
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $output = & $Executable @NativeArguments 2>&1
        $nativeExit = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previousPreference }
    $log = Join-Path $targetRoot ('logs\'+$Label+'.log')
    [IO.File]::WriteAllText($log,($output -join [Environment]::NewLine),$utf8)
    if ($nativeExit -ne 0) { throw "Failed $Label; inspect the private log: $log" }
}
function Get-Verified([string]$Url,[string]$Path,[string]$Expected,[long]$Bytes) {
    Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $Path
    if ((Get-Item -LiteralPath $Path).Length -ne $Bytes -or
        (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Expected) { throw 'Downloaded bootstrap failed size/SHA-256 verification' }
}
$preservedEnvironment = @{}
foreach ($item in Get-ChildItem Env:) {
    if ($item.Name -match '^(UV_|PIP_)' -or $item.Name -in @('MPLCONFIGDIR','PYTHONNOUSERSITE','PYTHONDONTWRITEBYTECODE')) {
        $preservedEnvironment[$item.Name] = $item.Value
    }
}
try {
    foreach ($key in @($preservedEnvironment.Keys)) { Remove-Item -LiteralPath ('Env:\'+$key) }
    New-Item -ItemType Directory -Path $targetRoot,(Join-Path $targetRoot 'tools'),(Join-Path $targetRoot 'logs'),(Join-Path $targetRoot 'runtime'),$cacheRoot -Force | Out-Null
    $env:UV_CACHE_DIR = $cacheRoot
    $env:UV_PYTHON_INSTALL_DIR = Join-Path $targetRoot 'runtime'
    $env:UV_PYTHON_BIN_DIR = Join-Path $targetRoot 'runtime-bin'
    $env:UV_LINK_MODE = 'copy'
    $env:UV_NO_CONFIG = '1'
    $env:UV_NO_PROGRESS = '1'
    $env:UV_KEYRING_PROVIDER = 'disabled'
    $env:MPLCONFIGDIR = Join-Path $cacheRoot 'matplotlib'
    $env:PYTHONNOUSERSITE = '1'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $uvWheel = Join-Path $targetRoot 'tools\uv.whl'
    Get-Verified $bootstrap.uv.url $uvWheel $bootstrap.uv.sha256 $bootstrap.uv.bytes
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [IO.Compression.ZipFile]::OpenRead($uvWheel)
    try {
        $entry = $archive.GetEntry($bootstrap.uv.entry)
        if ($null -eq $entry) { throw 'Verified uv wheel lacks expected executable' }
        $uv = Join-Path $targetRoot 'tools\uv.exe'
        [IO.Compression.ZipFileExtensions]::ExtractToFile($entry,$uv,$false)
    } finally { $archive.Dispose() }
    if ((Get-FileHash -LiteralPath $uv -Algorithm SHA256).Hash.ToLowerInvariant() -ne $bootstrap.uv.executable_sha256) { throw 'uv executable digest mismatch' }
    $pythonArchive = Join-Path $targetRoot 'tools\python.tar.gz'
    Get-Verified $bootstrap.python.url $pythonArchive $bootstrap.python.sha256 $bootstrap.python.bytes
    $tar = (Get-Command tar.exe -ErrorAction Stop).Source
    Invoke-Checked -Label 'extract-python' -Executable $tar -NativeArguments @('-xzf',$pythonArchive,'-C',(Join-Path $targetRoot 'runtime'))
    $runtimePython = Join-Path $targetRoot 'runtime\python\python.exe'
    if ((Get-FileHash -LiteralPath $runtimePython -Algorithm SHA256).Hash.ToLowerInvariant() -ne $bootstrap.python.executable_sha256) { throw 'Python executable digest mismatch' }
    $buildConstraints = Join-Path $projectRoot 'requirements\phase4\build-tools-lock.txt'
    $results = @()
    foreach ($profile in $profiles) {
        $environmentRoot = Join-Path $targetRoot ('envs\'+$profile)
        Invoke-Checked -Label ($profile+'-venv') -Executable $uv -NativeArguments @('--no-config','venv','--python',$runtimePython,$environmentRoot)
        $environmentPython = Join-Path $environmentRoot 'Scripts\python.exe'
        $lock = Join-Path $projectRoot ('requirements\phase4\'+$profile+'-lock.txt')
        Invoke-Checked -Label ($profile+'-install') -Executable $uv -NativeArguments @('--no-config','pip','install','--python',$environmentPython,'--default-index','https://pypi.org/simple','--index-strategy','first-index','--build-constraints',$buildConstraints,'--require-hashes','-r',$lock)
        if ($profile -eq 'generator-historical') {
            # Copy only the 86 hash-checked public upstream originals; never copy private .env/build outputs.
            $vendorRoot = Join-Path $targetRoot 'vendor-source\CrystalFormer'
            $manifest = Get-Content -LiteralPath (Join-Path $projectRoot 'publication\git-input-files.json') -Raw | ConvertFrom-Json
            $vendorRecords = @($manifest | Where-Object { $_.path.StartsWith('vendor/CrystalFormer/') })
            if ($vendorRecords.Count -ne 86) { throw 'Expected 86 reviewed CrystalFormer source records' }
            foreach ($record in $vendorRecords) {
                $relative = [string]$record.path
                if ($relative.Contains('..') -or $relative.Contains('\') -or $relative.Contains(':')) { throw 'Unsafe vendor manifest path' }
                $source = Join-Path $projectRoot ($relative.Replace('/','\'))
                Assert-NoReparseAncestor $source
                if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $record.sha256) { throw 'Vendored source differs from pinned manifest' }
                $suffix = $relative.Substring('vendor/CrystalFormer/'.Length)
                $copy = Join-Path $vendorRoot ($suffix.Replace('/','\'))
                New-Item -ItemType Directory -Force -Path (Split-Path -Parent $copy) | Out-Null
                Copy-Item -LiteralPath $source -Destination $copy
            }
            Invoke-Checked -Label ($profile+'-vendor') -Executable $uv -NativeArguments @('--no-config','pip','install','--python',$environmentPython,'--default-index','https://pypi.org/simple','--index-strategy','first-index','--build-constraints',$buildConstraints,'--no-deps',$vendorRoot)
        }
        Invoke-Checked -Label ($profile+'-check') -Executable $uv -NativeArguments @('--no-config','pip','check','--python',$environmentPython)
        $report = Join-Path $targetRoot ($profile+'-verification.json')
        $verifyArguments = @('-I','-B',(Join-Path $PSScriptRoot 'verify_python_environment.py'),'--spec',(Join-Path $projectRoot ('requirements\phase4\'+$profile+'.txt')),'--environment',$profile,'--report',$report)
        if ($profile -eq 'analysis-maintenance-cpu') { $verifyArguments += '--load-trusted-chgnet' }
        Invoke-Checked -Label ($profile+'-verify') -Executable $environmentPython -NativeArguments $verifyArguments
        $results += [pscustomobject]@{ profile=$profile; python=$environmentPython; verification=$report; status='PASS' }
        Write-Output "Installed and verified $profile"
    }
    $receipt = [ordered]@{ schema_version=1; status='PASS'; source_root=$projectRoot; destination=$targetRoot; bootstrap='requirements/phase4/bootstrap.json'; profiles=$results; no_original_environment_modified=$true; no_scientific_experiment_run=$true; historical_advisories_retained='Historical profiles reproduce old pins; maintenance CPU is a separate compatibility-tested environment.' }
    Write-Json (Join-Path $targetRoot 'INSTALLATION.json') $receipt
} finally {
    foreach ($item in @(Get-ChildItem Env:)) {
        if ($item.Name -match '^(UV_|PIP_)' -or $item.Name -in @('MPLCONFIGDIR','PYTHONNOUSERSITE','PYTHONDONTWRITEBYTECODE')) { Remove-Item -LiteralPath ('Env:\'+$item.Name) }
    }
    foreach ($key in $preservedEnvironment.Keys) { Set-Item -LiteralPath ('Env:\'+$key) -Value $preservedEnvironment[$key] }
}
