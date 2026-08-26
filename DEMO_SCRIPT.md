# GrantLoop — Demo Video Script (v1, aligned to PLANS/GRANTLOOP_PLAN.md @ b35d4c1)

**Target:** ~4:00 min. Judging: 40% innovation/operational utility, 30% architecture, 30% demo + production readiness. Video MUST show the backend running on Google Cloud.

**Owner:** Pooof (Paing's machine). **Status:** v1.1 — beats and scenario figures locked to the plan doc. Citation gate CLEARED: eCFR pass done 2026-08-26 (docs/ECFR_VERIFICATION_2026-08-26.md), rules at v1.0.0, citations now render on screen. Laptop beat leads with award term SC-2, CFR as context (per verified TXN-005 note).

**Everything model-facing sits behind one `MODEL_ID` env var** (Gemini 3.x blocker: swap is a one-liner when cleared).

---

## Beat sheet (mirrors plan doc §Demo flow, timed for 4:00)

### 0:00–0:20 — Cold open: the pain
- On screen: "A 2-person nonprofit wins a $250K federal grant. Now the hard part starts."
- VO: 2 CFR 200, SF-425 deadlines, high-risk designation for late reports, no grants manager. One botched award ends the org.
- No product on screen yet.

### 0:20–0:45 — Beat 1: Application catches its own inconsistency
- Application agent flags: narrative promises **120 youth at a 1:10 ratio**, but the budget funds **2 mentors at 0.5 FTE**. Routes to a human with three concrete resolutions.
- VO point: the system reads what you *promised*, not just what you wrote.

### 0:45–1:25 — Beat 2: Award handoff — THE MONEY SHOT (now DERIVED, not scripted)
- Upload the Notice of Award. Covenant diffs awarded budget lines vs application and independently finds **three critical findings** (all on the Covenant findings panel, straight from `/api/state/award`):
  1. **BL-04 cut 40% ($30k → $18k) while PP-1 accepted unchanged at 120 youth.**
  2. **BL-07 cut 33% ($12k → $8k) while PP-3 unchanged at 4 convenings** — same pattern, second instance: a *rule firing*, not a special case.
  3. **`award_total_mismatch`: the NOA states $212,000 federal share, but its own budget lines sum to $234,000 — a $22,000 unexplained gap.** The agent reconciles instead of trusting the headline number; drawing funds against an award that disagrees with itself is how recipients end up with questioned costs they never chose.
- VO: "They cut the money. They kept the promise." Then: "And the award doesn't even add up — Covenant caught that too."
- Equipment condition attached (BL-08) surfaces here; participant-support cut names 200.308(f)(5) in its downstream effect.
- Then, unprompted: obligation model, evidence plan, quarterly reporting calendar build themselves. Nobody clicks through steps.

### 1:25–2:25 — Beat 3: Ledger Sentinel — seven transactions, seven determinations
Live stream over Pub/Sub (replay CLI drives the deterministic seed; doubles as record-day fallback). Each determination value fires exactly once:

| Transaction | Determination |
|---|---|
| Alcohol in event catering → split | `presumptively_unallowable` |
| Rent → flagged for allocation | `requires_allocation` |
| Laptops → below the org's own $5,000 capitalization threshold AND the CFR's $10,000 — supplies under 200.453(c), the regulation permits them; **the block is award condition SC-2 and only SC-2** | `conflicts_with_award_terms` |
| Pre-award registration → caught by date | `requires_prior_approval` |
| Chamber dues → escalated, human-only call | `requires_human_determination` |
| (from seed) receipt-less expense | `missing_documentation` |
| (from seed) ordinary program cost sails through | `presumptively_allowable` |

- Show the DLQ/exception panel once: failed handler retries then lands visibly. Failure handling as a feature. (Replay CLI: `--dlq TXN-004` forces this on camera.)
- **Say out loud (VO, strength not limitation):** "The Sentinel doesn't ask a model whether a cost is allowable. It's a deterministic rule engine over verified citations — reproducible on camera, defensible to a judge. The model's only job is drafting the human-facing question on an escalation."
- **Second VO line:** "Unmatched costs escalate to a human. Silence is never approval." (One line of code; the difference between a compliance tool and a liability.)
- NO CFR number renders unless verified (Aria Agent's pass — done, rules v1.0.0).

### 2:25–3:00 — Beat 4: Reporting on the deadline event
- SF-425 assembled from real ledger state; **every figure clickable to its transaction**; unresolved exceptions attached.
- Then it **stops and waits for the Executive Director to certify**. Export labelled *simulated*.
- VO: "The report isn't written from memory. It's computed from the same object that made the promises."

### 3:00–3:25 — Beat 5: Renewal — the loop closes
- Next application pulls verified performance + clean-compliance evidence forward.
- Thesis line: "The application and the award are the same living object."

### 3:25–4:00 — Architecture flyover + production evidence
- **Two Cloud Run services** (orchestrator + ledger-sentinel), Pub/Sub topics per EVENT_CONTRACT, Firestore, Gemini via ADK.
- Say the two-service reasoning OUT LOUD (defended call from plan §Architecture): Sentinel is the only push-subscription, high-volume, retry/DLQ-heavy component; splitting it demonstrates retry isolation honestly. No agent calls another agent; every transition is an event with causation_id; every handler idempotent.
- GCP console cutaways: Cloud Run services live, Pub/Sub topics, Firestore docs.

---

## Dependencies
- [ ] MODEL_ID blocker — Gemini 3.5+ on the GCP project (Paing, Model Garden). Fix path in docs/GCP_VALIDATION_2026-08-26.md.
- [ ] eCFR verification pass (Aria Agent) gates all on-screen citations.
- [ ] Dashboard/UI (Pooof) — screens implied by beats: obligation graph, award-diff view, sentinel feed w/ 7-value legend, DLQ panel, SF-425 draft w/ click-through, certify gate, renewal evidence view.
- [ ] Devpost submission text (Pooof) — draft after dashboard screenshots exist.

## Recording notes
- Deterministic replay ⇒ identical takes. Record backend visibly on Google Cloud (console cutaways, not localhost).
- Script every VO line; zero improv on CFR numbers or dollar figures — all figures come from seed/riverbend_scenario.json and the plan doc.
