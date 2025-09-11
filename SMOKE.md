Lightweight E2E Smoke Checklist

Goal: Verify core flows quickly after changes.

1) Load Tree
- Open / (default Genesis 1). Ensure tree renders and toolbar works.
- Toggle orientation and view (Tidy/List) once each.

2) Versions Panel
- Click ‘역본’ to open panel. Selector shows KNT/NKRV/BHS.
- With KNT selected, verses render for current chapter.
- Hover a verse: matching clauses in tree enlarge (~1.25x).
- Click a verse: details panel opens; first clause auto-selected and centered.
- Change version to NKRV and BHS; ensure verses load (if present) or show empty state.
- Close the panel with the × button and Escape; re-open retains last selected version.

3) Details Navigation
- Use ‘이전 절/다음 절’ in details header: selection moves; panel active verse follows.

4) Persistence
- Refresh page: versions panel open/closed state persists; version selection persists.

5) API spot checks (devtools Network)
- /api/tree, /api/versions/chapter (knt/nkrv/bhs) return 200, with ETag and Cache-Control.

Notes
- If custom data roots are used, set VERSIONS_DIR or specific KNT_DIR/NKRV_DIR/BHS_DIR.
