#!/usr/bin/env python3
"""Quick color grades for social video, or apply your own .cube LUT.

Presets: punchy, warm, cinematic (teal & orange), moody, bw
"""
import argparse

from _ff import VIDEO_ENC, probe, require_ffmpeg, run

PRESETS = {
    "punchy": "eq=contrast=1.12:saturation=1.3:brightness=0.02,unsharp=5:5:0.6",
    "warm": "colorbalance=rs=0.06:gs=0.02:bs=-0.06:rm=0.05:bm=-0.04,eq=saturation=1.15:contrast=1.05",
    "cinematic": ("colorbalance=rs=-0.08:gs=-0.02:bs=0.10:rh=0.10:gh=0.03:bh=-0.08,"
                  "eq=contrast=1.1:saturation=1.1,vignette=PI/5"),
    "moody": "eq=contrast=1.15:saturation=0.8:brightness=-0.04:gamma=0.95,vignette=PI/4",
    "bw": "hue=s=0,eq=contrast=1.2",
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("output")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--preset", choices=sorted(PRESETS))
    g.add_argument("--lut", help="path to a .cube LUT file")
    a = p.parse_args()
    require_ffmpeg()

    vf = PRESETS[a.preset] if a.preset else f"lut3d='{a.lut}'"
    audio = ["-c:a", "copy"] if probe(a.input)["has_audio"] else ["-an"]
    run(["ffmpeg", "-y", "-i", a.input, "-vf", vf, *VIDEO_ENC, *audio, a.output])


if __name__ == "__main__":
    main()
