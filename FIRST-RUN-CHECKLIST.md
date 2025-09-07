# First Run Checklist

Use this quick checklist to verify the app runs correctly on your machine.

1) Get the app
- Developers: `git clone --recurse-submodules ...`
- End users: download OS‑specific ZIP from Releases (BHSA datasets are not included; they can be used from your Text‑Fabric cache or fetched on demand).

2) Launch
- Windows: `start_viewer.bat` (or `setup_windows.ps1 -AutoInstall`)
- macOS: double‑click `Start Viewer.command` (or `./run.sh`)

3) Python availability
- Windows: launcher auto‑downloads the official embeddable Python 3.11 if Python is missing.
- macOS: set `AUTO_INSTALL=1` for Homebrew install of Python if needed.

4) Dependencies
- The launcher creates `.venv` and installs packages. This may take a few minutes the first time.
- Offline: place required `.whl` files under `data/wheels/` to avoid network.

5) TF/BHSA data
- If you already have Text‑Fabric data (e.g., `%USERPROFILE%\text-fabric-data` on Windows or `~/text-fabric-data` on macOS), the launcher will try to use it.
- You can also clone with submodules to keep BHSA as part of the repository for development.

6) Open the app
- Browser: http://127.0.0.1:5001/
- Expected: top status shows “TF gloss 사용 가능” when BHSA/Gloss are available.

7) Verify endpoints
- Windows (PowerShell): `Invoke-RestMethod http://127.0.0.1:5001/api/tf/status`
- macOS/Linux: `curl http://127.0.0.1:5001/api/tf/status`

8) Common issues
- Firewall prompt: allow access.
- PowerShell execution policy: use `start_viewer.bat` on Windows.
- Port conflict: set a different port: `PORT=5002` (env) before running the launcher.
- Gatekeeper (macOS): right‑click → Open; or `xattr -d com.apple.quarantine` on blocked files; add execute bit `chmod +x` if needed.

9) Need help?
- Check `/api/version`, `/healthz`, `/api/gloss/status`.
- Review README‑RUN‑windows.txt / README‑RUN‑macOS.txt for platform tips.

