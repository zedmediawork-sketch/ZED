#!/usr/bin/env python3
"""Burn bold, word-by-word "reel style" captions onto a video.

Caption source (pick one):
  --srt FILE        an existing .srt (word timing is interpolated per cue)
  --words FILE      JSON list of {"word": str, "start": s, "end": s}
  --transcribe      auto-transcribe with faster-whisper (pip install faster-whisper)

Each caption shows a few words at once; the word being spoken is highlighted
and slightly enlarged, like CapCut / Submagic style captions.
"""
import argparse
import json
import os
import re
import tempfile

from _ff import VIDEO_ENC, probe, require_ffmpeg, run


def srt_time(ts):
    h, m, rest = ts.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def words_from_srt(path):
    text = open(path, encoding="utf-8-sig").read()
    words = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.strip().splitlines()
        idx = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if idx is None:
            continue
        start, end = (srt_time(x.strip().split()[0]) for x in lines[idx].split("-->"))
        cue_words = " ".join(lines[idx + 1:]).split()
        total = sum(len(w) for w in cue_words) or 1
        t = start
        for w in cue_words:
            dur = (end - start) * len(w) / total
            words.append({"word": w, "start": t, "end": t + dur})
            t += dur
    return words


def words_from_whisper(path, model_size, language):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("error: --transcribe needs faster-whisper: pip install faster-whisper")
    model = WhisperModel(model_size, device="auto", compute_type="auto")
    segments, _ = model.transcribe(path, word_timestamps=True, language=language)
    return [{"word": w.word.strip(), "start": w.start, "end": w.end}
            for seg in segments for w in seg.words if w.word.strip()]


def chunk_words(words, max_words):
    chunks, cur = [], []
    for w in words:
        if cur and w["start"] - cur[-1]["end"] > 0.15:
            chunks.append(cur)
            cur = []
        cur.append(w)
        if len(cur) >= max_words or re.search(r"[.!?,;:]$", w["word"]):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def ass_time(t):
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def ass_color(hex_rgb):
    h = hex_rgb.lstrip("#")
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def ass_escape(s):
    return s.replace("\\", "\\\\").replace("{", "(").replace("}", ")")


def build_ass(words, a, width, height):
    size = a.font_size or round(height * 0.045)
    margin_v = round(height * a.position)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Reel,{a.font},{size},{ass_color(a.color)},&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,1,0,1,{max(2, size // 12)},{max(1, size // 24)},2,{round(width * 0.08)},{round(width * 0.08)},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    hl = ass_color(a.highlight)
    events = []
    for chunk in chunk_words(words, a.max_words):
        texts = [ass_escape(w["word"].upper() if a.uppercase else w["word"]) for w in chunk]
        chunk_end = chunk[-1]["end"]
        if a.no_highlight:
            events.append((chunk[0]["start"], chunk_end, " ".join(texts)))
            continue
        for i, w in enumerate(chunk):
            end = chunk[i + 1]["start"] if i + 1 < len(chunk) else chunk_end
            parts = [
                f"{{\\c{hl}\\fscx112\\fscy112}}{t}{{\\r}}" if j == i else t
                for j, t in enumerate(texts)
            ]
            events.append((w["start"], max(end, w["start"] + 0.05), " ".join(parts)))
    lines = [f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Reel,,0,0,0,,{t}"
             for s, e, t in events]
    return header + "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input")
    p.add_argument("output", help="output video (or .ass file with --ass-only)")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--srt")
    src.add_argument("--words")
    src.add_argument("--transcribe", action="store_true")
    p.add_argument("--model", default="small", help="whisper model size (default small)")
    p.add_argument("--language", default=None, help="e.g. hi, en (default auto-detect)")
    p.add_argument("--max-words", type=int, default=3, help="words per caption (default 3)")
    p.add_argument("--font", default="DejaVu Sans")
    p.add_argument("--font-size", type=int, default=0, help="default 4.5%% of video height")
    p.add_argument("--color", default="#FFFFFF")
    p.add_argument("--highlight", default="#FFE600", help="active word color")
    p.add_argument("--position", type=float, default=0.28,
                   help="distance from bottom as a fraction of height (default 0.28)")
    p.add_argument("--no-uppercase", dest="uppercase", action="store_false")
    p.add_argument("--no-highlight", action="store_true")
    p.add_argument("--ass-only", action="store_true", help="write the .ass file and stop")
    a = p.parse_args()
    require_ffmpeg()

    info = probe(a.input)
    if a.srt:
        words = words_from_srt(a.srt)
    elif a.words:
        words = json.load(open(a.words, encoding="utf-8"))
    else:
        words = words_from_whisper(a.input, a.model, a.language)
    if not words:
        raise SystemExit("error: no caption words found")

    ass = build_ass(words, a, info["width"], info["height"])
    if a.ass_only:
        open(a.output, "w", encoding="utf-8").write(ass)
        print(f"wrote {a.output}")
        return

    with tempfile.TemporaryDirectory() as tmp:
        ass_path = os.path.join(tmp, "captions.ass")
        open(ass_path, "w", encoding="utf-8").write(ass)
        audio = ["-c:a", "copy"] if info["has_audio"] else ["-an"]
        run(["ffmpeg", "-y", "-i", a.input, "-vf", f"ass={ass_path}",
             *VIDEO_ENC, *audio, a.output])


if __name__ == "__main__":
    main()
