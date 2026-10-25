#!/usr/bin/env python3
"""Reframe any video to vertical 9:16 (1080x1920) for Reels/Shorts/TikTok.

Modes:
  crop  - center-crop to fill the frame (default; best for talking heads)
  blur  - fit the whole frame and fill the bars with a blurred copy
"""
import argparse

from _ff import AUDIO_ENC, VIDEO_ENC, probe, require_ffmpeg, run


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--mode", choices=["crop", "blur"], default="crop")
    p.add_argument("--width", type=int, default=1080)
    p.add_argument("--height", type=int, default=1920)
    p.add_argument("--x-offset", type=float, default=0.5,
                   help="horizontal crop position 0..1 (crop mode), 0.5 = center")
    p.add_argument("--fps", type=int, default=30)
    a = p.parse_args()
    require_ffmpeg()

    W, H = a.width, a.height
    if a.mode == "crop":
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
              f"crop={W}:{H}:(iw-{W})*{a.x_offset}:(ih-{H})/2,setsar=1,fps={a.fps}")
        filt = ["-vf", vf]
    else:
        fc = (f"[0:v]split[bg][fg];"
              f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"boxblur=30:5,eq=brightness=-0.08[bgb];"
              f"[fg]scale={W}:{H}:force_original_aspect_ratio=decrease[fgs];"
              f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={a.fps}[v]")
        filt = ["-filter_complex", fc, "-map", "[v]", "-map", "0:a?"]

    audio = AUDIO_ENC if probe(a.input)["has_audio"] else ["-an"]
    run(["ffmpeg", "-y", "-i", a.input, *filt, *VIDEO_ENC, *audio, a.output])


if __name__ == "__main__":
    main()
