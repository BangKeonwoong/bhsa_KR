# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2025-09-08
### Added
- Right-side Versions panel with KNT/NKRV/BHS support.
- Unified endpoint `/api/versions/chapter?version=knt|nkrv|bhs&book=...&chapter=...` with ETag/Last-Modified.
- Verse hover highlights corresponding clauses in the tree (x1.25).
- Verse click selects the first clause in the details panel.
- Accessibility: keyboardable verse items (Enter/Space), Escape to close, focus trap, aria labelling.

### Changed
- Consolidated versions data under `versions/{KNT,NKRV,BHS}` with flexible path detection (`VERSIONS_DIR`, `KNT_DIR`, `NKRV_DIR`, `BHS_DIR`).

## [0.2.2] - 2025-09-07
### Changed
- Release workflow: ensure OS-specific and portable ZIP assets are attached reliably (direct file list, no env var aggregation)

## [0.2.1] - 2025-09-07
### Added
- macOS double-click launcher: `Start Viewer.command` (uses AUTO_INSTALL=1)
- Windows portable package build: embeddable Python + preinstalled deps; `Start Viewer (Portable).bat`
- Platform-specific quick-start docs (README-RUN-*.txt) and FIRST-RUN-CHECKLIST.md

### Changed
- Release workflow builds OS-specific ZIPs (windows/macos) and a portable Windows ZIP
- README: beginner quick start, macOS Gatekeeper guidance, release ZIP usage

### Fixed
- Windows: robust pip bootstrap and embeddable Python site enabling (fixes "No module named pip")

## [0.2.0] - 2025-09-07
### Added
- Beginner-friendly quick start for Windows/macOS in README
- Windows: auto-download embeddable Python if missing (start_viewer.ps1)
- Windows: setup helper (setup_windows.ps1) to install Python/Git via winget
- macOS: AUTO_INSTALL=1 in run.sh to install Python via Homebrew
- OpenAPI spec and Redoc docs at `/api/docs`
- Request-ID propagation, simple CORS toggle, `/api/version`
- Spinner/toast UI, URL deep-linking, localStorage preferences
- CI workflow to run tests on push/PR

### Changed
- Refactor to app factory + blueprints; config/logging/errors/middleware modularization
- Cache-Control tuning for `/api/tree` (lite/full), env-tunable LRU caches
- Weak ETag for compressed responses; nocache toggle to bypass caches
- `/api/tree` supports `max_depth` pruning

### Fixed
- PowerShell 5.1 compatibility for start_viewer.ps1 (no heredoc/ternary)
- Submodule auto-init in launchers; improved ASCII-only messages on Windows

## [0.1.0] - 2025-08-??
- Initial import
