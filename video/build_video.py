#!/usr/bin/env python3
"""Assemble the final cut.

Every beat becomes one 1080p segment whose length is exactly its narration, then
the segments concatenate. Because each segment is cut to its own audio rather than
to a stopwatch, editing a line of the script reflows the video automatically and
nothing drifts out of sync.

    python3 video/build_video.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import soundfile as sf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from script import BEATS  # noqa: E402

BUILD = HERE / "build"
SEGMENTS = BUILD / "segments"
OUT = BUILD / "grantloop-demo.mp4"
W, H, FPS = 1920, 1080, 30
BG = "0x101418"          # matches the terminal theme, so pillarboxing is invisible
CROSSFADE = 0.0          # hard cuts: this is a product demo, not a showreel


def run(args: list[str]) -> None:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{' '.join(args[:6])}... failed:\n{result.stderr[-1500:]}")


def vo_path(beat_id: str) -> Path:
    return BUILD / "vo" / f"{beat_id}.wav"


def vo_seconds(beat_id: str) -> float:
    info = sf.info(str(vo_path(beat_id)))
    return info.frames / info.samplerate


def source_for(beat) -> tuple[str, Path]:
    """Where this beat's picture comes from, and the file holding it."""
    if beat.source == "title":
        return "still", BUILD / "cards" / f"{beat.id}.png"
    if beat.source == "image":
        return "still", ROOT / beat.target
    if beat.source == "terminal":
        return "clip", BUILD / "shots" / f"{beat.target}.mp4"
    return "clip", BUILD / "shots" / f"{beat.id}.webm"


#: Scale to fit inside 1080p, pad the remainder. Never crop: cropping a terminal
#: or a dashboard cuts off the very text the beat exists to show.
FIT = (f"scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,"
       f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={BG},setsar=1,fps={FPS},format=yuv420p")

#: Bring the narration to roughly the level a viewer expects. Raw pocket-tts
#: output sits near -25 dB mean, which is audible but quiet enough that people
#: reach for the volume, and judges watching many entries should not have to.
LOUDNESS = "loudnorm=I=-16:TP=-1.5:LRA=11"

#: Pin colour metadata. The browser captures carry bt470bg and the terminal
#: captures do not, which makes ffmpeg reconfigure mid-concat and can shift
#: colour between beats on some players.
COLOR = ["-colorspace", "bt709", "-color_primaries", "bt709",
         "-color_trc", "bt709", "-color_range", "tv"]


def build_segment(beat) -> Path:
    kind, source = source_for(beat)
    if not source.exists():
        raise FileNotFoundError(f"{beat.id}: {source} missing")
    seconds = vo_seconds(beat.id)
    out = SEGMENTS / f"{beat.id}.mp4"

    if kind == "still":
        video_in = ["-loop", "1", "-framerate", str(FPS), "-t", f"{seconds}", "-i", str(source)]
        vf = FIT
    else:
        # Hold the last frame if the clip is shorter than its narration, and cut
        # it if longer. tpad only extends; -t enforces the ceiling.
        video_in = ["-i", str(source)]
        vf = f"{FIT},tpad=stop_mode=clone:stop_duration={seconds}"

    run(["ffmpeg", "-v", "error", "-y", *video_in, "-i", str(vo_path(beat.id)),
         "-filter_complex", f"[0:v]{vf}[v];[1:a]{LOUDNESS}[a]",
         "-map", "[v]", "-map", "[a]",
         "-t", f"{seconds}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         *COLOR,
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         "-movflags", "+faststart", str(out)])
    return out


def main() -> int:
    SEGMENTS.mkdir(parents=True, exist_ok=True)
    print("building segments")
    segments = []
    total = 0.0
    for beat in BEATS:
        seg = build_segment(beat)
        seconds = vo_seconds(beat.id)
        total += seconds
        segments.append(seg)
        print(f"  {beat.id:22} {seconds:5.1f}s  {beat.source}")

    listing = SEGMENTS / "concat.txt"
    listing.write_text("".join(f"file '{s.name}'\n" for s in segments))
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
         "-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(OUT)])

    actual = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(OUT)], capture_output=True, text=True).stdout.strip())
    print(f"\n{OUT}")
    print(f"  {int(actual // 60)}m {actual % 60:04.1f}s ({actual:.0f}s), {len(segments)} beats")
    if actual > 240:
        print(f"  WARNING: {actual - 240:.0f}s over the 4:00 limit")
    else:
        print(f"  {240 - actual:.0f}s under the 4:00 limit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
