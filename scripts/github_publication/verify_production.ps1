param([string]$Root=(Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$rootPath=[System.IO.Path]::GetFullPath($Root)
$reportPath=Join-Path $rootPath 'PRODUCTION_BASELINE.json'
$expectedReportHash=([System.IO.File]::ReadAllText((Join-Path $rootPath 'PRODUCTION_BASELINE.sha256'))).Split(' ')[0].Trim()
$actualReportHash=(Get-FileHash -LiteralPath $reportPath -Algorithm SHA256).Hash.ToLowerInvariant()
if($actualReportHash -cne $expectedReportHash) { throw 'Baseline manifest checksum mismatch.' }
$report=[System.IO.File]::ReadAllText($reportPath) | ConvertFrom-Json
$htdocs=Join-Path $rootPath 'htdocs'
$prefix=$htdocs.TrimEnd('\','/')+[System.IO.Path]::DirectorySeparatorChar
$count=0
$bytes=0L
foreach($file in $report.files) {
  $path=[System.IO.Path]::GetFullPath((Join-Path $htdocs ([string]$file.path)))
  if(-not $path.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'Recovery manifest path escapes htdocs.' }
  $item=Get-Item -LiteralPath $path
  $hash=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
  if($item.Length -ne $file.expectedBytes -or $hash -cne $file.expectedSha256) { throw ('Recovery file mismatch: '+$file.path) }
  $count++
  $bytes+=$item.Length
}
$physicalCount=[System.IO.Directory]::GetFiles($htdocs,'*',[System.IO.SearchOption]::AllDirectories).Count
if($count -ne 123 -or $physicalCount -ne $count -or $bytes -ne $report.recoveryBytes) { throw 'Recovery file count or byte total mismatch.' }
$research=[System.IO.File]::ReadAllText((Join-Path $htdocs 'research\manifest.json')) | ConvertFrom-Json
foreach($file in $research.files) {
  $path=Join-Path (Join-Path $htdocs 'research') ([string]$file.path)
  $item=Get-Item -LiteralPath $path
  $hash=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
  if($item.Length -ne $file.bytes -or $hash -cne $file.sha256) { throw ('Research payload mismatch: '+$file.path) }
}
[PSCustomObject]@{status='passed';root=$rootPath;manifestSha256=$actualReportHash;filesVerified=$count;bytesVerified=$bytes;researchPayloadsVerified=$research.files.Count;sourceCheckoutRequired=$false;githubRequired=$false;networkRequired=$false} | ConvertTo-Json -Compress
