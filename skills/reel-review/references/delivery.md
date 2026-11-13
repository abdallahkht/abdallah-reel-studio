# Delivery contract

App root is three folders above this file. Run its `server.py` on loopback port 4318. `connect.py` checks the running app and registers an existing finished render without changing the editing skill's project.

The adapter expects:

```text
project/
  raw/raw.json
  raw/edl.json
  raw/chunks.json   # optional
```

`raw.json`: `{"source":"/absolute/path/to/uncut-portrait-source.mp4"}`.

`edl.json`: `{"fps":30,"pieces":[{"src":4.733333333,"n":27},{"src":20.066666667,"n":122}]}`. Each piece maps original source seconds to the next span of finished output; `n / fps` is its length. `f0 / fps` may replace `src`. The output can contain any rendered graphics or reference-based visuals, but its narration/cut timing must correspond to this map.

`chunks.json`: array of `{s,e,text,words?}` in original source seconds. Do not translate source transcript timestamps into output seconds here.

The completed MP4 must be 9:16 and match the sum of kept durations within one frame. The current recovery map assumes one source with non-overlapping source ranges and normal speed. For a landscape recording, your editing skill can first produce an uncut portrait composition and map cuts against that source. Do not invent a map for speed ramps, freeze-frame extensions or multiple narration sources. Report the mismatch and retain the finished MP4; source recovery for those projects needs a richer map.

Use the `--notes ID` output before revising an already reviewed project. It includes all source ranges, enabled/excluded state, locks and notes. Reconcile those changes into the original editable project. A new final delivery gets its own review project and URL; the earlier review remains available.

The UI saves notes and corrections automatically. Source cuts use original seconds. Notes include both the viewed timestamp and, for new notes, `sourceTime`. Output seconds can move after earlier cuts are changed, so use source anchors when locating the actual word.

For cut-only API updates, GET `/api/state` for the local session token and GET `/api/projects/ID/handoff` for the current revision. POST `/api/projects/ID/save` with `{project,actor:"ai",reason}` and `X-Reel-Token`. The server rejects stale revisions and changes to locked clips. Do not write its project JSON directly. Keep source and finished media immutable.

Export options: POST `/api/projects/ID/export` with `{revision,settings:{height:1920,fps:30,quality:"high"}}`. Optional settings `directory` (existing absolute folder path) and `filename` save a copy there without overwriting existing files. Heights: 1280/1920/2560/3840; frame rates: 24/25/30/50/60; quality: high/standard/draft. This re-encodes the review timeline. Higher resolution/frame rate cannot recover detail or frames missing from the finished AI render.
