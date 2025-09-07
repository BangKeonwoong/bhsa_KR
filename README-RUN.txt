CTT Viewer — Windows Quick Start
================================

1) Unzip the release archive to a folder you control (e.g., Desktop).

2) Run (recommended)
   - Double‑click: start_viewer.bat
     (This bypasses PowerShell execution policy automatically.)

   Alternative (PowerShell):
   - powershell -NoProfile -ExecutionPolicy Bypass -File .\start_viewer.ps1

3) First run behavior
   - If Python is not installed, the launcher downloads and uses
     the official embeddable Python 3.11 package automatically.
   - Dependencies are installed into a local virtual environment (.venv).

4) Optional helper (winget)
   - If you prefer system installs via winget:
     PowerShell> .\setup_windows.ps1 -AutoInstall
     (Installs Python/Git via winget, then launches the app.)

5) Open in your browser
   - http://127.0.0.1:5001/
   - Top status should read: "TF gloss 사용 가능" when BHSA/Gloss are available.

6) Offline/limited network
   - Place pre‑downloaded .whl files under data\wheels\ then run the launcher.
   - The launcher will try to use local wheels first.

7) Notes
   - Windows may prompt for firewall permission on first run. Allow access.
   - If PowerShell blocks scripts, always use start_viewer.bat (it bypasses policy).
   - The release ZIP excludes the large BHSA datasets. The app can use
     your existing Text‑Fabric cache (e.g., %USERPROFILE%\text-fabric-data)
     or fetch BHSA on demand.

Troubleshooting
---------------
PowerShell version:
  $PSVersionTable.PSVersion

Check TF status:
  PowerShell> Invoke-RestMethod http://127.0.0.1:5001/api/tf/status

Common fixes:
  - Run start_viewer.bat from the app folder (current directory matters)
  - If port 5001 is in use, close the other app and try again
  - Antivirus/SmartScreen prompts must be allowed

