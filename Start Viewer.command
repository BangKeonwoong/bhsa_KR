#!/bin/bash
# macOS double-click launcher (delegates to run.sh with auto-install)
set -euo pipefail
cd "$(cd "$(dirname "$0")" && pwd)"
export AUTO_INSTALL="${AUTO_INSTALL:-1}"
chmod +x ./run.sh 2>/dev/null || true
exec ./run.sh

