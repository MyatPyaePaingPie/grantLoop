# Devpost submission — live copy

**Status: ON DEVPOST.** Project overview and Project details are filled and saved at
https://devpost.com/software/grantloop (draft, 2/5 steps). This file is the source of truth for
that copy: edit here, then mirror to Devpost.

## Project name

GrantLoop

## Elevator pitch

Most grant software remembers the documents. GrantLoop remembers the promises. Agents carry every
budget commitment from application through award and spending to an audit-ready SF-425.

## Built with (tags entered)

python · gemini · vertex-ai · google-cloud-run · google-cloud-pubsub · firestore · google-adk ·
fastapi · docker · javascript · ecfr-api

## Try it out

https://github.com/MyatPyaePaingPie/grantLoop

---

## Project story (as saved)

## Inspiration

A two-person nonprofit wins a $250,000 federal award and inherits 2 CFR Part 200 with it: an allowability test on every expense, an SF-425 on a deadline, and specific conditions that can follow them into the next award cycle.

The tools they can buy split cleanly in half. Grant-writing AI abandons them at the moment of victory. Compliance dashboards start from scratch after it, knowing nothing about what was promised. The application and the award are treated as two unrelated documents.

They are not. Every budget line in a proposal is a promise, and every transaction afterwards either keeps it or breaks it. Nobody closes that loop, so we built it.

**Most grant software remembers the documents. GrantLoop remembers the promises.**

## What it does

GrantLoop carries one lineage end to end:

`NOFO -> application -> award -> transaction and evidence -> report -> renewal`

**Covenant** takes the Notice of Award and the application and derives an obligation model by diffing them. In our scenario it finds what a human reviewer would miss on award day: participant support was cut 40 percent, from $30,000 to $18,000, while the performance target it paid for was accepted unchanged at 120 youth. The agency cut the money and kept the promise. It then finds the same pattern a second time on a different pair of lines, because it is applying a rule rather than reciting a script.

It also reconciles the award against itself. Our Notice of Award states a federal share of $212,000 while its own budget lines sum to $234,000, and Covenant raises that $22,000 discrepancy as a critical exception rather than trusting the headline figure. Drawing funds against an award whose totals disagree is how a recipient acquires questioned costs it never chose.

**Ledger Sentinel** watches the transaction stream and classifies every expense into one of seven determinations: presumptively allowable, presumptively unallowable, missing documentation, requires allocation, requires prior approval, conflicts with award terms, requires human determination. Not a yes/no filter. Seven visibly different behaviors, each citing the regulation it applied.

A catering invoice is split rather than rejected: $412 of wine carved out as unallowable under 2 CFR 200.423, and the remaining $828 routed for programmatic review instead of being approved by association. A laptop purchase is blocked, and the reason is the interesting part: at $1,600 a unit the regulation actually permits it under 200.453(c), so the block cites the award's own specific condition. The regulation permits this, your award does not.

A membership invoice is escalated to a human with the exact question stated, because whether an organization's primary purpose is lobbying is a fact about the organization and not something that can be read off an invoice. Costs that match no rule escalate too. Silence is never approval.

**Reporting** assembles the SF-425 from actual ledger state with every figure traceable to the transactions behind it, then stops. 2 CFR 200.415(a) requires certification by an official authorized to legally bind the recipient, so the system assembles and a named human certifies.

## How we built it

**The classification engine is deterministic, and that is a design decision rather than a limitation.** A model is not asked whether a cost is allowable. That determination has to be defensible against a citation and reproducible on demand, and "the agent decided" is a far weaker claim than "the agent applied 2 CFR 200.454(e), and here is the paragraph." The language model's job is drafting the human-facing question when the fleet escalates, which is work a rule engine genuinely cannot do.

**Agents communicate only through events.** No agent calls another agent. Every state transition is an event carrying a `causation_id`, so any downstream fact walks back to the event that caused it. Every handler is idempotent on a key derived from the event's content, so at-least-once delivery becomes exactly-once in effect. Failures retry and then land in a dead-letter queue that is a panel on screen, not a line in a log.

The event contract is the only coupling in the system, which means the transport underneath it is swappable. The same twelve topics run over an in-process bus offline and Pub/Sub in the cloud, chosen by configuration, and no agent knows which one it is talking to.

**Two Cloud Run services, not five.** Four of the agents are low-frequency, human-paced, and share the same working set, so they run together in one orchestrator. The Ledger Sentinel deploys alone because it is the only high-volume, push-subscription, retry-heavy component, and isolating it buys real failure isolation instead of five services bought for the diagram. A defended two-service design says more about understanding the architecture than five undefended ones.

