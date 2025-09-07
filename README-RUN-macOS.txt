CTT Viewer — macOS Quick Start
==============================

1) Unzip the archive, then open the folder in Finder.

2) Double‑click launcher (recommended)
   - Start Viewer.command
     (Internally runs ./run.sh with AUTO_INSTALL=1 to install Python via Homebrew when missing.)

   Alternative (Terminal):
   - ./run.sh
   - AUTO_INSTALL=1 ./run.sh   # attempt Homebrew install of Python

3) First run notes (Gatekeeper)
   - If macOS blocks the file as from the Internet, open System Settings → Privacy & Security → Allow Anyway.
   - Or remove quarantine: xattr -d com.apple.quarantine "Start Viewer.command"
   - Ensure execute bit: chmod +x "Start Viewer.command" ./run.sh

4) Open the app
   - http://127.0.0.1:5001/

Troubleshooting
---------------
- Install Homebrew if missing: /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
- Then: brew install python
- Check status: curl http://127.0.0.1:5001/api/tf/status

