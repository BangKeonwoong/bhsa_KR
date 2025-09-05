@echo off
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION

REM Minimal ASCII-only Windows launcher delegating to PowerShell to avoid encoding issues.
pushd "%~dp0"

REM Use PowerShell to run the cross-version startup logic.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_viewer.ps1"

popd
endlocal
