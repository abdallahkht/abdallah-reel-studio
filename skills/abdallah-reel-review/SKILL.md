---
name: abdallah-reel-review
description: Open a completed AI-edited portrait video in Abdallah Reel Studio with original-footage recovery, and read timestamped notes for revisions. Use after the creative edit is finished or when handling review corrections.
---

# Deliver to the review editor

Find the kit by resolving this skill's real path and going up two directories. On Windows use `app-location.txt`. Read `references/delivery.md` when preparing a recovery map or resolving an import mismatch.

Use the member's existing editing skill, or the included `abdallah-reel-edit` starter, to complete the creative edit first. Preserve that skill's pacing, language and style. The review editor is for frame stepping, tiny trims/restoration, notes and export; it does not perform AI editing by itself.

1. Keep the finished MP4, editable source project and original footage. The MP4 must include all intended graphics, captions, inserts and sound.
2. Supply `raw/raw.json`, `raw/edl.json` and optionally `raw/chunks.json`, matching the exact final timeline. Current recovery supports one uncut portrait source at normal speed. Don't invent a recovery map for unsupported retiming or multiple narration sources.
3. Start `python3 launcher.py` from the repository if the editor is not running. Then run:

```sh
python3 connect.py --project /path/to/edit-project --edit /path/to/finished.mp4 --name "My Reel"
```

4. Wait for preview preparation and open the returned review URL. Give the user the final file and the review link, briefly.

Before revisions, run `python3 connect.py --notes PROJECT_ID`. Read source-anchored notes, enabled/excluded ranges and locked cuts. Honor manual corrections. Graphics changes happen in the editable project, followed by a new complete render and review project. Notes are instructions for the next AI session; they do not automatically run an agent.

Export from the app writes the current reviewed timeline to the folder the user chooses. Do not pick a destination or export merely to demonstrate the feature. Original media stays unchanged, and collisions receive a new filename.
