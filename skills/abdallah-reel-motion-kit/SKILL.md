---
name: abdallah-reel-motion-kit
description: Create Arabic titles, word highlights, comparisons, quotes, metric cards and step explainers for Reels using the original editable motion starter pack in Abdallah Reel Studio. Use for short animated scenes or graphics inside an edit.
---

# Arabic motion starter pack

Locate the repository by resolving this skill's real path and going up two directories; on Windows read `app-location.txt`. Read `motion/README.md` for renderer commands and template fields.

The supplied pack has six original starting points: `title`, `caption`, `compare`, `metric`, `quote` and `steps`. These are editable full-screen scenes, not automatic face segmentation or a general VFX engine. For a different concept, build a new scene with the user's available tools. Never claim an effect exists in the pack if it does not.

Use Arabic as written by the user, with proper RTL shaping. Keep the narration's language; don't insert English labels by default. Use the bundled OFL-licensed IBM Plex Sans Arabic, or a font installed on the member's own computer that they have permission to use. Do not copy commercial font files into the project for distribution.

Motion decisions:
- Tie each visual change to the word or idea it explains. Choose one dominant idea per scene.
- Specify palette, type hierarchy, entrance, hold and exit. Let the landed headline stay still. Avoid endless pulsing and a repeated slide-up treatment for every object.
- Use short eased arrivals (about 0.3–0.6s), stagger related steps, and hold long enough to read. Data values must come from the user's material; template numbers are illustrative.
- In a presenter edit, don't obscure the face. These templates render full-frame MP4s; use them as deliberate B-roll or adapt the compositor before making an overlay.
- Use actual product screenshots/recordings for product demonstrations. Do not draw a fake interface and present it as a captured product.

Copy a template JSON into the member's working project and edit its text, colors and duration. Render it using the documented script, inspect the poster and decoded transition/hold frames, then check the MP4 with ffprobe. Fix broken Arabic, clipped text, illegible contrast or animation collisions before placing it in the final edit. Match the final video's frame rate and use an explicit duration.

Keep generated media in the member's project. Do not modify bundled examples as a side effect of editing their video.
