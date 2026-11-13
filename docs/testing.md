# Release checks and current limits

Version 0.1.0 — first community release, November 13, 2026.

The editor core was exercised locally on macOS: complete-render preview, frame stepping, cuts, Undo, raw-footage restoration, notes, saved history and corrected MP4 output. The community distribution starts with an empty workspace and includes no personal projects or footage.

Automated project tests cover immutable source references, revision recovery, stale-save protection, locked edits, playback mapping, export collision protection and mocked native-picker success/cancel/timeout. Native picker checks use mocks; its live dialog still needs user verification. Windows/Linux and a fresh-member full AI-edit-to-review workflow remain unverified.

The three bundled motion examples are generated from the included original renderer and JSON templates. They are silent full-screen scenes, not segmentation effects or transparent overlays. Core editor needs Python + FFmpeg; optional motion needs the packages listed in motion/requirements.txt. Font binaries and dependency binaries are not distributed.

The editor does not include an AI model, automatic transcription service or paid assets. The skills guide the member's own Claude/Codex session. There is no automatic agent connection from Notes.

Recovery currently assumes one uncut portrait source at normal speed, with the finished render matching its cut map. Export presets re-encode video; upscaling does not recover source detail. The UI's 2K label maps to 1440×2560. Code review or automated tests alone are not a full cross-platform certification.

Run: `python3 -m unittest discover -s tests -v` and `python3 setup.py --check`.

Release preparation verified all three MP4s at 720×1280 / 30 fps (120, 120 and 150 frames), inspected Arabic posters, and loaded the five-second steps example in an isolated editor workspace. Frame seek to 2.000s displayed frame 61. The repository screenshot contains only that synthetic example. Twenty project tests passed; all three skill frontmatters passed validation.
