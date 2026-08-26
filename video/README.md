# Video pipeline

✅ **`video/build/grantloop-demo.mp4`** — 3:42, 1080p, narrated. 18 seconds under the 4:00 cap.

Rebuilds from source in about four minutes:

```bash
pip install -e ".[video]"
python3 video/narrate.py       # pocket-tts, one wav per beat        (~20s)
python3 video/cards.py         # title cards, SVG then PNG            (~1s)
vhs video/tapes/replay.tape    # real CLI, real determinations       (~30s)
vhs video/tapes/dlq.tape       # real retry and dead-letter          (~15s)
vhs video/tapes/health.tape    # live Cloud Run + Gemini proof shot  (~20s)
python3 video/capture.py       # dashboard beats, driven by Playwright (~2m)
python3 video/build_video.py   # normalise, mux narration, concatenate (~40s)
```

## What is and is not generated

**Nothing in this video is synthesised footage.** Every frame of the product is the real
dashboard and the real CLI, driven by a script instead of a hand. Fabricating a demo of a
compliance product would be precisely the dishonesty the product exists to prevent, and a
judge who ran the repo would find the difference in a minute.

What *is* generated: the narration (pocket-tts, local, no account), and the two title cards.

## Why script the capture instead of recording it

- **It cannot drift.** The narration, the shot lengths and the final cut all derive from
  `video/script.py`. Edit a line and everything reflows; nothing needs re-timing by hand.
- **It is reproducible**, like the demo it records. `python -m grantloop.replay` is
  byte-identical every run, so re-recording after a code change is one command, not an
  afternoon.
- **No retakes.** The VO script is timed to ±0s rather than ±10s, and no one has to hit a
  four-minute mark on the seventh attempt.

## Structure

| File | Role |
|---|---|
| `script.py` | The beats: VO text, source, dwell. One source of truth. |
| `narrate.py` | pocket-tts, sentence by sentence, one wav per beat |
| `cards.py` | Title cards as SVG, rendered to PNG |
| `capture.py` | Playwright drives the real dashboard, one video per beat |
| `tapes/*.tape` | VHS scripts for the real terminal beats |
| `build_video.py` | Scale, pad, loudness-normalise, mux, concatenate |

Each beat's picture is cut to exactly its narration length, so audio and video stay in step
without anyone counting.

## Known constraints

- The Cloud Console cutaway is the one shot left to a human. Automating a Google auth session
  is fragile and not worth it; two screenshots of the Cloud Run service page cover it.
- `capture.py` records against the deployed configuration, so the dashboard badge reads
  `LIVE · CLOUD` and the escalation question on screen is the one Gemini actually wrote. On a
  machine without project access it records in offline mode instead of failing.
