#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'

# Simple prerequisite installer for Windows (optional)
# - Installs Python 3 and Git via winget when AUTO_INSTALL=1
# - Then launches start_viewer.bat

param(
  [switch]$AutoInstall
)

Set-Location -LiteralPath $PSScriptRoot
Write-Host "[CTT Viewer] Windows setup helper"

function Have-Cmd($name){ try { Get-Command $name -ErrorAction Stop | Out-Null; return $true } catch { return $false } }

$doAuto = $AutoInstall.IsPresent -or ($env:AUTO_INSTALL -eq '1')

if ($doAuto -and (Have-Cmd 'winget')) {
  # Install Python if missing
  if (-not (Have-Cmd 'python') -and -not (Have-Cmd 'py')) {
    Write-Host "[CTT Viewer] Installing Python 3 via winget"
    try { winget install -e --id Python.Python.3.11 -h } catch {}
  }
  # Install Git if missing
  if (-not (Have-Cmd 'git')) {
    Write-Host "[CTT Viewer] Installing Git via winget"
    try { winget install -e --id Git.Git -h } catch {}
  }
}
else {
  if (-not $doAuto) { Write-Host "[CTT Viewer] AUTO_INSTALL=1 로 자동 설치 활성화 가능" }
  if (-not (Have-Cmd 'winget')) { Write-Host "[CTT Viewer] winget이 없습니다. 수동 설치를 진행합니다." }
}

Write-Host "[CTT Viewer] Launching start_viewer.bat"
cmd /c ".\start_viewer.bat"

