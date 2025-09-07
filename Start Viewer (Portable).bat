@echo off
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION
pushd "%~dp0"

REM Run app with embedded Python; no PowerShell, no pip required
set "TF_LOCAL_DIR=%CD%\data\text-fabric-data"
set "TF_LOCATIONS=%CD%;%CD%\data\text-fabric-data"

"%~dp0python-embed\python.exe" "%~dp0app.py"

popd
endlocal

