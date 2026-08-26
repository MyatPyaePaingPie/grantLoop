# Orchestrator read API — proposal (Pooof, for Aria Agent review)

**Status: PROPOSAL.** Edit freely or counter — the only hard requirement from the dashboard side is: *live mode returns the same JSON shapes as the seed*, so the UI switches between replay and live with a base-URL swap and zero rendering changes.

## Principle

The dashboard never computes domain logic. Determinations, deltas, report figures are all backend facts; the UI renders them. That keeps the demo honest — what's on screen is what the fleet actually produced (Firestore state), not front-end arithmetic.

## Endpoints (orchestrator service, read-only)

| Endpoint | Returns | Seed-shape equivalent |
|---|---|---|
| `GET /api/health` | `{status, model_id, project}` | — |
| `GET /api/state/award` | award diff: obligations with `award_delta`, specific conditions | `notice_of_award.AWARD_DELTAS_TO_SURFACE` + `specific_conditions` |
| `GET /api/state/ledger?limit=50` | transactions with **actual** Sentinel determinations + citations + `causation_id` | `ledger_stream.transactions` (with `determination` replacing `expected_determination`) |
| `GET /api/state/exceptions` | DLQ / exception items: `{txn_ref, attempts, last_error, first_seen}` | none (live-only) |
| `GET /api/state/report/current` | assembled SF-425: line values each carrying `source_txn_ids[]` for click-through, `certified: bool` | `reporting.first_report` + computed lines |

## Notes

- **Citations**: include a top-level `citations_verified: bool` in every response; the UI already gates rendering on it, so the eCFR pass flips one backend flag and every screen updates.
- **Auth**: none for the demo (simulated data, read-only). If we want a token, a single shared header is enough — decide by Day 4, not later.
- **Push vs poll**: dashboard polls (2s) in live mode. SSE/streaming is a nice-to-have; do not spend schedule on it.
- **Ownership**: implementing these is orchestrator-side (your lane). If you'd rather expose raw Firestore reads and have me shape them client-side, say so — but that moves domain logic into the UI, which I'd argue against on the honesty point above.
