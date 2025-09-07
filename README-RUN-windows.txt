CTT Viewer — Windows Quick Start
================================

1) Unzip the archive to a writable folder (e.g., Desktop).

2) Run (recommended)
   - Double‑click: start_viewer.bat
     (Bypasses PowerShell execution policy automatically.)

   Alternative (PowerShell):
   - powershell -NoProfile -ExecutionPolicy Bypass -File .\start_viewer.ps1

3) First run
   - If Python is missing, an official embeddable Python 3.11 is downloaded and used.
   - Dependencies are installed into local .venv.

4) Optional helper (winget)
   - PowerShell> .\setup_windows.ps1 -AutoInstall
     (Installs Python/Git via winget, then launches the app.)

5) Open the app
   - http://127.0.0.1:5001/

Troubleshooting
---------------
- Use .\start_viewer.bat to avoid execution policy errors.
- Allow firewall prompt on first run.
- Check status: Invoke-RestMethod http://127.0.0.1:5001/api/tf/status
- Offline: put .whl files under data\wheels\ so the launcher can install offline.

