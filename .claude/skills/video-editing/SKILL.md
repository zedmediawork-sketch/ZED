---
name: video-editing
description: Edit raw clips into Instagram Reels / YouTube Shorts / TikTok style videos with ffmpeg — vertical 9:16 reframe, jump cuts (silence removal), bold word-by-word highlighted captions, punch-in zooms, color grades, and background music that ducks under the voice. Use when the user asks to edit a video, make a reel/short, add captions/subtitles, remove pauses, zoom in, color grade, or add music.
---

# Video editing (Reels / Shorts style)

All tools are Python 3 scripts in `scripts/` that only need `ffmpeg` + `ffprobe`
(auto-transcription optionally needs `pip install faster-whisper`).
Run them with `python3 .claude/skills/video-editing/scripts/<script>.py --help`.

## One command

```bash
python3 .claude/skills/video-editing/scripts/reel.py raw.mp4 reel.mp4 \
  --grade punchy --punch-every 3 --transcribe --language hi --music bgm.mp3
```

Order: cut silence → reframe 9:16 → grade → punch zooms → captions → music.
Captions come *after* cutting, so use `--transcribe` (or `--no-cut` with an SRT
made for the raw clip) to keep them in sync.

## Individual tools

| Script | What it does | Key options |
|---|---|---|
| `cut_silence.py in out` | Jump cuts: removes pauses/dead air | `--noise -32` (dB, raise to -25 in noisy rooms), `--min-silence 0.45`, `--pad 0.08`, `--dry-run` |
| `reframe_vertical.py in out` | 1080x1920 vertical | `--mode crop` (fill) or `blur` (whole frame + blurred bars), `--x-offset 0..1` |
| `add_captions.py in out` | Bold captions, active word highlighted + enlarged | `--srt f` / `--words f.json` / `--transcribe`, `--max-words 3`, `--highlight #FFE600`, `--font`, `--position 0.28`, `--ass-only` |
| `punch_zoom.py in out` | Punch-in zoom for emphasis | `--at 2-3.5 6-7`, `--every 3`, `--zoom 1.18`, `--ease 0.1`, `--y-focus 0.4` |
| `color_grade.py in out` | Look presets or a LUT | `--preset punchy|warm|cinematic|moody|bw`, `--lut file.cube` |
| `add_music.py in music out` | Looped music, sidechain-ducked under voice, fade out, -14 LUFS | `--music-volume 0.35`, `--music-start`, `--no-duck` |

## Workflow tips

1. `ffprobe` the input first (resolution, duration, audio present?).
2. Run `cut_silence.py --dry-run` to tune `--noise`/`--min-silence` before cutting.
3. Check a frame after captions/zoom:
   `ffmpeg -ss 2 -i out.mp4 -frames:v 1 frame.png` and look at it.
4. Keep intermediate files; each step re-encodes with x264 CRF 20 so quality
   loss across the chain is minimal.
5. For Hindi/Hinglish captions in Devanagari, pass a font that has the glyphs
   (e.g. `--font "Noto Sans Devanagari"`); for Roman Hinglish the default works.
