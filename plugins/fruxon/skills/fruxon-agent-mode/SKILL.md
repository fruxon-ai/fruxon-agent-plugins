---
name: fruxon-agent-mode
displayName: Read fruxon's output and recover from errors
description: >
  The fruxon CLI's machine contract: what its exit codes (2, 10-16)
  mean, the {"error":{...}} envelope on stderr, commands that refuse
  without --yes (exit 16), and the JSON / NDJSON shapes that `agents
  draft run`, `agents sandbox stream`, `agents sandbox test`, and
  `agents tests watch` emit. Load when a fruxon command fails or
  refuses, when you need to parse one of those streams, or when
  scripting the CLI from CI.
---

This is the contract the `fruxon` CLI keeps with a program driving it:
how to read what a command returns, and how to recover when it fails.
Every behavior here is tested and stable; prefer it over inferring from
`--help` text. For *what to do* — build an agent, debug a run, wire an
integration — load the task guides listed at the end.

## Agent mode — what it is, how it's detected

The CLI auto-detects "agent mode" from any of these environment
signals (true if any is set):

- `FRUXON_AGENT_MODE=1` — explicit opt-in
- `CLAUDECODE=1` — set by Claude Code in spawned shells
- `CODEX_THREAD_ID` (any value) or `CODEX_CI=1` — set by Codex in
  spawned shells
- `CI=true` / `CI=1` — universal automation marker

In agent mode the CLI:

- Defaults every `--output` to `json` (humans get `text`)
- Drops banners, spinners, and chrome from stderr
- Switches `fruxon agents draft run` and `fruxon agents tests watch` to
  newline-delimited JSON on stdout
- Refuses any path that would block on stdin (browser login, `--edit`,
  missing `--yes`) with a typed exit code instead of hanging

## Exit codes — typed, stable, sufficient for retry logic

Every failure classifies into one of these:

| Code | Slug | Meaning |
|---:|---|---|
| 0 | — | Success |
| 1 | `generic` | Unclassified failure (legacy paths, user-cancel) |
| 2 | `usage` | Parse error — unknown flag, missing argument, unknown command, a group invoked with no subcommand. At every depth, including a bad flag on `fruxon` itself. Never a crash report. |
| 10 | `auth_required` | 401/403, no credentials, missing scope |
| 11 | `not_found` | 404 — the agent / integration / tool / key doesn't exist |
| 12 | `validation` | 400/422, bad flag value, malformed body, pre-flight failed |
| 13 | `conflict` | 409 — draft moved, version mismatch |
| 14 | `server_error` | 5xx, mid-stream server failure |
| 15 | `network_error` | Couldn't reach the API |
| 16 | `interactive_required` | A blocking prompt was hit in agent mode |

A driver branching retry/abort decisions should match on these
numbers, not on prose. The codes are picked outside Python's (0/1/2)
and shell's (126+) common range so they don't collide.

## Error envelope — every failure speaks JSON

