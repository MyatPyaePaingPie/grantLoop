#!/usr/bin/env python3
"""Generate the voiceover with pocket-tts, one wav per beat.

Runs entirely locally: no account, no API key, no per-minute cost. Roughly ten
times faster than realtime on this machine, so the whole narration regenerates in
under a minute whenever the script changes.

Long beats are synthesised sentence by sentence and concatenated. The model
degrades on very long single utterances, and per-sentence generation also gives
natural pauses at the joins, which a single pass does not.

    python3 video/narrate.py                 # all beats
    python3 video/narrate.py 02-award-handoff # one beat
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from script import BEATS  # noqa: E402

OUT = Path(__file__).resolve().parent / "build" / "vo"
VOICE = "vera"
LANGUAGE = "english_2026-04"

#: Silence inserted between sentences, and after the last one. Without it the
#: joins sound clipped and the picture has no room to land.
GAP_S = 0.28
TAIL_S = 0.45


def sentences(text: str) -> list[str]:
    """Split on sentence ends, keeping decimals and section numbers intact."""
    protected = re.sub(r"(\d)\.(\d)", r"\1<DOT>\2", text)
    parts = re.split(r"(?<=[.!?])\s+", protected)
    return [p.replace("<DOT>", ".").strip() for p in parts if p.strip()]


def main(only: str | None = None) -> int:
    from pocket_tts import TTSModel
    from pocket_tts.utils.utils import get_predefined_voice

    OUT.mkdir(parents=True, exist_ok=True)
    print(f"loading pocket-tts (voice: {VOICE})...")
    model = TTSModel.load_model()
    state = model.get_state_for_audio_prompt(get_predefined_voice(LANGUAGE, VOICE))
    sr = model.sample_rate
    gap = np.zeros(int(GAP_S * sr), dtype=np.float32)
    tail = np.zeros(int(TAIL_S * sr), dtype=np.float32)

    total = 0.0
    for beat in BEATS:
        if only and beat.id != only:
            continue
        started = time.time()
        chunks: list[np.ndarray] = []
        for sentence in sentences(beat.vo):
            audio = model.generate_audio(state, sentence, frames_after_eos=2, copy_state=True)
            chunks.append(np.asarray(audio).squeeze().astype(np.float32))
            chunks.append(gap)
        track = np.concatenate(chunks[:-1] + [tail]) if chunks else tail
        path = OUT / f"{beat.id}.wav"
        sf.write(path, track, sr)
        seconds = len(track) / sr
        total += seconds
        print(f"  {beat.id:22} {seconds:5.1f}s  ({time.time() - started:4.1f}s to generate)")

    if not only:
        # int(), not :.0f. Rounding the minutes reported 222s as "4m 42s",
        # which reads as over the limit when it is eighteen seconds under it.
        print(f"\ntotal narration: {int(total // 60)}m {total % 60:04.1f}s ({total:.0f}s)")
        if total > 240:
            print(f"  WARNING: over the 4:00 limit by {total - 240:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else None))
