#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'

# Move to script directory
Set-Location -LiteralPath $PSScriptRoot

Write-Host "[CTT Viewer] Project: $PSScriptRoot"

function Resolve-Python {
  $candidates = @('python', 'py')
  foreach ($c in $candidates) {
    try {
      $ver = & $c -c "import sys; print(sys.version)" 2>$null
      if ($LASTEXITCODE -eq 0 -and $ver) { return $c }
    } catch {}
  }
  throw "No Python interpreter found in PATH. Install Python 3 first."
}

function Get-ArchTag {
  try {
    if ([Environment]::Is64BitOperatingSystem) { return 'amd64' } else { return 'win32' }
  } catch { return 'amd64' }
}
function Set-Tls12 {
  try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}
}
function Download-FileOnce($url, $dst) {
  Set-Tls12
  # Prefer Invoke-WebRequest
  try {
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $dst -TimeoutSec 90
    return $true
  } catch {}
  # Try curl.exe if available
  try {
    if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
      & curl.exe -L --connect-timeout 15 --max-time 120 -o $dst $url
      if ($LASTEXITCODE -eq 0 -and (Test-Path $dst)) { return $true }
    }
  } catch {}
  # Fallback to WebClient
  try {
    $wc = New-Object System.Net.WebClient
    $wc.DownloadFile($url, $dst)
    return $true
  } catch {}
  return $false
}
function Download-File($url, $dst, $retries=3) {
  for ($i=1; $i -le [Math]::Max(1,$retries); $i++) {
    Write-Host "[CTT Viewer] Downloading: $url (attempt $i)"
    if (Download-FileOnce $url $dst) {
      try {
        $info = Get-Item -LiteralPath $dst -ErrorAction Stop
        if ($info.Length -gt 1000000) { return $true } # >1MB looks sane
      } catch {}
    }
    Start-Sleep -Seconds ([Math]::Min(5*$i,15))
  }
  return $false
}
function Ensure-EmbeddedPython {
  $embedDir = Join-Path $PSScriptRoot 'python-embed'
  $embedExe = Join-Path $embedDir 'python.exe'
  if (Test-Path $embedExe) { return $embedExe }
  Write-Host "[CTT Viewer] Downloading Python embeddable (one-time)"
  $ver = '3.11.8'
  $arch = Get-ArchTag
  $zip = Join-Path $PSScriptRoot "python-${ver}-embed-${arch}.zip"
  $defaultUrl = "https://www.python.org/ftp/python/${ver}/python-${ver}-embed-${arch}.zip"
  $overrideUrl = $env:PY_EMBED_URL
  $url = if ([string]::IsNullOrEmpty($overrideUrl)) { $defaultUrl } else { $overrideUrl }
  if (-not (Download-File $url $zip 3)) {
    # Last resort: try default URL if override was set and vice versa
    if ([string]::IsNullOrEmpty($overrideUrl)) {
      Write-Host "[CTT Viewer] Download failed: $defaultUrl"
    } else {
      Write-Host "[CTT Viewer] Download failed: $url; retrying with default: $defaultUrl"
      if (-not (Download-File $defaultUrl $zip 2)) {
        Write-Host "[CTT Viewer] Failed to download Python embeddable. Please install Python 3 manually."
        exit 1
      }
    }
  }
  try {
    if (-not (Test-Path $embedDir)) { New-Item -ItemType Directory -Force -Path $embedDir | Out-Null }
    Expand-Archive -LiteralPath $zip -DestinationPath $embedDir -Force
    # Ensure embeddable Python loads site-packages (required for pip)
    try {
      $pth = Get-ChildItem -LiteralPath $embedDir -Filter "python*._pth" -File | Select-Object -First 1
      if ($pth) {
        $lines = Get-Content -LiteralPath $pth.FullName
        $hasImportSite = $false
        $new = @()
        foreach ($ln in $lines) {
          if ($ln -match '^\s*#\s*import site\s*$') { $new += 'import site'; $hasImportSite = $true }
          elseif ($ln -match '^\s*import site\s*$') { $new += $ln; $hasImportSite = $true }
          else { $new += $ln }
        }
        if (-not $hasImportSite) { $new += 'import site' }
        Set-Content -LiteralPath $pth.FullName -Value $new -Encoding ASCII
      }
    } catch {}
  } catch {
    Write-Host "[CTT Viewer] Failed to extract Python embeddable."
    exit 1
  } finally { try { Remove-Item -Force $zip } catch {} }
  return $embedExe
}

