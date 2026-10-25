#!/usr/bin/env python3
"""One-command Reel edit: raw clip in, ready-to-post vertical video out.

Pipeline (each step optional):
  1. cut_silence      jump cuts, remove dead air       (--no-cut to skip)
  2. reframe_vertical 1080x1920                        (--reframe crop|blur|none)
  3. color_grade      preset look                      (--grade PRESET)
  4. punch_zoom       auto punch-ins                   (--punch-every N)
  5. add_captions     word-by-word captions            (--srt / --transcribe)
  6. add_music        ducked background music          (--music FILE)
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def step(script, *args):
    cmd = [sys.executable, os.path.join(HERE, script), *map(str, args)]
    print(f"\n== {script} ==", file=sys.stderr)
    if subprocess.run(cmd).returncode != 0:
        sys.exit(f"error: {script} failed")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--no-cut", action="store_true")
    p.add_argument("--silence-db", type=float, default=-32)
    p.add_argument("--reframe", choices=["crop", "blur", "none"], default="crop")
    p.add_argument("--grade", default=None, help="punchy|warm|cinematic|moody|bw")
    p.add_argument("--punch-every", type=float, default=0)
    p.add_argument("--srt")
    p.add_argument("--transcribe", action="store_true")
    p.add_argument("--language", default=None)
    p.add_argument("--music")
    p.add_argument("--music-volume", type=float, default=0.35)
    a = p.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        cur, n = a.input, 0

        def nxt():
            nonlocal n
            n += 1
            return os.path.join(tmp, f"step{n}.mp4")

        if not a.no_cut:
            out = nxt(); step("cut_silence.py", cur, out, "--noise", a.silence_db); cur = out
        if a.reframe != "none":
            out = nxt(); step("reframe_vertical.py", cur, out, "--mode", a.reframe); cur = out
        if a.grade:
            out = nxt(); step("color_grade.py", cur, out, "--preset", a.grade); cur = out
        if a.punch_every > 0:
            out = nxt(); step("punch_zoom.py", cur, out, "--every", a.punch_every); cur = out
        if a.srt or a.transcribe:
            if a.srt and not a.no_cut:
                print("warning: SRT timings refer to the uncut clip; use --no-cut or "
                      "--transcribe so captions stay in sync", file=sys.stderr)
            src = ["--srt", a.srt] if a.srt else ["--transcribe"]
            if a.language:
                src += ["--language", a.language]
            out = nxt(); step("add_captions.py", cur, out, *src); cur = out
        if a.music:
            out = nxt()
            step("add_music.py", cur, a.music, out, "--music-volume", a.music_volume)
            cur = out
        shutil.copyfile(cur, a.output)
    print(f"\ndone -> {a.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