**Everything runs offline too.** The replay path is pure Python with no cloud dependency and no installed packages, and it produces byte-identical output every run, provenance chain included. It began as insurance for recording day, on the principle that a demo path which never touches the network cannot fail because of the network. It ended up being how the whole system was built while cloud access was still being sorted out.

## Challenges we ran into

**A confidently wrong citation is worse than no citation.** Our allowability ruleset was written from working knowledge and shipped marked `VERIFICATION_STATUS: DRAFT`, with the UI refusing to render any CFR number until that flag flipped. Verifying it against the eCFR API found four rules making claims the regulation does not support. The worst: we cited 2 CFR 200.474 for travel costs. Travel is 200.475. 200.474 is Transportation costs, meaning freight. We had also written that civic organization memberships require prior approval when 200.454(c) makes them allowable outright, and cited the record-retention section for a missing receipt when the requirement to have one is 200.403(g).

We were right not to write the de minimis indirect rate from memory. It is 15 percent of modified total direct costs, raised from 10 percent by the 2024 OMB revision.

**A green test suite proves only what it ran.** We deliberately broke sixteen things across the build to check the tests noticed. Two got through. Regressing the travel citation back to 200.474 passed everything, because no seeded transaction reaches the travel rule, so the regression test for the exact bug we had just fixed did not cover it. Disabling the idempotency check also passed everything, because the replay harness published each transaction once and never exercised redelivery. Both were the specific guarantees those tests existed to protect.

**Two arithmetic bugs, both found by asserting a total against its parts.** The SF-425 rolled each transaction into its top-level determination and silently dropped the $828 remainder of the split catering invoice, reporting $12,354 against a ledger of $13,182. Separately, the $22,000 award reconciliation gap had been sitting in our scenario unnoticed because nothing ever recomputed the total from the lines. No per-item check would have caught either. When you aggregate, assert the sum.

**Model availability is a deployment fact, not a documentation fact.** Every Gemini 3.x model ID returned 404 on our first project in every region we tried, while 2.5-flash worked fine. Only live probes settled it. Everything model-facing went behind a single `MODEL_ID` environment variable the same day, and nothing anywhere hardcodes a project ID. That turned out to matter: we changed Google Cloud projects mid-build and the code needed no edit.

## What we learned

Building a compliance product teaches you to hold yourself to the standard you are selling. Twice we hit a number that did not add up and the tempting fix was to make it tidy. The $22,000 gap could have been closed by inventing agency cuts that never happened. We surfaced it as a finding instead, because a tool that quietly reconciles away inconvenient arithmetic is precisely the tool nobody should trust with their federal award.

The same instinct applies to the seventh determination value. The easy design escalates nothing and looks more autonomous in a demo. The honest one admits that some questions are facts about the world that an agent cannot see from a transaction, and asks.

## What's next

Real bookkeeping integrations for actual transaction feeds, single-audit preparation, and multi-award support against the same obligation graph.

## Disclosure

The ledger feed, agency submission, and accounting-system integration are simulated and labelled as such on screen. The demo scenario, Riverbend Youth Services, is entirely synthetic. Discovery and full proposal generation are out of scope. The regulatory citations are real and verified against the eCFR.

---

## ⛔ Blocking gaps before Aug 31

Two of these are hard submission requirements that our code does not yet satisfy. They are not
copy problems, they are build problems.

| Gap | Why it blocks | Owner |
|---|---|---|
| **Gemini 3.5+ is not called by our code** | Every project "must use Gemini 3.5 or newer". Our Sentinel is deterministic by design and the model lane (drafting escalation questions) is not wired yet. | Aria Agent |
| **No Google Agent Framework used** | ADK, GenAI SDK, Antigravity or Genkit is required. We use none today. `google-adk` is in our tags on that basis, not on current code. | Aria Agent |
| Architecture diagram | Required file upload on Additional info. Does not exist. | unassigned |
| ~4-min demo video | Required. Blocks Project details from completing. | Pooof |
| Hosted project URL | Strongly recommended, and the visible proof of GCP deployment. Blocked on IAM. | Paing to grant Editor |
| Submitter type, country, start date, org name | Personal details only Aria can answer. | Aria |
| Reproducible testing instructions in README | Answer is Yes; README has them. Just needs selecting. | done in repo |

The first two are the ones that can disqualify us on a rules check no matter how good the build is.
Both are addressable: the escalation-question drafter is a genuine, honest use of Gemini, and
running the orchestrator's agents under ADK satisfies the framework requirement without changing
the deterministic classification design.
