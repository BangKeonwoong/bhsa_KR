@echo off
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION
pushd "%~dp0"

REM Run the PowerShell helper with execution policy bypass to avoid policy blocks
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_windows.ps1" %*

popd
endlocal

