# Changelog

All notable changes to this project will be documented in this file.

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

