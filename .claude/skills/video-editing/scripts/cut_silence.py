#!/usr/bin/env python3
"""Jump-cut editing: remove silent pauses / dead air from a talking video.

Uses ffmpeg silencedetect, keeps the spoken parts (with a little padding so
words are not clipped) and stitches them together.
"""
import argparse
import re
import subprocess

from _ff import AUDIO_ENC, VIDEO_ENC, probe, require_ffmpeg, run


def detect_silences(path, noise_db, min_silence):
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", path, "-af",
         f"silencedetect=noise={noise_db}dB:d={min_silence}", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", proc.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", proc.stderr)]
    return list(zip(starts, ends + [None] * (len(starts) - len(ends))))


def keep_segments(silences, duration, pad, min_keep):
    keeps, cursor = [], 0.0
    for start, end in silences:
        seg_end = min(start + pad, duration)
        if seg_end - cursor >= min_keep:
            keeps.append((cursor, seg_end))
        cursor = duration if end is None else max(end - pad, 0.0)
    if duration - cursor >= min_keep:
        keeps.append((cursor, duration))
    return keeps


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--noise", type=float, default=-32,
                   help="silence threshold in dB (default -32; raise to -25 for noisy rooms)")
    p.add_argument("--min-silence", type=float, default=0.45,
                   help="pauses shorter than this (s) are kept (default 0.45)")
    p.add_argument("--pad", type=float, default=0.08,
                   help="seconds of audio kept around each cut (default 0.08)")
    p.add_argument("--min-keep", type=float, default=0.15,
                   help="drop spoken fragments shorter than this (s)")
    p.add_argument("--dry-run", action="store_true", help="only print the segments")
    a = p.parse_args()
    require_ffmpeg()

    info = probe(a.input)
    if not info["has_audio"]:
        raise SystemExit("error: input has no audio track to detect silence on")
    keeps = keep_segments(detect_silences(a.input, a.noise, a.min_silence),
                          info["duration"], a.pad, a.min_keep)
    kept = sum(e - s for s, e in keeps)
    print(f"{len(keeps)} segments, {info['duration']:.1f}s -> {kept:.1f}s "
          f"({info['duration'] - kept:.1f}s removed)")
    for s, e in keeps:
        print(f"  keep {s:8.2f} - {e:8.2f}")
    if a.dry_run or not keeps:
        return

    expr = "+".join(f"between(t,{s:.3f},{e:.3f})" for s, e in keeps)
    script = (f"[0:v]select='{expr}',setpts=N/FRAME_RATE/TB[v];"
              f"[0:a]aselect='{expr}',asetpts=N/SR/TB[a]")
    run(["ffmpeg", "-y", "-i", a.input, "-filter_complex", script,
         "-map", "[v]", "-map", "[a]", *VIDEO_ENC, *AUDIO_ENC, a.output])


if __name__ == "__main__":
    main()
