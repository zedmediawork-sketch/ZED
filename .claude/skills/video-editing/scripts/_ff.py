"""Shared ffmpeg helpers for the video-editing skill scripts."""
import json
import shutil
import subprocess
import sys


def require_ffmpeg():
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"error: {tool} not found on PATH (install ffmpeg)")


def run(cmd):
    print("+ " + " ".join(cmd), file=sys.stderr)
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        sys.exit(f"error: command failed with exit code {proc.returncode}")


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_streams", "-show_format", path],
        capture_output=True, text=True, check=True,
    ).stdout
    data = json.loads(out)
    video = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    audio = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    return {
        "duration": float(data["format"].get("duration", 0)),
        "width": int(video["width"]) if video else None,
        "height": int(video["height"]) if video else None,
        "has_audio": audio is not None,
    }


# Instagram/TikTok/Shorts friendly encode settings.
VIDEO_ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
AUDIO_ENC = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