$python = $null
try { $python = Resolve-Python } catch { $python = $null }
$useEmbedded = $false
if (-not $python) {
  $embedPy = Ensure-EmbeddedPython
  $python = $embedPy
  $useEmbedded = $true
  Write-Host "[CTT Viewer] Using embedded Python: $python"
} else {
  Write-Host "[CTT Viewer] Python: $python"
}

$venvDir = Join-Path $PSScriptRoot '.venv'
$resetVenv = $false
if (-not [string]::IsNullOrEmpty($env:RESET_VENV)) {
  $resetVenv = ($env:RESET_VENV -eq '1')
}
if ($resetVenv -and (Test-Path $venvDir)) {
  Write-Host "[CTT Viewer] Reset venv (.venv)"
  try { Remove-Item -Recurse -Force -LiteralPath $venvDir } catch {}
}
$venvActivate = Join-Path $venvDir 'Scripts\Activate.ps1'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
if (-not $useEmbedded -and (-not (Test-Path $venvActivate) -or -not (Test-Path $venvPython))) {
  Write-Host "[CTT Viewer] Creating venv (.venv)"
  & $python -m venv $venvDir
}

if (-not $useEmbedded) {
  # Activate venv
  Write-Host "[CTT Viewer] Activate venv (.venv)"
  . $venvActivate
}

# Ensure git submodules are initialized
try {
  if (Test-Path "$PSScriptRoot/.git") {
    $status = & git submodule status 2>$null
    if ($status -match "^-\w+") {
      Write-Host "[CTT Viewer] Initializing/updating git submodules (clone with --recurse-submodules recommended)"
      & git submodule update --init --recursive | Out-Null
    }
  }
} catch {}

function Repair-Pip {
  Write-Host "[CTT Viewer] Repair pip via ensurepip"
  try { & $venvPython -m ensurepip -U --default-pip | Out-Null } catch {}
}
function Ensure-Pip {
  try { & $venvPython -m pip --version | Out-Null } catch { Repair-Pip }
  try { & $venvPython -m pip --version | Out-Null } catch {
    Write-Host "[CTT Viewer] Bootstrapping pip (get-pip.py)"
    $tmp = [System.IO.Path]::GetTempFileName() + '.py'
    try {
      if (-not (Download-File 'https://bootstrap.pypa.io/get-pip.py' $tmp 3)) { throw "get-pip download failed" }
      & $venvPython $tmp
    } finally { if (Test-Path $tmp) { Remove-Item $tmp -Force } }
  }
}
if ($useEmbedded) {
  # Install pip into embedded via get-pip, best-effort
  Write-Host "[CTT Viewer] Prepare pip for embedded Python"
  try {
    & $python -m pip --version | Out-Null
  } catch {
    $tmp = [System.IO.Path]::GetTempFileName() + '.py'
    try {
      if (-not (Download-File 'https://bootstrap.pypa.io/get-pip.py' $tmp 3)) { throw "get-pip download failed" }
      & $python $tmp
    } finally { if (Test-Path $tmp) { Remove-Item $tmp -Force } }
  }
} else {
  Ensure-Pip
}

# Install dependencies (fast, offline-aware)
$req = Join-Path $PSScriptRoot 'requirements.txt'
if (Test-Path $req) {
  Write-Host "[CTT Viewer] Installing dependencies"
  $skip = ($env:SKIP_PIP -eq '1')
  if (-not $skip) {
    # Quick module check to skip pip when already satisfied
    $importOk = $false
    try {
      if ($useEmbedded) {
        & $python -c "import importlib; importlib.import_module('flask'); importlib.import_module('tf.fabric')" 2>$null
      } else {
        & $venvPython -c "import importlib; importlib.import_module('flask'); importlib.import_module('tf.fabric')" 2>$null
      }
      if ($LASTEXITCODE -eq 0) { $importOk = $true }
    } catch {}
    if ($importOk) {
      Write-Host "[CTT Viewer] Modules already satisfied; skip pip"
    } else {
      if ($useEmbedded) {
        $embeddedSite = Join-Path $PSScriptRoot 'python-embed\site-packages'
        if (-not (Test-Path $embeddedSite)) { New-Item -ItemType Directory -Force -Path $embeddedSite | Out-Null }
        try { & $python -m pip install -r $req -t $embeddedSite } catch {}
        $env:PYTHONPATH = "$embeddedSite;$PSScriptRoot"
      } else {
        $env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
        if (-not [string]::IsNullOrEmpty($env:PIP_DEFAULT_TIMEOUT)) { } else { $env:PIP_DEFAULT_TIMEOUT = '10' }
        # Install from local wheels if present
        $wheelsDir = Join-Path $PSScriptRoot 'data\wheels'
        if (Test-Path $wheelsDir) {
          $wheels = Get-ChildItem -Path (Join-Path $wheelsDir '*.whl') -ErrorAction SilentlyContinue | Select-Object -First 1
          if ($wheels) {
            Write-Host "[CTT Viewer] Installing from local wheels (data\wheels)"
            try { & $venvPython -m pip install --no-index --find-links $wheelsDir -r $req } catch {}
          }
        }
        # If still missing Flask, try online best-effort
        $haveFlask = $false
        try { & $venvPython -c "import flask" 2>$null; if ($LASTEXITCODE -eq 0){ $haveFlask = $true } } catch {}
        if (-not $haveFlask) {
          try {
            if ($env:UPGRADE_PIP -eq '1') { & $venvPython -m pip install --upgrade 'pip<25' | Out-Null }
          } catch {}
          try { & $venvPython -m pip install -r $req } catch {}
        }
      }
    }
  } else {
    Write-Host "[CTT Viewer] SKIP_PIP=1; skip pip install"
  }
}

