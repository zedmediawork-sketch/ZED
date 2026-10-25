#!/usr/bin/env python3
"""Add background music that automatically ducks under the voice.

The music is looped to the video length, lowered whenever someone speaks
(sidechain compression), faded out at the end, and the final mix is
loudness-normalized to -14 LUFS (Instagram/YouTube target).
"""
import argparse

from _ff import AUDIO_ENC, probe, require_ffmpeg, run


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("music")
    p.add_argument("output")
    p.add_argument("--music-volume", type=float, default=0.35)
    p.add_argument("--music-start", type=float, default=0, help="skip into the track (s)")
    p.add_argument("--fade-out", type=float, default=1.5)
    p.add_argument("--no-duck", action="store_true")
    a = p.parse_args()
    require_ffmpeg()

    info = probe(a.input)
    dur = info["duration"]
    fade_st = max(dur - a.fade_out, 0)
    music = (f"[1:a]atrim=start={a.music_start},asetpts=PTS-STARTPTS,"
             f"volume={a.music_volume},atrim=end={dur:.3f},"
             f"afade=t=out:st={fade_st:.3f}:d={a.fade_out}[m]")
    if not info["has_audio"]:
        fc = f"{music};[m]loudnorm=I=-14:TP=-1.5:LRA=11[out]"
    elif a.no_duck:
        fc = (f"{music};[0:a][m]amix=inputs=2:duration=first:normalize=0,"
              f"loudnorm=I=-14:TP=-1.5:LRA=11[out]")
    else:
        fc = (f"{music};[0:a]asplit[voice][sc];"
              f"[m][sc]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[duck];"
              f"[voice][duck]amix=inputs=2:duration=first:normalize=0,"
              f"loudnorm=I=-14:TP=-1.5:LRA=11[out]")
    run(["ffmpeg", "-y", "-i", a.input, "-stream_loop", "-1", "-i", a.music,
         "-filter_complex", fc, "-map", "0:v", "-map", "[out]",
         "-c:v", "copy", *AUDIO_ENC, "-shortest", a.output])


if __name__ == "__main__":
    main()
