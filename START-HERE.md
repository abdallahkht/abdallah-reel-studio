# Your first reel

1. Unzip the download and keep the whole folder together. The gallery shows examples. The review editor runs on your own computer.
2. Install Python 3.10+ and FFmpeg. Open the extracted folder in Claude Code or Codex. Ask **«جهّز المشروع وثبّت مهاراته، وبعدين افتح لي المحرر.»** The setup command is `python3 setup.py`. For the motion templates use `python3 setup.py --motion`. Reopen your assistant session after setup.
3. Give the assistant your raw video, any optional reference, and a short brief. Keep each reel’s originals and references together in a folder of your choice. For example: **«مونتج هذا الفيديو كريل عمودي. استخدم الملف الثاني كمرجع، وافتح النتيجة في المحرر مع إمكانية استرجاع القصّات.»**
4. Open the editor with `python3 launcher.py` (on Windows use `python launcher.py`). In the local timeline you can step through frames, adjust a cut, or leave a note at a timestamp. Restoring removed footage needs the original video and its cut map. In **Export**, choose the resolution, filename and destination folder.

| Ask for | Skill |
| --- | --- |
| A full 9:16 edit from raw footage | [reel-edit](skills/reel-edit/SKILL.md) |
| A motion graphic for one beat | [reel-motion-kit](skills/reel-motion-kit/SKILL.md) |
| Timeline review, notes and cut recovery | [reel-review](skills/reel-review/SKILL.md) |

[دليل الإعداد بالعربي](docs/setup-ar.md) · [Example reels](https://abdallahkht.github.io/abdallah-reel-studio/)
