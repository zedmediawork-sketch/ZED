#!/usr/bin/env python3
"""Punch-in zooms: the quick zoom-in emphasis used on Reels/Shorts.

  --at 2.5-4 7-8.2      zoom during these time ranges (seconds)
  --every 3             or auto-alternate zoom in/out every N seconds
"""
import argparse

from _ff import VIDEO_ENC, probe, require_ffmpeg, run


def parse_range(s):
    start, end = s.split("-")
    return float(start), float(end)


def zoom_expr(ranges, zoom, ease):
    if not ranges:
        return "1"
    terms = []
    for s, e in ranges:
        if ease > 0:
            ramp = f"min(1,(t-{s})/{ease})"
            terms.append(f"between(t,{s},{e})*{zoom - 1}*{ramp}")
        else:
            terms.append(f"between(t,{s},{e})*{zoom - 1}")
    return "1+" + "+".join(terms)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--at", nargs="+", type=parse_range, default=[], metavar="START-END")
    p.add_argument("--every", type=float, default=0,
                   help="auto punch: zoom every other N-second block")
    p.add_argument("--zoom", type=float, default=1.18, help="zoom factor (default 1.18)")
    p.add_argument("--ease", type=float, default=0.0,
                   help="seconds to ease into the zoom (0 = hard punch)")
    p.add_argument("--y-focus", type=float, default=0.4,
                   help="vertical zoom center 0..1 (0.4 keeps faces in frame)")
    a = p.parse_args()
    require_ffmpeg()

    info = probe(a.input)
    ranges = list(a.at)
    if a.every > 0:
        t = a.every
        while t < info["duration"]:
            ranges.append((round(t, 3), round(min(t + a.every, info["duration"]), 3)))
            t += 2 * a.every
    if not ranges:
        raise SystemExit("error: give --at ranges or --every N")

    W, H = info["width"], info["height"]
    z = zoom_expr(ranges, a.zoom, a.ease)
    vf = (f"scale=w='trunc(iw*({z})/2)*2':h='trunc(ih*({z})/2)*2':eval=frame,"
          f"crop={W}:{H}:(iw-{W})/2:(ih-{H})*{a.y_focus},setsar=1")
    audio = ["-c:a", "copy"] if info["has_audio"] else ["-an"]
    run(["ffmpeg", "-y", "-i", a.input, "-vf", vf, *VIDEO_ENC, *audio, a.output])


if __name__ == "__main__":
    main()