# Prefer local TF data inside project; copy from user cache if available
$LocalTf = Join-Path $PSScriptRoot 'data\text-fabric-data'
$UserTfBhsa = Join-Path $env:USERPROFILE 'text-fabric-data\etcbc\bhsa'
$LocalBhsa = Join-Path $LocalTf 'etcbc\bhsa'
if (-not (Test-Path $LocalBhsa) -and (Test-Path $UserTfBhsa)) {
  Write-Host "[CTT Viewer] Copying TF data from user cache into project (first run)"
  New-Item -ItemType Directory -Force -Path (Split-Path $LocalBhsa) | Out-Null
  try { Copy-Item -Recurse -Force -Path $UserTfBhsa -Destination (Split-Path $LocalBhsa) } catch {}
}
$env:TF_LOCAL_DIR = $LocalTf
# Prefer project dir first so .\bhsa is used when present
$env:TF_LOCATIONS = "$PSScriptRoot;$LocalTf"

# Optional: check TF updates on every launch (default OFF). Enable by setting TF_UPDATE_ON_START=1
# if (-not $env:TF_UPDATE_ON_START) { $env:TF_UPDATE_ON_START = '0' }

# Auto-detect Korean gloss CSV if not set
if (-not $env:GLOSS_KO_CSV) {
  $dataDir = Join-Path $PSScriptRoot 'data'
  if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Force -Path $dataDir | Out-Null }
  $bundled = Join-Path $dataDir 'gloss_ko.csv'
  if (Test-Path $bundled) {
    $env:GLOSS_KO_CSV = $bundled
  } else {
    $dl = Join-Path $env:USERPROFILE 'Downloads'
    $hit = Get-ChildItem -Path (Join-Path $dl 'all_gloss_*.csv') -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $hit) { $hit = Get-ChildItem -Path (Join-Path $dl '*\all_gloss_*.csv') -ErrorAction SilentlyContinue | Select-Object -First 1 }
    if ($hit) {
      Copy-Item -Path $hit.FullName -Destination $bundled -Force
      $env:GLOSS_KO_CSV = $bundled
      Write-Host "[CTT Viewer] Copy gloss CSV: $($hit.FullName) -> $bundled"
    }
  }
}

# Prefetch 기능 제거됨(패키징 스크립트 삭제). 최초 실행 시 필요한 범위만 자동 캐시합니다.

# Resolve a Python executable
$env:PYTHONUNBUFFERED = '1'
$hostAddr = '127.0.0.1'
$candidates = @(5000,5001,5173,8000,5050,5051,7000,7001)
function Find-FreePort {
  param([int[]]$Ports)
  foreach ($p in $Ports) {
    try {
      $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $p)
      $listener.Start(); $listener.Stop(); return $p
    } catch {}
  }
  return 5000
}
$port = Find-FreePort -Ports $candidates
$url = "http://$hostAddr:5001/"
$env:HOST = $hostAddr
$env:PORT = 5001

# Start Flask app in a separate window (venv python)
Write-Host "[CTT Viewer] Starting server: $url"
$pyToRun = $venvPython
if ($useEmbedded) { $pyToRun = $python }
$startInfo = @{ FilePath = $pyToRun; ArgumentList = 'app.py'; WorkingDirectory = $PSScriptRoot; WindowStyle = 'Normal'; }
$proc = Start-Process @startInfo -PassThru

# Wait for server (best-effort up to ~10s)
for ($i=0; $i -lt 40; $i++) {
  Start-Sleep -Milliseconds 250
  try {
    $resp = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2
    if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) { break }
  } catch {}
}

# Open default browser
Write-Host "[CTT Viewer] Opening: $url"
Start-Process $url | Out-Null

Write-Host "[CTT Viewer] Server is running in a separate window. Close that window to stop."