In agent mode, every error path emits a single JSON line on **stderr**
(your stdout stays reserved for the command's primary output):

```json
{"error":{"code":"auth_required","message":"No workspace found.","exit_code":10,"hint":"Run fruxon login --workspace <id>..."}}
```

Fields are stable across releases. `code` is the slug from the exit-
code table above. `message` is plain text — Rich markup is stripped.
`hint` may be absent when there's no actionable next step. To recover,
read stderr's last JSON line on non-zero exit.

## Interactive guards — what to do when you hit one

These paths block on a human under normal use; in agent mode they
fail fast with exit `16` (`interactive_required`) and a hint naming
the bypass flag.

| Path | Bypass |
|---|---|
| `fruxon login` (no key) | Pass `--token $FRUXON_TOKEN` |
| `fruxon agents draft run --edit` | Pass the value via `-p key=value` or `--params file.json` |
| `keys delete` (no --yes) | Pass `--yes` |
| `agents tests delete` (no --yes) | Pass `--yes` |
| `agents budget delete` (no --yes) | Pass `--yes` |
| `agents draft evaluate` (no --yes) | Pass `--yes` — it costs real money |
| `agents approvals respond` / `cancel` (no --yes) | Pass `--yes` — **but stop first.** This responds to a *human-in-the-loop* gate; a response can run the gated tool. Only auto-`--yes` if the human you're acting for explicitly told you to approve/reject this request. Defaulting to approve defeats the gate. |
| `agents memory forget-subject` (no --yes) | Pass `--yes` — it irreversibly deletes a subject's memories (GDPR forget). |
| `triggers fire` (no --yes) | Pass `--yes` — it runs the bound agent(s) now (cost + side effects). |
| `triggers delete` / `unbind` (no --yes) | Pass `--yes` — removes the trigger / its agent wiring. |
| `participants delete` (no --yes) | Pass `--yes` — removes the participant from the network. |
| `capabilities delete` (no --yes) | Pass `--yes` — removes the capability from the routing vocabulary. |
| `participants unbind` (no --yes) | Pass `--yes` — removes the participant from the agent's consult roster. |
| `consult-pins delete` (no --yes) | Pass `--yes` — removes the deterministic routing override. |

## Workspaces — one key each, named per command

A Fruxon key is a **(user x workspace)** credential. It is stored in one
workspace's residency cell and authenticates only at that cell's host, so
there is no install-wide key: signing in happens once per workspace and
each keeps its own.

Every command takes `--workspace <id>`; without it, the stored default is
used. The CLI resolves the workspace first, then that workspace's key
*and* host together — they cannot be mixed.

```bash
fruxon workspaces list                      # what this machine holds, offline, no auth
fruxon agents list --workspace acme-corp    # run against one, whatever the default is
fruxon config set workspace=acme-corp       # change the default
fruxon login --workspace acme-corp          # add one (does NOT evict the others)
fruxon logout --workspace acme-corp         # drop one; --all drops every one
```

Naming a workspace this machine holds no key for fails **locally**, before
any request, with exit `10` (`auth_required`) and a hint naming the login
to run — the `hint` lists the workspaces that *are* signed in, so recover
by picking one of those or running the login it names. Do not read that as
a permissions problem; nothing was sent.

`FRUXON_TOKEN` is the exception and stays unkeyed: when set it is used
verbatim with whatever workspace was resolved. That is the CI path, and
the caller exporting it is the one asserting the two match.

`fruxon login` is additive and never prompts to replace a stored key, so
it has no interactive guard beyond needing a browser (see Interactive
guards above).

## Discovery — one call to learn the whole CLI

Two commands, both offline, no auth required, both JSON in agent mode:

```
fruxon describe                # the whole command tree, schema_version'd
fruxon examples [topic]        # curated pasteable invocations
```

`describe` is the single most useful call: it returns every command
path, its arguments, options (long + short), types, defaults, choices,
repeatable flags, hidden flag, and curated examples per top-level
group. Read it once and you're fluent. The document is versioned via
`schema_version` at the top — if you parse it, pin to the major you
saw. After an exit `2` (usage error), re-read the command's entry in
`describe` rather than guessing another flag.

## Output shapes

### `agents validate` and `agents draft validate`

`fruxon agents validate <agent> -p k=v` pre-flights run parameters. Returns:

```json
{
  "valid": true,
  "errors": []
}
```

…or, with findings:

```json
{
  "valid": false,
  "errors": [
    {"parameter": "user_qury", "code": "unknown_parameter", "expected": ["user_query"]},
    {"parameter": "user_query", "code": "missing_required", "expected": "string"}
  ]
}
```

Crucially, every finding is surfaced in **one pass** — don't iterate
one-error-at-a-time. The `code` slugs are stable: `missing_required`,
`unknown_parameter`, `wrong_type`, `invalid_option`. Validation fails
with exit 12; valid payloads exit 0. `fruxon agents draft validate`
lints a draft *body* with the same `{valid, errors}` envelope and exit
code, plus an advisory `warnings[]` that never flips `valid`.

### `agents draft run` — NDJSON event stream in agent mode

```
fruxon agents draft run my-agent -p user_query="hello"
```

Emits one JSON record per line on stdout. Frame:

```json
{"type":"start","schema_version":2,"agent":"my-agent"}
{"type":"text","delta":"Hel"}
{"type":"text","delta":"lo."}
{"type":"tool_call","id":"tc-1","name":"search","display_name":"GitHub search",
  "integration_id":"github","tool_type":"Api","arguments":{"q":"x"},
  "start_time_ms":1700000000000}
{"type":"tool_result","id":"tc-1","status":"succeeded","result":{"hits":3},
  "end_time_ms":1700000000042}
{"type":"usage","input_tokens":100,"output_tokens":250,
  "cached_tokens":30,"cache_write_tokens":12,"thinking_tokens":5,
  "web_search_calls":2}
{"type":"done","agent":"my-agent","record_id":"rec-99","session_id":"sess-1",
  "duration_ms":1234,"total_cost":0.0012,"input_cost":0.0008,
  "output_cost":0.0004,"cache_write_tokens":12,"cache_write_cost":0.0001,
  "web_search_calls":2,"web_search_cost":0.0002,
  "provider_reported_cost":0.0011,"agent_revision":7}
```

Stream `text.delta` strings in arrival order to reconstruct the
response body. Match `tool_result.id` to the corresponding
`tool_call.id`. Branch on `tool_result.status` (`succeeded` /
`failed` / `cancelled`) for the authoritative pass/fail signal —
don't infer from `result` shape. The `done` record carries the
`record_id` you'll pass to `fruxon agents executions trace` for post-mortem inspection.

**Event types you'll see** (all on a single ``run`` may overlap):

| `type` | When | Key fields |
|---|---|---|
| `start` | First | `schema_version`, `agent` |
| `text` | LLM streamed text | `delta` |
| `tool_call` | Agent dispatched a tool | `id`, `name`, `arguments`, `integration_id`, `tool_type` |
| `tool_result` | Tool finished | `id`, `status`, `result`, `end_time_ms` |
| `status` | Backend state change | `status` |
| `usage` | Near end of stream | `input_tokens`, `output_tokens`, `cached_tokens`, `cache_write_tokens`, `thinking_tokens`, `web_search_calls` |
| `done` | Terminal | `record_id`, `session_id`, `duration_ms`, costs (incl. `cache_write_cost`, `web_search_cost`), `provider_reported_cost`?, `agent_revision` |
| `error` | Terminal on failure | `message`, `code`? |

Cost-breakdown fields on `usage`/`done` are additive: backends that
don't track a bucket omit the key, so treat a missing field as 0.
`provider_reported_cost` is the exception — it's omitted when the
LLM provider reported no cost at all, which is not the same as $0.

**HITL pause.** If the run paused for human approval, `done` carries
`status: "waiting_for_human"` and `human_approval_request_id` instead
of the trace fields — same `type: "done"`, distinguished by the
`status` field:

```json
{"type":"done","agent":"my-agent","record_id":"rec-99","session_id":"sess-1",
  "status":"waiting_for_human","human_approval_request_id":"har-7"}
```

**Step traces.** `fruxon agents draft run` additionally emits
`{"type":"step_trace","id":"…","name":"…","step_type":"LlmStep",
"status":"succeeded","duration_ms":1234}` when each flow step
finishes — useful for CI gates that need per-step cost attribution.

On failure, a single `{"type":"error","message":"…","code":"…"?}`
record is emitted before exit. The schema_version field on `start`
is the parser-pinning point: bump = breaking shape change.

### `agents sandbox stream` — a second NDJSON stream (network testing)

`fruxon agents sandbox stream <session>` follows a *sandbox* run (one
opened with `agents sandbox open`, driven by `turn` / `fire`). It's a
different event taxonomy from `draft run` — it reports the agent's
network behavior, not token-by-token text:

```json
{"type":"start","schema_version":1,"stream":"sandbox","session":"s_abc"}
{"type":"tool_call","toolName":"search","toolCallId":"tc-1","argsSummary":"…"}
{"type":"tool_result","outcome":"completed","resultSummary":"…"}
{"type":"pending_consult","advisor":"finance","question":"…","operationId":"op_1","advisorIsAgent":true}
{"type":"reply","text":"Your refund is processed.","at":1719158400000}
{"type":"turn_complete","outcome":"replied"}
{"type":"stopped"}
```

It runs until `turn_complete` (outcome `replied` / `silent` /
`suspended` / `failed`), then exits 0 — a parked run emits
`turn_complete` with outcome `suspended`. Resolve the gate
**out-of-band**: `agents sandbox answer <session> <operationId>` for a
`pending_consult`, `agents approvals respond` for a `pending_approval`
(it carries `requestId`), then re-run `stream` to see the resumed
reply. `blocked` frames report real sends the sandbox prevented — assert
on them for "no-leak" tests. `typing` / `status` liveness frames are
dropped in agent mode.

`agents sandbox fork` returns both `resendText` and `prefillText`. If you
send the customer's message yourself, send `resendText`: the platform
frames every inbound turn, so `prefillText` would reach the agent framed
twice. (`fork --send` does this for you.)

### `agents sandbox test` — one verdict, not a stream

To *assert* network behavior rather than watch it, write a scenario file and
run `fruxon agents sandbox test <file-or-dir>`. It drives the sandbox for you
(steps + scripted `responders` for the gates) and returns a single JSON
verdict — no stream to parse:

```json
{"passed": false, "total": 1, "passed_count": 0,
 "results": [{"name": "refund-flow", "agent": "support-bot", "passed": false,
   "assertions": [{"kind": "reply_contains", "passed": true, "detail": ""},
                  {"kind": "no_blocked", "passed": false, "detail": "expected no blocked sends, got ['telegram:123']"}],
   "failures": ["expected no blocked sends, got ['telegram:123']"], "transcript": [/* frames */]}]}
```

Exit **0** = all scenarios passed, **1** = an assertion failed (fix the
agent), **12** = a malformed scenario file, **10–15** = couldn't run
(auth/network — fix the setup). `--junit <file>` writes a JUnit report for CI.
This is the agent-authored e2e gate: write the file, run one command, branch on
`passed`.

### Draft state and `tests watch`

Every read command emits a parseable shape; every write command echoes
the server's response so you don't need a follow-up GET. Highlights:

- `fruxon agents draft status` — booleans `local_edits` and
  `needs_reconcile` for direct branching ("if local_edits: push", "if
  needs_reconcile: pull").
- `fruxon agents draft pull` — `source` enum tells you whether you
  picked up in-progress edits (`existing_draft`) or seeded from a
  deployed body (`revision`). Seeding can fail with **12** on a legacy
  multi-step revision that has no single definition to fork; nothing is
  written in that case, so there is no half-file to clean up.
- `fruxon agents draft push` — echoes the post-write `version`, usable
  as the next `If-Match` without re-fetching.
- `fruxon agents tests watch` — long-lived NDJSON stream:
  `{"type":"start"}` → `{"type":"stream_live"}` → `{"type":"event",...}*`
  → `{"type":"stopped"}` on Ctrl-C.

## When to load the task guides

The `done` record of a run carries a `record_id`; reading what that run
did is `fruxon-debug-trace`'s job. For the rest:

- **fruxon-build-agent** — authoring loop (draft pull / edit / push /
  test / evaluate / deploy).
- **fruxon-create-integration** — bootstrap a new integration with API
  or Python tools.
- **fruxon-use-integrations** — wire existing tools into an agent.
- **fruxon-debug-trace** — read an execution trace to explain a run
  that failed, hung, or quietly did the wrong thing.

Each assumes the contract documented here: JSON by default, typed exit
codes, and the error envelope.
