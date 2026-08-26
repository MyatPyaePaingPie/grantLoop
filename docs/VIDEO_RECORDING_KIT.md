# Demo video — recording kit (Pooof)

Everything needed to record the ~4:00 video in one sitting. VO is word-for-word (≈580 words ≈ 3:50 at normal pace). Screen actions are listed per beat. Replay mode records TODAY with zero cloud dependency; the two cloud cutaways get spliced in once the Cloud Run URL exists.

## Setup (5 min)
1. Terminal at repo root, font large (18pt+), dark theme.
2. `python3 -m grantloop.api` → browser at `http://127.0.0.1:8080/dashboard/` (mode badge should read LIVE · OFFLINE).
3. Recorder: OBS or Windows Game Bar (Win+Alt+R), 1080p minimum, system audio off, mic on.
4. Second terminal ready for the replay commands.
5. Do a silent dry run through the click path once before recording.

---

## Beat 0 — Cold open (0:00–0:20)
**Screen:** black slide or plain doc with one line: *"A 2-person nonprofit wins a $250K federal grant. Now the hard part starts."*

**VO:** "A two-person nonprofit wins a two hundred fifty thousand dollar federal grant. With it, they inherit 2 CFR Part 200: an allowability test on every expense, an SF-425 on a deadline, and a high-risk designation waiting if they slip. Grant-writing AI abandons you at the moment of victory. Compliance tools start from scratch after it. Nobody closes the loop. GrantLoop is the loop."

## Beat 1 — Application catches its own inconsistency (0:20–0:45)
**Screen:** repo view or dashboard; show the application inconsistency (narrative 120 youth @ 1:10 vs 2 mentors @ 0.5 FTE) — from the seed panel or a brief JSON view.

**VO:** "It starts before the award. The application agent reads what the narrative promises — a hundred twenty youth at a one-to-ten ratio — against what the budget funds: two mentors at half time. It flags the contradiction and offers three concrete resolutions. The system reads what you promised, not just what you wrote."

## Beat 2 — Award handoff, THE MONEY SHOT (0:45–1:25)
**Screen:** dashboard → Award Handoff tab. Point at the callout, then the Covenant findings panel (three critical findings).

**VO:** "Award day. Covenant diffs the Notice of Award against the application — and derives three findings nobody scripted. Participant support: cut forty percent. The target it paid for: accepted unchanged at a hundred twenty youth. They cut the money and kept the promise. Then it finds the same pattern again on outreach — a rule firing, not a special case. And a third finding: this award's stated total is twenty-two thousand dollars less than its own budget lines. The award doesn't add up — and Covenant caught that too, because it reconciles instead of trusting the headline number."

## Beat 3 — Ledger Sentinel (1:25–2:25)
**Screen:** second terminal: `python3 -m grantloop.replay --pace 1.5`, then dashboard → Ledger Sentinel tab. Hover the seven badges. Then `python3 -m grantloop.replay --dlq TXN-004` and show the Exceptions/DLQ tab.

**VO:** "Now money starts moving. Seven transactions, seven different determinations — every one citing the regulation it applied. A catering invoice isn't rejected; it's split — four hundred twelve dollars of wine carved out under 200.423, the rest routed for review. The laptops are the interesting one: the regulation actually permits them. The award's own condition doesn't. 'The regulation permits this — your award does not.' The Sentinel doesn't ask a model whether a cost is allowable. It's a deterministic rule engine over eCFR-verified citations — reproducible on camera, defensible to a judge. The model's job is drafting the human-facing question when it escalates. And when a message poisons, it retries five times and lands here — on screen, loudly. Unmatched costs escalate to a human. Silence is never approval."

## Beat 4 — SF-425 (2:25–3:00)
**Screen:** dashboard → SF-425 tab. Point at split lines reconciling, source transaction IDs, then the disabled certify button and statutory text.

**VO:** "Reporting day. The SF-425 assembles itself from actual ledger state. The catering split survives all the way through — two lines, reconciling to the cent. Every figure traces to its transactions. And then it stops. 2 CFR 200.415 requires an official who can legally bind the recipient — so the system assembles, and a human certifies. That button is disabled by construction."

## Beat 5 — The loop closes (3:00–3:20)
**Screen:** back to Award tab or a renewal slide.

**VO:** "Next application, the loop closes: verified performance and a machine-checked compliance record carry forward as evidence. Most grant software remembers the documents. GrantLoop remembers the promises."

## Beat 6 — Architecture + cloud proof (3:20–4:00)
**Screen:** `docs/architecture.png` full-screen, then [AFTER DEPLOY] GCP console: Cloud Run services page, then the deployed /api/health response.

**VO:** "Under the hood: two Cloud Run services, deliberately not five. Four human-paced agents share an orchestrator; the Sentinel deploys alone because it's the only high-volume, retry-heavy component — that's real failure isolation, not diagram decoration. Agents never call each other: every transition is an event with a causation ID, every handler idempotent, failures land in a dead-letter queue you just saw on screen. ADK agents plan and explain; deterministic engines decide and cite. Gemini 3.5 drafts the questions only humans can answer. Running on Google Cloud — here's the live service. GrantLoop: from promise to proof."

---

## Splice list — DEPLOY IS LIVE, record these now
Service: `https://grantloop-orchestrator-361788129265.us-central1.run.app` (identity-token gated — fine per rules: app need not be public).
- [ ] Console cutaway: Cloud Run services page in project active-future-506706-s7 showing the service green.
- [ ] Terminal shot: `curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" https://grantloop-orchestrator-361788129265.us-central1.run.app/api/health` → shows `"mode":"cloud"`, `"model_id":"gemini-3.5-flash"`, `"location":"global"`, model lane with gemini. This single shot is the GCP + Gemini proof.
- [ ] Beat 3 model moment: the deployed Gemini-drafted escalation question ("Is the primary purpose of the Community Chamber Alliance to engage in lobbying?") — visible on the deployed dashboard's Sentinel tab.
- [ ] Optional: record beat 3 against the deployed dashboard (badge LIVE · CLOUD) instead of local.

## Rules check before upload
- Backend visibly on Google Cloud ✔ (beat 6 cutaways)
- ~4 minutes ✔ (VO measured ≈3:50)
- Upload to YouTube/Vimeo → paste link into Devpost "Project details".
