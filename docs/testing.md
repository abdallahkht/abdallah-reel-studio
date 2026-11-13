# Release checks and current limits

Version 0.2.0 — visual gallery and six motion templates, November 13, 2026. The editor behavior is unchanged from the initial 0.1.0 release.

The editor core was exercised locally on macOS: complete-render preview, frame stepping, cuts, Undo, raw-footage restoration, notes, saved history and corrected MP4 output. The community distribution starts with an empty workspace and includes no personal projects or footage.

Automated project tests cover immutable source references, revision recovery, stale-save protection, locked edits, playback mapping, export collision protection and mocked native-picker success/cancel/timeout. Native picker checks use mocks; its live dialog still needs user verification. Windows/Linux and a fresh-member full AI-edit-to-review workflow remain unverified.

The six current bundled motion examples are generated from the included original renderer and JSON templates. They are silent full-screen scenes, not segmentation effects or transparent overlays. Core editor needs Python + FFmpeg; optional motion needs the packages listed in motion/requirements.txt. IBM Plex Sans Arabic font files are bundled with their OFL license. Dependency binaries are not distributed.

The editor does not include an AI model, automatic transcription service or paid assets. The skills guide the member's own Claude/Codex session. There is no automatic agent connection from Notes.

Recovery currently assumes one uncut portrait source at normal speed, with the finished render matching its cut map. Export presets re-encode video; upscaling does not recover source detail. The UI's 2K label maps to 1440×2560. Code review or automated tests alone are not a full cross-platform certification.

Run: `python3 -m unittest discover -s tests -v` and `python3 setup.py --check`.

Initial 0.1.0 release preparation verified all three MP4s at 720×1280 / 30 fps (120, 120 and 150 frames), inspected Arabic posters, and loaded the five-second steps example in an isolated editor workspace. Frame seek to 2.000s displayed frame 61. The repository screenshot contains only that synthetic example. Twenty project tests passed; all three skill frontmatters passed validation.

## 0.2.0 presentation checks

All six current demo MP4s were verified at 1080×1920 / 30 fps (120 frames each, steps 150). Arabic posters were visually inspected. The 25-second synthetic showcase was opened in an isolated editor workspace; seeks to 6.000, 10.000 and 22.000 seconds showed frames 181, 301 and 661. A timestamped Arabic note was added and saved. The review GIF uses three real captured UI states.

Gallery checked in the in-app browser at desktop width 1280 and phone width 390, with no horizontal overflow. The caption video opened and played at its native 1080×1920 dimensions; closing the dialog worked. Twenty editor tests passed, setup dependency checks passed, and Python/JavaScript syntax checks passed. The cover is a 1920×1080 composition with genuine Claude SVG geometry.
