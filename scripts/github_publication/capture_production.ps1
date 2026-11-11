param(
  [string]$ProjectRoot = 'D:\bears',
  [string]$OutputRoot = (Split-Path -Parent $PSScriptRoot),
  [switch]$ResumeVerifiedCapture
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Add-Type -AssemblyName System.Net.Http
$utf8 = [System.Text.UTF8Encoding]::new($false)
$website = Join-Path ([System.IO.Path]::GetFullPath($ProjectRoot)) 'website'
$output = [System.IO.Path]::GetFullPath($OutputRoot)
$htdocs = Join-Path $output 'htdocs'
$resumeRows = @{}
if (Test-Path -LiteralPath $htdocs) {
  if (-not $ResumeVerifiedCapture) { throw 'Output htdocs already exists. Select a new capture directory or explicitly resume a recorded incomplete capture.' }
  if (Test-Path -LiteralPath (Join-Path $output 'PRODUCTION_BASELINE.json')) { throw 'A completed capture is never replaced.' }
  $failurePath = Join-Path $output 'CAPTURE_FAILURE.json'
  if (-not (Test-Path -LiteralPath $failurePath)) { throw 'Resume requires a recorded incomplete capture.' }
  $previousFailure = [System.IO.File]::ReadAllText($failurePath) | ConvertFrom-Json
  foreach($recordedFile in $previousFailure.completedFiles) {
    if($resumeRows.ContainsKey([string]$recordedFile.path)) { throw 'Duplicate retained capture path.' }
    $resumeRows[[string]$recordedFile.path] = $recordedFile
  }
} elseif($ResumeVerifiedCapture) { throw 'Resume requires an existing incomplete capture.' }
$packagePath = Join-Path $website 'reports\CRYSTAL_LAB_RELEASE_PACKAGE.json'
$hostRecordPath = Join-Path $website 'reports\W7_HOST_FILES.json'
$package = [System.IO.File]::ReadAllText($packagePath) | ConvertFrom-Json
$hostRecord = [System.IO.File]::ReadAllText($hostRecordPath) | ConvertFrom-Json
$origin = 'https://theflamelproject.42web.io'
$started = [DateTimeOffset]::UtcNow.ToString('o')
$rows = [System.Collections.Generic.List[object]]::new()
$checks = [System.Collections.Generic.List[object]]::new()
$aliases = [System.Collections.Generic.List[object]]::new()
$policyHash = 'cfec2cddb8cbbf215fbe2ee17593a20f8b470d80071648ddb6d79004a8bbd149'
function Digest([byte[]]$Bytes) {
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try { return [Convert]::ToHexString($sha.ComputeHash($Bytes)).ToLowerInvariant() } finally { $sha.Dispose() }
}
function Resolve-Within([string]$Root,[string]$Relative) {
  if ([System.IO.Path]::IsPathRooted($Relative) -or $Relative.Contains('\') -or ($Relative.Split('/') -contains '..')) { throw ('Unsafe relative path: '+$Relative) }
  $full = [System.IO.Path]::GetFullPath((Join-Path $Root $Relative))
  $prefix = $Root.TrimEnd('\','/') + [System.IO.Path]::DirectorySeparatorChar
  if (-not $full.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)) { throw ('Path escapes target: '+$Relative) }
  return $full
}
function Record-Check([string]$Name,[bool]$Passed) {
  $checks.Add([PSCustomObject]@{name=$Name;passed=$Passed})
  if (-not $Passed) { throw ('Verification failed: '+$Name) }
}
function Write-New([string]$Path,[byte[]]$Bytes) {
  if (Test-Path -LiteralPath $Path) {
    if (-not $ResumeVerifiedCapture) { throw ('Existing capture file is never replaced: '+$Path) }
    if ((Digest ([System.IO.File]::ReadAllBytes($Path))) -cne (Digest $Bytes)) { throw ('Existing capture file differs: '+$Path) }
    return
  }
  [System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($Path)) | Out-Null
  $stream = [System.IO.File]::Open($Path,[System.IO.FileMode]::CreateNew,[System.IO.FileAccess]::Write,[System.IO.FileShare]::None)
  try { $stream.Write($Bytes,0,$Bytes.Length) } finally { $stream.Dispose() }
  if ((Digest ([System.IO.File]::ReadAllBytes($Path))) -cne (Digest $Bytes)) { throw ('Read-back digest mismatch: '+$Path) }
}
# Validate every retained active release file before requesting production.
$expectedMap = @{}
foreach($file in $package.files) {
  $relative = [string]$file.path
  if ($expectedMap.ContainsKey($relative)) { throw ('Duplicate package path: '+$relative) }
  $localPath = Resolve-Within (Join-Path $website 'dist') $relative
  $localBytes = [System.IO.File]::ReadAllBytes($localPath)
  Record-Check ('Local package '+$relative) (($localBytes.Length -eq $file.bytes) -and ((Digest $localBytes) -ceq $file.sha256))
  $expectedMap[$relative] = $file
}
Record-Check 'Package file count' ($package.files.Count -eq $package.fileCount)
$localSum = ($package.files | Measure-Object -Property bytes -Sum).Sum
Record-Check 'Package byte total' ($localSum -eq $package.totalBytes)
[System.IO.Directory]::CreateDirectory($htdocs) | Out-Null
$cookieJar = [System.Net.CookieContainer]::new()
$handler = [System.Net.Http.HttpClientHandler]::new()
$handler.CookieContainer = $cookieJar
$handler.AllowAutoRedirect = $true
$client = [System.Net.Http.HttpClient]::new($handler)
$client.Timeout = [TimeSpan]::FromSeconds(30)
$client.DefaultRequestHeaders.UserAgent.ParseAdd('Flamel-Production-Backup/1.0')
$client.DefaultRequestHeaders.CacheControl = [System.Net.Http.Headers.CacheControlHeaderValue]::new()
$client.DefaultRequestHeaders.CacheControl.NoCache = $true
$challengeHandled = $false
function Read-Public([string]$Relative) {
  $uri = if ($Relative -eq '') { $origin+'/' } else { $origin+'/'+(($Relative.Split('/') | ForEach-Object { [Uri]::EscapeDataString($_) }) -join '/') }
  for($attempt=0;$attempt -lt 3;$attempt++) {
    $response = $client.GetAsync($uri).GetAwaiter().GetResult()
    $bytes = $response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
    $body = if($bytes.Length -lt 4096) { $utf8.GetString($bytes) } else { '' }
    if ($body.Contains('slowAES.decrypt')) {
      $numbers = [regex]::Matches($body,'toNumbers\("([a-fA-F0-9]+)"\)')
      if($numbers.Count -ne 3) { throw 'Unrecognized standard public-site cookie challenge.' }
      $aes = [System.Security.Cryptography.Aes]::Create()
      $aes.Mode = [System.Security.Cryptography.CipherMode]::CBC
      $aes.Padding = [System.Security.Cryptography.PaddingMode]::None
      $aes.Key = [Convert]::FromHexString($numbers[0].Groups[1].Value)
      $aes.IV = [Convert]::FromHexString($numbers[1].Groups[1].Value)
      $ciphertext = [Convert]::FromHexString($numbers[2].Groups[1].Value)
      $decryptor = $aes.CreateDecryptor()
      try { $cookieValue = [Convert]::ToHexString($decryptor.TransformFinalBlock($ciphertext,0,$ciphertext.Length)).ToLowerInvariant() }
      finally { $decryptor.Dispose(); $aes.Dispose() }
      $cookieJar.Add([System.Net.Cookie]::new('__test',$cookieValue,'/','theflamelproject.42web.io'))
      $cookieValue = $null
      $script:challengeHandled = $true
      $response.Dispose()
      continue
    }
    if([int]$response.StatusCode -ne 200) { $status=[int]$response.StatusCode; $response.Dispose(); throw ('HTTP '+$status+' for '+$Relative) }
    $result = [PSCustomObject]@{
      bytes=$bytes
      metadata=[PSCustomObject]@{
        url=$uri;finalUrl=$response.RequestMessage.RequestUri.AbsoluteUri;status=[int]$response.StatusCode
        bytes=$bytes.Length;sha256=(Digest $bytes);contentType=[string]$response.Content.Headers.ContentType
        cacheControl=[string]$response.Headers.CacheControl;etag=[string]$response.Headers.ETag
        contentEncoding=($response.Content.Headers.ContentEncoding -join ',');retrievedAt=[DateTimeOffset]::UtcNow.ToString('o')
      }
    }
    $response.Dispose()
    return $result
  }
  throw ('Cookie challenge did not settle for '+$Relative)
}
function Read-CapturedOrPublic([string]$Relative) {
  if ($resumeRows.ContainsKey($Relative)) {
    $recorded = $resumeRows[$Relative]
    if ($null -eq $recorded.http -or $recorded.http.status -ne 200) { throw ('Retained download has no successful HTTP provenance: '+$Relative) }
    $bytes = [System.IO.File]::ReadAllBytes((Resolve-Within $htdocs $Relative))
    if (($bytes.Length -ne $recorded.http.bytes) -or ((Digest $bytes) -cne $recorded.http.sha256)) { throw ('Retained HTTP capture bytes differ: '+$Relative) }
    return [PSCustomObject]@{bytes=$bytes;metadata=$recorded.http}
  }
  return (Read-Public $Relative)
}
try {
  $n=0
  foreach($file in $package.files) {
    $relative=[string]$file.path
    $got=Read-CapturedOrPublic $relative
    Record-Check ('Live active release '+$relative) (($got.metadata.bytes -eq $file.bytes) -and ($got.metadata.sha256 -ceq $file.sha256))
    Write-New (Resolve-Within $htdocs $relative) $got.bytes
    $rows.Add([PSCustomObject]@{path=$relative;provenance='downloaded-effective-http-response';expectedSha256=$file.sha256;expectedBytes=$file.bytes;sourceRecord='website/reports/CRYSTAL_LAB_RELEASE_PACKAGE.json';http=$got.metadata})
    $n++
    if($n % 10 -eq 0) { Write-Output ('PROGRESS active '+$n+'/'+$package.files.Count) }
  }
  $sidecars=@($hostRecord.files | Where-Object { $_.path.EndsWith('.bin') })
  Record-Check 'Expected 33 image backing sidecars' ($sidecars.Count -eq 33)
  foreach($file in $sidecars) {
    $relative=[string]$file.path
    $original=$relative.Substring(0,$relative.Length-4)
    Record-Check ('Image mapping closure '+$relative) ($expectedMap.ContainsKey($original) -and ($expectedMap[$original].sha256 -ceq $file.sha256))
    $localPath=Resolve-Within $website ([string]$file.localPath)
    $localBytes=[System.IO.File]::ReadAllBytes($localPath)
    Record-Check ('Retained backing image '+$relative) (($localBytes.Length -eq $file.bytes) -and ((Digest $localBytes) -ceq $file.sha256))
    $got=Read-CapturedOrPublic $relative
    Record-Check ('Live backing image '+$relative) (($got.metadata.bytes -eq $file.bytes) -and ($got.metadata.sha256 -ceq $file.sha256))
    Write-New (Resolve-Within $htdocs $relative) $got.bytes
    $rows.Add([PSCustomObject]@{path=$relative;provenance='downloaded-image-backing-http-response';expectedSha256=$file.sha256;expectedBytes=$file.bytes;sourceRecord='website/reports/W7_HOST_FILES.json';http=$got.metadata})
    $n++
    if($n % 10 -eq 0) { Write-Output ('PROGRESS downloaded '+$n+'/121') }
  }
  $configuration=@(
    [PSCustomObject]@{path='.htaccess';local='deployment/cache-fix/.htaccess';sha256=$policyHash;bytes=1230},
    [PSCustomObject]@{path='research/releases/data-v1-2a138b7808f0d12c5151/figures/structures/.htaccess';local='deployment/opaque-repair/.htaccess';sha256='f0186d0c1b566e026fb41ff967ad7b66febc9d88c00b42e355f0e4b84d9084ae';bytes=156}
  )
  foreach($file in $configuration) {
    $localBytes=[System.IO.File]::ReadAllBytes((Resolve-Within $website $file.local))
    Record-Check ('Accepted retained configuration '+$file.path) (($localBytes.Length -eq $file.bytes) -and ((Digest $localBytes) -ceq $file.sha256))
    Write-New (Resolve-Within $htdocs $file.path) $localBytes
    $rows.Add([PSCustomObject]@{path=$file.path;provenance='retained-local-accepted-configuration-not-http-downloaded';expectedSha256=$file.sha256;expectedBytes=$file.bytes;sourceRecord=('website/'+$file.local);http=$null})
  }
  $entry=$expectedMap['index.html']
  foreach($relative in @('','refresh','index.html')) {
    $got=Read-Public $relative
    Record-Check ('Current entry alias /'+$relative) (($got.metadata.bytes -eq $entry.bytes) -and ($got.metadata.sha256 -ceq $entry.sha256))
    Record-Check ('No-store entry alias /'+$relative) ($got.metadata.cacheControl -match 'no-store')
    $aliases.Add([PSCustomObject]@{path=('/'+$relative);sameAsCapturedIndex=$true;http=$got.metadata})
  }
  # Verify both manifests and their full declared payload dependency closure.
  $research = [System.IO.File]::ReadAllText((Resolve-Within $htdocs 'research/manifest.json')) | ConvertFrom-Json
  foreach($file in $research.files) {
    $relative='research/'+[string]$file.path
    $b=[System.IO.File]::ReadAllBytes((Resolve-Within $htdocs $relative))
    Record-Check ('Research manifest payload '+$relative) (($b.Length -eq $file.bytes) -and ((Digest $b) -ceq $file.sha256))
  }
  $uiManifest=[System.IO.File]::ReadAllText((Resolve-Within $htdocs ([string]$package.manifestPath))) | ConvertFrom-Json
  foreach($file in $uiManifest.files) {
    $b=[System.IO.File]::ReadAllBytes((Resolve-Within $htdocs ([string]$file.path)))
    Record-Check ('UI manifest payload '+$file.path) (($b.Length -eq $file.bytes) -and ((Digest $b) -ceq $file.sha256))
  }
  # Check emitted HTML and asset chunk references against captured paths.
  $assetRefs=[System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
  foreach($file in $package.files | Where-Object { $_.path -eq 'index.html' -or $_.path -match '\.(js|css)$' }) {
    $text=[System.IO.File]::ReadAllText((Resolve-Within $htdocs ([string]$file.path)))
    foreach($match in [regex]::Matches($text,'(?:\./)?assets/[A-Za-z0-9._-]+\.(?:js|css)')) { [void]$assetRefs.Add(($match.Value -replace '^\./','')) }
    foreach($match in [regex]::Matches($text,'(?:import\(|from\s*)["''](\./[^"'']+\.(?:js|css))["'']')) {
      $base=([string]$file.path).Substring(0,([string]$file.path).LastIndexOf('/')+1)
      [void]$assetRefs.Add($base+$match.Groups[1].Value.Substring(2))
    }
  }
  foreach($relative in $assetRefs) { Record-Check ('Emitted asset reference '+$relative) $expectedMap.ContainsKey($relative) }
  Record-Check 'Recovery tree count 123' ($rows.Count -eq 123)
  $physicalCount = [System.IO.Directory]::GetFiles($htdocs,'*',[System.IO.SearchOption]::AllDirectories).Count
  Record-Check 'No extra unrecorded files in recovery tree' ($physicalCount -eq $rows.Count)
  $scriptBytes=[System.IO.File]::ReadAllBytes($PSCommandPath)
  $report=[ordered]@{
    schemaVersion=1;status='verified-active-production-recovery-baseline';startedAt=$started;completedAt=[DateTimeOffset]::UtcNow.ToString('o')
    projectRoot=[System.IO.Path]::GetFullPath($ProjectRoot);origin=$origin;uiBuildId=$package.uiBuildId;dataReleaseId=$package.dataReleaseId
    sourcePackageRecord='website/reports/CRYSTAL_LAB_RELEASE_PACKAGE.json';sourcePackageRecordSha256=(Digest ([System.IO.File]::ReadAllBytes($packagePath)))
    activeReleaseFiles=$package.files.Count;activeReleaseBytes=$package.totalBytes;downloadedSidecars=$sidecars.Count;retainedLocalConfigurations=2;recoveryFiles=$rows.Count
    recoveryBytes=($rows | Measure-Object -Property expectedBytes -Sum).Sum
    standardPublicCookieChallengeHandled=$challengeHandled;credentialUsed=$false;cookiePersisted=$false;hostingChanged=$false
    physicalConfigurationDownloaded=$false;physicalDocumentRootEnumerated=$false;effectiveResponsesByteIdentical=$true
    resumedIncompleteCapture=[bool]$ResumeVerifiedCapture;initialCaptureFailureRecord=$(if($ResumeVerifiedCapture){'CAPTURE_FAILURE.json'}else{$null})
    scope='Complete current active application dependency recovery tree, not an exhaustive export of every physical hosting/account file. HTTP image URLs can be internally rewritten; captured effective responses and separately requested image backing sidecars are identified. Root/child configurations are exact retained accepted local bytes with their behavior checked live, not physically downloaded from hosting. Unknown, unreferenced and obsolete remote files are not enumerated by HTTP.'
    researchManifestPayloads=$research.files.Count;uiManifestPayloads=$uiManifest.files.Count;emittedAssetReferences=$assetRefs.Count
    checksPassed=$checks.Count;checksFailed=0;captureScriptSha256=(Digest $scriptBytes);aliases=$aliases.ToArray();files=$rows.ToArray();checks=$checks.ToArray()
  }
  Write-New (Join-Path $output 'PRODUCTION_BASELINE.json') ($utf8.GetBytes(($report | ConvertTo-Json -Depth 12)+[Environment]::NewLine))
  $readme=@"
# Phase 1 production recovery baseline

Captured current effective production content from $origin using read-only HTTPS requests.
Active UI: $($package.uiBuildId). Research: $($package.dataReleaseId).

- All $($package.files.Count) active release files match the retained package byte-for-byte ($($package.totalBytes) bytes).
- All $($sidecars.Count) separately downloaded image backing sidecars match the retained image inventory.
- Both root and child Apache configurations are preserved from accepted local files with exact SHA-256 verification.
- The resulting htdocs recovery tree contains $($rows.Count) files.
- Root, /refresh and /index.html returned the captured index bytes with Cache-Control: no-store.
- Research/UI manifest payloads and emitted code/chunk references resolve inside this recovery tree.
- No hosting file was changed and no account credential or challenge cookie is saved.

## Scope and provenance

This is a deployable backup of the current active application, not a physical FTP/File Manager export.
HTTP image URLs may resolve through the adapter to backing files. Both effective images and the
33 .bin backing responses are retained. The two .htaccess files were copied from the accepted local
configuration, not downloaded from the host; live behavior is checked separately. Unknown,
unreferenced and obsolete hosting files could not be enumerated by public HTTP. Historical local
production packages and account recovery records are preserved in the separate complete project backup.

## Recovery

1. Verify every htdocs file against PRODUCTION_BASELINE.json before use.
2. Preserve the current destination entry, hosting configuration and unknown files before recovery.
3. Upload required immutable assets and research payloads first; retain existing older assets.
4. Upload all .bin backing images and the child Apache configuration.
5. Apply this backup's current 1230-byte root .htaccess, not the obsolete 230-byte image-only configuration.
6. Update any mutable research pointer before uploading htdocs/index.html last.
7. Open the permanent submission link /refresh, check UI/research identities, no-store headers and actual website controls.

Use direct-file upload; ZIP extraction has not been established as byte-preserving on this host.
Recovery material and instructions are verified without performing a destructive live rollback.

## Repeating the capture

Run tools/capture-production.ps1 with ProjectRoot and a fresh OutputRoot. An existing htdocs
capture is never overwritten. A standard public-site cookie challenge is handled in memory only.
"@
  Write-New (Join-Path $output 'README.md') ($utf8.GetBytes($readme+[Environment]::NewLine))
  Write-Output ([PSCustomObject]@{Status=$report.status;ActiveFiles=$report.activeReleaseFiles;Sidecars=$report.downloadedSidecars;RecoveryFiles=$report.recoveryFiles;ChecksPassed=$report.checksPassed;Report=(Join-Path $output 'PRODUCTION_BASELINE.json')} | ConvertTo-Json -Compress)
} catch {
  $failure=[ordered]@{status='incomplete';recordedAt=[DateTimeOffset]::UtcNow.ToString('o');message=$_.Exception.Message;checks=$checks.ToArray();completedFiles=$rows.ToArray()}
  $failurePath=Join-Path $output 'CAPTURE_FAILURE.json'
  if(-not (Test-Path -LiteralPath $failurePath)) { [System.IO.File]::WriteAllText($failurePath,($failure | ConvertTo-Json -Depth 10),$utf8) }
  throw
} finally { $client.Dispose(); $cookieJar=$null }
