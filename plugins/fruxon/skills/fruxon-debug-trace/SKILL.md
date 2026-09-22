---
name: fruxon-debug-trace
displayName: Debug a Fruxon Trace
description: >
  Work out why a run did what it did, from its execution trace: find the
  run, read the step tree, drill into a tool call's parameters and
  result, and reconstruct the state the agent decided from. Load when a
  run failed, hung, or produced a surprising result — including the
  common case of a run that reports COMPLETED but did the wrong thing.
---

You are now operating as a Fruxon execution-trace forensics specialist.

The question is almost never "which step threw". It's "why did the
agent decide *that*" — why it processed two items when twenty were
available, why it skipped a customer, why it stopped for nine minutes.
The trace holds the answer, but only if you read the inputs each step
saw, not just its status.

> Authoring failures — a revision that won't create, deploy, or run at
> all — are a different job. Go to `fruxon-build-agent` ("Common
> pitfalls") for those, and `fruxon-agent-mode` for the exit-code and
> error-envelope contract.

## Workflow

1. Find the execution record id.
2. `executions get` for the headline, `trace` for the step tree.
3. Find the step where the behaviour diverged from what you expected.
4. Read that step's **inputs** — parameters, and the result of whatever
   fed it. Most surprises are an input you assumed, not a bug.
5. Confirm across a second run before concluding it's systemic.

## 1. Find the run

```
fruxon agents executions list <agent>                    # newest-first
fruxon agents executions list <agent> -s FAILED -n 50
fruxon agents executions list <agent> --origin TEST      # your draft runs
fruxon agents executions list <agent> --since 2026-08-05 --until 2026-08-06
```

**When the report came from a person, not an alert**, filter by
conversation instead of by time — you rarely know the timestamp, and
scanning a busy agent's log for "the run that served this customer" is
hopeless:

```
fruxon participants list --query +972545614701 -o id     # person → id
fruxon agents executions list <agent> --participant <id>  # → their runs
fruxon agents executions list <agent> --session ts_9dbaf…  # one conversation
fruxon agents executions list <agent> --tool system.escalate_to_human --since 2026-08-01
fruxon agents executions list <agent> --with-tool-errors -n 20
```

`--query` matches channel addresses and linked account ids, so a phone
number, email or handle resolves to a participant id directly. `--tool`
takes `integrationId.toolId` and is backed by the tool-usage projection,
which lags the newest runs by about a minute.

Each row carries `subject` (a one-line "who and what"), `deliveryStatus`
and `runType`. **`COMPLETED` is not `DELIVERED`** — a run can finish
cleanly while its reply is withheld or never lands, and only
`deliveryStatus` says so.

Statuses, mirroring the backend's `AgentExecutionRecordStatus`:
`IN_PROGRESS`, `WAITING_FOR_ASYNC`, `COMPLETED`, `FAILED`, `CANCELLED`,
`REJECTED`.

- **`WAITING_FOR_ASYNC` is the only suspended state.** Consults, human
  approvals and sub-task fan-outs all report it. *What* the run is
  parked on lives in the trace's `waitingFor.kind`, never in the status.
- **`REJECTED` never ran.** Blocked at the pre-flight gate (cost budget,
  exhausted credits, invalid licence), so there is no trace to read —
  the record's rejection reason is the whole story.
- `--origin` defaults to `PRODUCTION`. Your own `agents draft run`
  invocations are `TEST`-origin and are invisible until you ask.

**From a dashboard URL.** The `id=` query parameter on an executions-tab
URL is the execution record id (under `group=session`, the root run's
record id) — paste it straight into `executions get`. If it 404s, fall
back to `executions list` narrowed to that timestamp.

**Listing does not mark sub-tasks.** A fan-out puts the orchestrator and
every spawned child in the same list, and the row shape doesn't say
which is which. `executions tree <agent> <any-id-in-the-tree>` answers
this directly — it returns the whole tree with parentage and depth, from
any node in it. Without it: the orchestrator is the one whose trace
contains the `spawn_subtasks` step, and each child's record id is inside
that step's result (see §5).

## 2. The three facets

| Command | Answers |
|---|---|
| `executions get <agent> <id>` | status, timing, cost, tokens |
| `executions trace <agent> <id>` | what ran, in what order, what broke |
| `executions result <agent> <id>` | the run's inputs and final output |
| `executions tree <agent> <id>` | every run in the spawn tree, and what the whole request cost |

Each maps to one endpoint. `get` is deliberately thin — it will not tell
you a run is blocked on a named person; only `trace` carries that.

`tree` is the one to reach for on a fan-out: it returns the orchestrator,
every sub-task and every consult in one request, each with its depth,
status and cost. Your run is marked `▸` and is often not the root —
asking about a consult returns the tree that consult sits in.

## 3. Read the step tree

Text output renders the whole tree, one line per step:

```
✓ Trace · 20 step(s) · COMPLETED · 1 error(s)
   agent      emailpoliciesparser (revision 59)
   duration   11m 23s

   1  FLOW_STEP · Agent  (SUCCESS · 19.4s)
     1.1  LLM_STEP · LLM Query  (SUCCESS · google/gemini-3.5-flash)
       1.1.2  TOOL · Search Emails  (SUCCESS · 4.8s · google_gmail/search)
       1.1.3  TOOL · Spawn Subtasks (batch)  (SUCCESS · 36.7s · system/spawn_subtasks)
         1.1.3.1  TOOL · Spawn Subtasks (batch)  (SUCCESS · 36.7s · system/spawn_subtasks)
       1.1.10  TOOL · Consult for Role  (ERROR · system/consult_for_role)
           ✗ addressing_failed: role 'advisor' no_match — No available participant…
```

The dotted path is a stable handle — use it when talking about a step.

**The JSON shape.** `--output json` is where the real detail lives, and
the shape is not what the top-level key names suggest:

```
{
  "status":           "COMPLETED" | "WAITING_FOR_ASYNC" | …,
  "runType":          "ROOT" | …,
  "rootExecutionId":  "…",
  "waitingFor":       { … },          # only while suspended
  "trace": {
    "agentId", "agentRevision", "startTime", "endTime",
    "traces": [                        # ← the flow's top-level steps
      { "id", "displayName", "type": "FLOW_STEP", "status", "duration",
        "steps": [                     # ← nested, recursively
          { "type": "LLM_STEP", "llmStepTrace": { … }, "steps": [ … ] },
          { "type": "TOOL",     "toolTrace":    { … }, "result": { … },
            "status": "ERROR", "error": "…" }
        ] } ] } }
```

Note `trace.traces[]`, **not** `trace.steps[]`; a step's kind is `type`
and its label is `displayName`. Useful one-liners:

```
# every tool that ran, in order
… trace <agent> <id> -o json | jq -r '.. | objects | select(.toolTrace) | .toolTrace.tool | "\(.integrationId)/\(.id)"'

# only the steps that errored, anywhere in the tree
… trace <agent> <id> -o json | jq -r '.. | objects | select(.status=="ERROR") | "\(.displayName): \(.error)"'

# what the run is blocked on
… trace <agent> <id> -o json | jq '.waitingFor'
```

`jq`'s recursive descent (`..`) is the right tool here — writing out
`.trace.traces[0].steps[0].steps[3]` by hand breaks the moment the flow
gains a step.

## 4. If the run is suspended

```json
"waitingFor": {
  "kind": "CONSULT", "displayName": "Dor Gelless", "participantKind": "PERSON",
  "topicId": "b8a2e04a-…", "waitingSince": 1785999774196, "expiresAt": 1786433573679
}
```

- `kind` is `CONSULT` (a participant's answer), `APPROVAL` (a human
  go/no-go), or `SUBTASK` (delegated children — `childCount` says how
  many). This is the only signal separating a machine wait from a
  human one.
- `expiresAt` is the TTL after which the sweeper times the wait out.
  A run that looks stuck may simply be waiting on someone who went home.
- Follow a consult with `fruxon agents topics get <agent> <topic-id>`
  and `topics messages` — that's the conversation, including the reply.

> ⚠️ **A suspended trace is live.** Fetch it twice and you may get two
> different documents: the consult resolves, the run continues, steps
> appear. If you are reasoning about a `WAITING_FOR_ASYNC` run, save the
> payload to a file and analyse the file, or re-fetch and re-read before
> you conclude anything. `endTime: 0` (not `null`) means still open.

## 4b. Ending a run that will not end itself

Two verbs, and picking the wrong one wastes a cycle:

```
fruxon agents executions cancel-wait <agent> <id> --yes   # skip the consult, run continues
fruxon agents executions cancel      <agent> <id> --yes   # end the run, terminally
```

- **`cancel-wait` is the scalpel.** It resolves the consult as cancelled
  and the run picks up where it left off. Right when a specific consult
  is the blocker and the run should still finish — someone answered out
  of band, or the participant is gone.
- **`cancel` is the hammer.** Use it when skipping one consult would not
  help: an agent that re-issues the same consult just parks again.
- **`cancel-wait` only skips consults.** An `APPROVAL` or `SUBTASK` wait
  reports the same `WAITING_FOR_ASYNC` and gets a 400. Read
  `waitingFor.kind` (§4) *before* choosing.

`cancel` answers differently depending on what it caught:

- Parked run → killed on the spot; the command says so.
- Live run → the worker executing it lives in another process, so this
  only *requests* cancellation and the output says "requested". It stops
  at its next checkpoint. **A run that finishes on its own first stays
  `COMPLETED`** — the cancel is not retroactive. `--wait` polls and then
  tells you which of the two happened.

> Both verbs confirm first, and under agent mode they refuse without
> `--yes`. They stop live work on a deployed agent.

## 5. Drill into a step

Every `TOOL` step carries what went in and what came back:

```
toolTrace.tool            # {integrationId, id} — the identity to grep for
toolTrace.parameters      # exactly what the model passed
toolTrace.resultDelivery  # SIZES ONLY — how much the model was shown
result.jsonValue          # structured result …
result.strValue           # … or a string one
error                     # present iff status == "ERROR"
```

**`result` is a sibling of `toolTrace`, not a field inside it.** Read
`toolTrace` alone and every payload looks stripped of its results —
`resultDelivery` carries character counts and nothing else, so it reads
like a redaction. It isn't: the value is right there one level up.
Anyone who concludes "the trace doesn't expose tool results" has looked
in `toolTrace` and stopped.

For a quick read without jq, `--show-io` prints each tool step's
parameters and result beneath its line in the tree, truncated:

```
fruxon agents executions trace <agent> <id> --show-io
```

Whole results, unabridged, in JSON:

```
… trace <agent> <id> -o json | jq '.. | objects
  | select(.toolTrace) | {tool: .toolTrace.tool.id,
                          params: .toolTrace.parameters,
                          result: .result}'
```

**Check `resultDelivery` before theorising.** It reports
`originalChars` / `deliveredChars` and `offloaded` / `projected`. A tool
that returned 22 records but delivered a truncated view explains a model
that "ignored" most of them — and no amount of prompt-reading will show
you that. Equally, if `offloaded` is false and the counts match, you can
trust that the model genuinely saw the whole result and the fault is in
its reasoning or its instructions.

`LLM_STEP` steps carry:

```
llmStepTrace.systemInstructions  # the deployed prompt — an ARRAY of
                                 # message records, not one string
llmStepTrace.reasoningBlocks     # the model's own account of why
llmStepTrace.llmMessages         # the conversation turns
llmStepTrace.tools               # the tools the step had available
llmStepTrace.{input,output,cached,thinking}Tokens and matching costs
```

`reasoningBlocks` is the highest-value field in the whole payload when
the question is "why did it decide that" — it often names the rule it
was following. `systemInstructions` lets you read the prompt the run
*actually* executed rather than the file you think is deployed.

`--show-thinking` prints the reasoning inline, the way `--show-io` does
for tool payloads, so you do not have to drop to `jq` for the one field
you came for:

```
fruxon agents executions trace <agent> <id> --show-thinking
fruxon agents executions trace <agent> <id> --show-io --show-thinking
```

The two flags answer different questions — `--show-io` is "what was it
handed", `--show-thinking` is "what did it make of that" — and the
second is the only one that catches a model reasoning from how a system
like this *usually* works instead of from anything it retrieved. That
failure leaves no error, no missing call and no odd result. Blocks are
numbered (`think 2/4`) because one LLM step spans every model turn: the
model re-reasons after each tool result, and which pass a claim first
appears in is most of the diagnosis.

**Sub-task correlation.** A `spawn_subtasks` step's result embeds each
child's `execution_record_id`. Pull them out and trace each child as a
first-class run:

```
… trace <agent> <id> -o json | jq -r '
  [ .. | objects | select(.toolTrace.tool.id=="spawn_subtasks")
    | .result.strValue? // empty | fromjson
    | .. | objects | .execution_record_id? // empty ] | unique[]'
```

The shape-agnostic form is deliberate: a batch spawn nests a child step
per sub-task, so recursive descent hits **two** result shapes — the
parent's `{results: [...]}` and each child's bare
`{execution_record_id, status, response, session_id}`. Reaching straight
for `.results[]` works on the parent and throws "Cannot iterate over
null" on every child. `fromjson` inside `jq` also saves a second process
and keeps the whole thing one pipeline.

> ⚠️ **Payloads are double-encoded, and non-ASCII is escaped.** A
> spawn's `prompts` parameter is a JSON *string* inside the parameters
> object; its result is a `strValue` string containing JSON containing
> more JSON. Expect two or three `jq`/`json.loads` passes. Non-Latin
> text arrives as `\uXXXX` — use `jq -r` and, in Python,
> `json.dumps(…, ensure_ascii=False)`, or you will be reading escape
> soup instead of the customer's name.
>
> **Redirect traces to files; don't hold them in shell variables.** Once
> `jq -r` has decoded the escapes, the payload contains real UTF-8, and
> `payload=$(fruxon … -o json)` in zsh fails on it with `character not
> in range` — every downstream `jq` then sees truncated input and dies
> on an unfinished string. Looping over many runs? Write each trace to
> `<id>.json` and read the files.

## 6. Reconstruct the state the run decided from

A step's output is rarely the mystery. The mystery is the state it read.

- **Memory is the state machine** for scheduled agents — watermarks,
  processed-id lists, pending batches. `memory_search` results *inside a
  trace are truncated*, so the trace alone cannot tell you what the run
  read. Two ways out: `fruxon agents memory list <agent>` /
  `memory get` for the value **now**, or the *previous* run's
  `memory_write` step for the value **as it was**. Prefer the second —
  memory has usually been overwritten since.
- **Triggers set the batch size.** `fruxon triggers get <trigger-id>`
  gives the cadence, timezone, and the literal parameter mappings the
  agent is invoked with. A run that processed "too few" items is very
  often a run that fired sooner than the schedule implies — an
  off-schedule fire consumed the backlog and advanced the watermark.
  `triggers list` alone won't tell you: it carries `lastFiredAt` but not
  the schedule.
- **A ledger automation's state is the item, not memory.** When the run's
  trigger type is `LEDGER_ITEM`, the durable state is the work item the
  sweep claimed — so the question "what did this run know?" is answered by
  `fruxon triggers ledger items <trigger-id> --item-key <key>` (its
  accumulated `data`) and `ledger transitions <trigger-id> <item-id>` (every
  attempt, each with the `executionRecordId` behind it). Both are per-item
  history the trace cannot carry: a run shows one attempt, the transition
  log shows why there was a third. `fruxon triggers preview-shape
  <trigger-id>` then renders the exact `user_query` that stage sends,
  including the item payload appended to the instruction — which is usually
  most of the prompt and appears nowhere in the shape as authored.
- **A WAITING item is not stuck — it is parked, and the question may have
  reached nobody.** `WAITING` means the item is on an ASK stage's batch, and
  `ledger items` carries the `batchId` that joins it to one. The pairing is
  total for that status (an item is WAITING only while its batch is open), so
  one `fruxon triggers ledger batches <trigger-id> --open-only` resolves every
  waiting row. Read `delivery` there before anything else: `UNDELIVERABLE` and
  `FAILED` mean **nobody was asked and nobody will answer**, so the items sit
  until the batch expires while the batch, the count and the stage all look
  healthy — this is the failure that looks like nothing at all. `QUEUE_ONLY`
  is not a fault; the contact is queue-bound and the pending row is itself the
  operator-queue item. The way out is `fruxon triggers questions answer` out of
  band, or `ledger cancel-batch`, which returns the items to READY.
- **An IGNORED item was a decision, and the reason is the diagnosis.**
  `ledger funnel` stops at a count, which nobody can act on. `fruxon triggers
  ledger exclusions <trigger-id>` lists every reason a stage recorded with how
  many items each holds — usually the fastest way to see that a prompt is
  excluding a whole class of work it should not. Each count is exactly what
  `redrive-many --ignore-reason` resolves, so the diagnosis and the fix use the
  same string, matched whole and case-sensitively.
- **"What is this automation costing?" is a per-pass question.**
  `executions get` prices one run; a schedule's bill is the runs its sweeps
  caused, which is what `fruxon triggers ledger passes <trigger-id>` reports
  — one row per fire, with `admitted` / `dispatched` / `completed` / `runs`
  and the all-in USD of that pass. Two readings to get right. `runs` sits
  below `dispatched` while runs are in flight or when a dispatch was parked
  on a human, so the gap is not a lost item. And a pass's `cost` **rises
  after** its `firedAt` as those runs finish — read it once `completed` has
  caught up with `dispatched`, or you are reading a floor. `ledger funnel`
  carries the same two fields per stage/status cell, which is how you find
  *where* the money goes rather than only how much; a `Cost` of `—` there
  means nothing in the cell has ever been claimed, as against `$0.0000`,
  which means it ran and was genuinely free.
- **"Too few items" needs the size of the backlog, not a sample of it.**
  `fruxon triggers test-source <trigger-id>` lists a page of what the door
  returns right now; a full page comes back saying *more available*, which
  is not an answer to how far behind an automation is.
  `fruxon triggers test-source <trigger-id> --count` is: it pages the same
  door to exhaustion and reports the total, how many a `door.skipWhen`
  filter drops, how many the ledger already holds, and how many clear the
  watermark. `total - filtered - already held` is the work a pass would
  actually admit, and on a healthy automation that difference is small —
  every pass re-lists its own overlap window, so a large `already held` is
  the source working, not repeating itself. Add `--apply-watermark` for
  what the *next* pass would see rather than what the query matches at
  all. Ceilinged server-side at 2,000 records / 20 pages; when a ceiling
  stops it the CLI says "at least", and that floor is not a number to
  quote as a backlog.
- **"The model never saw that field" is the projection, not the prompt.**
  An item carries only what `workShape.door.projection` names, and the
  stage's `user_query` carries the item — so a field an instruction asks
  about is absent from the prompt whether the source omitted it or the
  shape dropped it. `fruxon triggers test-source <trigger-id>` prints each
  record as the item will carry it, with an `item keeps` line naming the
  surviving paths, which separates the two. Items admitted BEFORE a
  projection changed keep what they were admitted with, so an old item and
  a new one under the same shape legitimately carry different fields —
  compare `ledger items` against the current `test-source` output rather
  than assuming the ledger is uniform. An absent projection keeps whole
  records, and then the field really was never sent. Note that `ledger
  items` returns one page of 20 and says how many matched in total — do
  not read a page as the ledger. Narrow it with `--stage` / `--status`, or
  ask for the walk with `--all`.
- **"The automation ignored almost everything" may be a filter, not a
  decision.** A shape's `workShape.door.skipWhen` drops matching records
  *before* admission — no item, no transition, no model call — so those
  records appear in no ledger query at all, and the gap shows up only as
  a source that lists far more than the ledger holds. `fruxon triggers
  test-source <trigger-id>` marks each such record `FILTERED` and counts
  them in the footer. A large IGNORED pile is the opposite finding: that
  is a stage spending a model call per record to reach a verdict, which
  is what a `skipWhen` rule exists to replace when the question is one a
  dotted path can answer. The filter governs admission only — items
  admitted before it was added stay where they are.
- **A knowledge-base hit is state you can re-run.** When the step that
  decided things was `search_assets`, the trace gives you the query it
  sent and what came back — but not whether anything *better* was there.
  Replay it:

  ```
  fruxon assets search <asset-id> -q "<the query from toolTrace.parameters>"
  fruxon assets search <asset-id> -q "<what the customer actually asked>"
  ```

  Two different answers means the retrieval was the fault, not the
  reasoning. The `<asset-id>` is in the run's `<knowledge_base>` system
  block (`llmStepTrace.systemInstructions`).

  Read `score` carefully: in the default `HYBRID` mode it is normalised
  against the best hit, so **the top result always scores 1.0** and tells
  you nothing about absolute relevance. `--mode VECTOR` gives a real
  0–1 similarity when you need to judge that.

  **When the chunk you expected is indexed and still did not come back,
  `--explain` says which leg lost it:**

  ```
  fruxon assets search <asset-id> -q "<the query from the trace>" --explain
  ```

  It runs all three legs, prints where each placed every fused hit, and
  names what went wrong as a `code` a driver can branch on:

  | code | what it means |
  |---|---|
  | `FTS_LEG_EMPTY` | full-text matched nothing, so HYBRID ran on the vector leg alone |
  | `VECTOR_LEG_EMPTY` | the reverse — usually embedding-side, not a query problem |
  | `WEAK_VECTOR_MATCH` | best true similarity is low; nothing here is a confident match |
  | `FUSED_DROPPED_LEG_TOP` | a leg's best hit fell below the fused cut — try the weights |
  | `ALL_LEGS_EMPTY` | check ingestion before blaming the query |

  `FTS_LEG_EMPTY` is the one to expect on an agent's own query. The
  full-text leg wants every term of the query in a single chunk, so a
  long query matches *less* than a short one — and a model writes longer
  queries the harder it tries. A chunk that ranks first for four words
  can fall out of the top twenty-five for the same four plus four more,
  with nothing in the ordinary result to show it. Re-run the search
  shortened before concluding the answer is not indexed.

  If a search finds nothing you expected to be there, the index — not the
  query — may be the problem: `fruxon assets documents <asset-id>` shows
  what was ingested, and a `chunkCount` of 0 is a file that produced no
  indexable text at all.
- **Compare against the previous run.** `executions list`, take the run
  before, trace it, and diff the inputs. A watermark, a roster size, a
  memory value: one of them moved.

## 7. "The run says COMPLETED but it did the wrong thing"

The most common real defect. Two shapes:

**A step errored and the agent recovered.** Status stays `COMPLETED`
because the model routed around the failure. It will be in the tree as
an `ERROR` step — the text renderer counts them in the headline
(`· 1 error(s)`). These repeat silently forever; check whether the same
step errors in the previous run too before dismissing it as a blip.

**Every step succeeded and the *decision* was wrong.** Nothing is red.
Work backwards: find the step whose output first disagreed with your
expectation, then read the inputs it had — the tool result that fed it,
the memory it searched, and `reasoningBlocks` for its own account. In
practice the answer is usually one of: a watermark or filter excluded
more than you thought; a dedupe rule collapsed rows; the result was
truncated before the model saw it (`resultDelivery`); or the deployed
`systemInstructions` are not the prompt you have open in your editor.

## 8. "The agent went quiet and I cannot see why"

Three separate causes, none of which appear in a trace, because in each one
the runtime worked correctly and the *conversation* is where the story is.

**The customer's message never reached an agent.** A withheld inbound is
recorded and then deliberately kept from every agent — a human owns the chat
in the source console, or admission refused the sender. It never becomes a
conversation turn, so `topics messages` shows the customer writing and
nothing after it, and there is no run to trace because no run happened.

```
fruxon messages list --agent <agent> --delivery WITHHELD --since 2026-08-01
fruxon messages list --delivery WITHHELD_PENDING     # never acted on at all
```

`withheldReason` is `HUMAN_OWNED_CONVERSATION` (a person had the chat) or
`ADMISSION_REFUSED` (the sender is unknown or unenrolled). A row with a
reason and no `withheldConsumedAt` was never replayed into a later run and
never discarded — nothing will drain it.

**A person took the conversation over.** Then the agent is muted on purpose.

```
fruxon escalations history --agent <agent> --address +9725...
```

`escalations list` will not show it — that is a queue, and a takeover leaves
it the moment it stops needing someone. **`humanObservedAt` is the field
that matters**: null means nobody was ever seen actually holding the chat,
even on a `RESOLVED` row, because ownership returning to the assistant is
equally what a chat nobody touched reports. `openDurationMs` is how long
they had it, and is null while the handoff is still open.

**Nobody was reachable to take it.** Then the customer was told someone
would follow up and the runtime moved on — `escalations unhandled`. To see
whether that was a misconfiguration or the design:

```
fruxon escalations policy <agent>
```

An empty ladder under `mode: NATIVE_HANDOFF` is correct — the channel's own
console supplies the human. An empty `offerableOperators` under `BRIDGE`
means an escalation right now would degrade. Read `configuredOperators`, not
`offerableOperators`, when reconstructing a *past* escalation: the second is
filtered by who is available this minute, and presence today says nothing
about presence then.

## 9. "The agent answered as if it had never seen the conversation"

The opposite failure: the agent did reply, promptly and fluently, to a
customer whose question only makes sense against an exchange it appears not
to know about. The trace is clean, because the run genuinely had no history
to work from — it was a *different session*.

A topic outlives its sessions. The platform ends an episode and mints a fresh
one rather than keeping one open, and the fresh one starts with an empty
transcript. `topics messages` stamps every turn with its `sessionId`, so the
boundary is visible there — but not the reason for it.

```
fruxon agents topics sessions <agent> <topic>
```

**`endCause` on the *previous* session is the answer.**
`CONSOLE_ALREADY_RESOLVED` means a human closed the conversation in the
provider's own console; that is what ended the session that knew about the
escalation. A follow-up sent seconds later lands in a fresh session, and the
agent answers it blind — which is precisely when a customer asks about
something a colleague just told them.

`seedContextIn` says whether the runtime pointed the new session at that
resolved case. A `recentSupportHandoff` block carries the ids —
`supportCaseId`, `sourceTopicId`, the handoff, and when it resolved — and its
absence on a session that opened moments after a handoff resolved is the
agent going in with nothing. The seed's prose is deliberately not on the
wire: read `sourceTopicId` with `topics get` for the redacted outcome the
agent was actually shown.

Two shapes to check while you are here. A session still `RUNNING` on a
`RESOLVED` topic is an episode nothing ever closed — which is also why
nothing handed the conversation back to its console. And an `endCause` with
no `endedAt` is an end that was *requested* and never applied; a new inbound
message voids it, so it is not an ended episode and must not be counted as
one.

## 10. Reproduce the bad reply, then prove the fix

Reading the trace tells you why the agent answered badly; it cannot tell you
whether your edit answers better. Replay the same turn instead of waiting for
the next customer:

```
fruxon agents topics messages <agent> <topic> -o json      # the id of the reply that went wrong
fruxon agents draft pull <agent>                           # edit, then:
fruxon agents draft push <agent>
fruxon agents sandbox fork <agent> <message-id> --send --draft -o id
fruxon agents sandbox stream <session>
```

`fork` copies every turn the agent had loaded when it produced that reply —
from the last summary checkpoint before it, so the window matches — into a
fresh sandbox session, and `--send` re-sends the customer message that
preceded it. `--draft` runs your draft rather than the deployed revision;
check `sandbox draft <session>` if it is refused, or if `onCurrentRevision` is
false (your draft forks from an older revision than production runs).

What this does **not** reproduce: the copied history is frozen, but tools run
live against today's data, so a lookup can answer differently than it did
then. Only one topic's history is copied. And the sandbox blocks channel sends
and memory writes but **not integration writes** — `--send` holds every
create / update / delete call as a `pending_approval` for exactly that reason;
answer it with `agents approvals respond`. The forked topic then appears in
`topics list` under the real participant, flagged `isSandbox` — it is not
their conversation.

## Gotchas

- **`role: assistant` does not mean the agent said it.** A human
  colleague's message is stored as an `ASSISTANT` turn on purpose, so the
  agent reads it on re-engage instead of re-asking what the person already
  handled. `author` is the field that separates them: `HUMAN_OPERATOR` is a
  person, `AGENT` is the agent. `UNSPECIFIED` means the row predates
  authorship stamping and could be either — it is **not** a synonym for
  `AGENT`, and treating it as one is how an operator's words get quoted back
  as the agent's.
- **A fresh `sessionId` is not a new conversation.** One topic spans many
  sessions, and each new one starts with an empty transcript — so an agent
  can answer a follow-up knowing nothing about the exchange directly above
  it in `topics messages`. `topics sessions` says why the previous episode
  ended; `endCause: CONSOLE_ALREADY_RESOLVED` is the common one.
- **A gap in a transcript may be a message that was never delivered.** A
  withheld inbound is absent from `topics messages` entirely rather than
  shown as unanswered, so the transcript cannot distinguish "the agent chose
  not to reply" from "the agent never saw it". `fruxon messages list` can.
- **`get` won't tell you a run is blocked.** Only `trace` carries
  `waitingFor`. A suspended run and a hung one look identical from `get`.
- **Ids in agent-written memory may be corrupt.** When a prompt has the
  model re-emit a long list of opaque ids each run, it garbles them.
  Verify a stored id against a real one before trusting a dedupe list —
  a near-miss (one hex character off) is the tell.
- **A trace's own `duration` on the outermost step is not the run.** A
  run that suspended and resumed reports only the resumed segment there.
  The run span is `trace.endTime - trace.startTime`.
- **`executions list` has no cursor.** It's a time-ordered log; to go
  further back, slide `--since` / `--until` rather than paging.
- **"Cancellation requested" is not "cancelled".** For a live run the
  command returns before the worker has stopped. Read the record back
  (or pass `--wait`) before reporting a run as cancelled — it may have
  completed instead.
- **A tree can be pruned by retention and still look whole.** `executions
  tree` warns when the retention window dropped runs out of it; the
  totals then cover only what is left. Without that line the tree just
  draws short.
