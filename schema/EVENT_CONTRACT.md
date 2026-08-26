# GrantLoop Pub/Sub event contract v1.0.0

One topic per state transition. Every agent is a subscriber, never a caller.
No agent invokes another agent directly — the only coupling is this contract.

## Envelope (every message)

```json
{
  "event_id": "uuid-v4",
  "event_type": "award.received",
  "schema_version": "1.0.0",
  "occurred_at": "2026-08-26T14:03:11Z",
  "org_id": "org_riverbend",
  "award_id": "FAIN-93600-2026-0417",
  "idempotency_key": "sha256(org_id|event_type|natural_key)",
  "causation_id": "event_id of the event that caused this one",
  "correlation_id": "constant for the whole award lineage",
  "actor": { "type": "agent|human|system", "id": "ledger_sentinel" },
  "payload": { }
}
```

**Idempotency rule.** Before acting, every agent writes
`processed/{agent}/{idempotency_key}` in Firestore inside the same transaction as
its output. If the doc already exists, the agent acks and no-ops. Pub/Sub is
at-least-once; this makes every handler exactly-once in effect.

**Retry rule.** Handler returns HTTP 5xx -> Pub/Sub redelivers with exponential
backoff (min 10s, max 600s). After 5 attempts the message goes to
`<topic>.dlq` and an `exception.raised` event is emitted so the failure is
*visible in the UI*, not silent. Judges score failure handling — make the DLQ a
panel, not a log line.

## Topics

| # | Topic | Emitted by | Consumed by | Payload core |
|---|---|---|---|---|
| 1 | `document.ingested` | Intake | Application, Covenant | `doc_id, doc_kind, extracted_fields[], confidence[]` |
| 2 | `application.assembled` | Application | UI | `application_id, sections[], budget_lines[]` |
| 3 | `consistency.exception_raised` | Application | UI (human queue) | `exception_id, kind, conflicting_sources[2], proposed_resolutions[]` |
| 4 | `human.resolution_recorded` | UI | Application, Covenant | `exception_id, chosen_resolution, resolved_by, rationale` |
| 5 | `award.received` | Intake | Covenant | `notice_of_award_doc_id, application_id` |
| 6 | `obligation_model.created` | Covenant | Ledger Sentinel, Reporting, UI | full obligation model (see `obligation.schema.json`) |
| 7 | `award.delta_detected` | Covenant | UI | `deltas[] {obligation_id, status, proposed, awarded, downstream_effect}` |
| 8 | `transaction.posted` | Ledger feed (simulated) | Ledger Sentinel | `txn_id, date, vendor, memo, amount, gl_account, attachments[]` |
| 9 | `determination.made` | Ledger Sentinel | Reporting, UI | `txn_id, splits[] {amount, determination, citations[], obligation_id}, confidence, rationale` |
| 10 | `determination.escalated` | Ledger Sentinel | UI (human queue) | `txn_id, reason, question_for_human, options[]` |
| 11 | `reporting.window_opened` | Cloud Scheduler | Reporting | `report_id, form, period_start, period_end, due_date` |
| 12 | `report.drafted` | Reporting | UI | `report_id, sf425_fields{}, line_traceability[], unresolved_exceptions[]` |
| 13 | `report.certified` | UI (human) | Reporting, Renewal | `report_id, certified_by, certified_at, attestation_text` |
| 14 | `report.exported` | Reporting | Renewal | `report_id, export_artifact_uri, submission_mode: "simulated"` |
| 15 | `exception.raised` | any | UI | `source_agent, severity, message, dlq_ref` |

## The two rules that make this "not a chatbot with steps"

1. **No agent reads another agent's private state.** The obligation model is the
   only shared object, and only Covenant writes it. Everyone else appends to
   their own collection keyed by `obligation_id`.
2. **Every write carries its cause.** `causation_id` on every event means the UI
   can render the full lineage `nofo -> application -> award -> transaction ->
   determination -> report line` as a literal graph query, not a story we tell.
   That graph *is* the pitch.

## Human-authority boundary (hard)

Agents may draft, classify, split, cite, schedule and escalate.
Agents may **not**: certify a report (2 CFR 200.415 requires an authorized
official), submit to an agency, or resolve a `requires_human_determination`.
Any UI affordance that looks like an agent doing one of these is a lie we do not tell.
