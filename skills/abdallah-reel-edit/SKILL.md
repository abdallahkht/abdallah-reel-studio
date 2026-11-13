---
name: abdallah-reel-edit
description: Edit Arabic 9:16 Reels from raw footage and optional references, then deliver the complete video to Abdallah Reel Studio for small final corrections. Use when a community member requests a full short-form edit.
---

# Arabic Reel editing

Locate the kit by resolving this skill's real path and going up two directories; on Windows read `app-location.txt` beside the installed skill. Read `docs/workflow-ar.md` there for the project layout.

The user gives footage and a brief, optionally a reference, screen recordings, logos or images. Perform the full edit with the tools available in their AI session. Preserve any existing personal editing skill and style instructions. This kit is a starting workflow, not a built-in AI service: it does not provide a Claude/Codex subscription, transcription API or paid assets.

1. Inspect media dimensions, frame rate, duration and audio. Transcribe with a locally available tool or the user's chosen provider. Confirm uncertain Arabic words by listening. If no transcription capability is available, explain the specific missing dependency; do not invent speech or timestamps.
2. Choose complete, coherent takes. Remove restarts, repeated takes and unnecessary pauses without cutting word endings or changing the speaker's meaning. Do not impose a fixed short duration. Keep all raw inputs immutable.
3. For landscape footage, make an uncut portrait composition first and use it as the recovery source. Keep the speaker visible. Do not add routine face punch-ins. Place graphics away from the face, including during transitions. A reference informs pacing and visual treatment; use supplied or permitted assets and never copy its presenter or watermark.
4. Save exact source cut decisions in `raw/edl.json`, using `src` in source seconds and integer `n` frame counts at the chosen fps. Preserve normal speed and avoid overlapping source ranges for editor recovery. Store the absolute source path in `raw/raw.json`. See `skills/abdallah-reel-review/references/delivery.md` for the contract.
5. Complete the creative edit: deliberate, word-timed motion, relevant real screen recordings, Arabic captions if requested, and restrained sound. Read `skills/abdallah-reel-motion-kit/SKILL.md` when graphics help. Captions use RTL shaping and phone-readable short phrases; don't translate the speaker's language unless asked.
6. Render a complete 1080×1920 MP4 including all graphics and audio. Listen at each cut, check first/last frames of overlays, and verify duration, dimensions, frame rate and audio with ffprobe. The final duration must match the cut map within one frame. Keep the editable code and assets alongside the render.
7. Follow `skills/abdallah-reel-review/SKILL.md` to import the finished video and original footage for review. A cuts-only file is not a finished creative edit unless the user asked for cuts only.

For revisions, read the current review notes and locked cuts before changing the editable project. Small manual corrections must survive the next AI edit. A restored raw moment may need new audio/graphics work; make that change in the source project and deliver a new complete render.
