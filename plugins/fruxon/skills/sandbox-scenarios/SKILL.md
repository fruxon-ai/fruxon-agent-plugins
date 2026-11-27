---
name: sandbox-scenarios
displayName: Write sandbox test scenarios
description: >
  The scenario file format `fruxon agents sandbox test` runs: top-level
  keys, the revision selector (deployed / draft / proposal), setup blocks
  (asset, participant, agent, seed) and ${ref} templating, turn and fire
  steps, gate responders, every expect assertion, the result shape, and
  the recipe for a throwaway tester the agent answers. Load when writing
  or fixing a scenario file, or when `sandbox test` exits 12.
---

A scenario is a small YAML or JSON file that drives an agent in a sandbox
session and asserts what happened. `fruxon agents sandbox test <file-or-dir>`
runs one file, or every `*.test.yaml` / `*.test.yml` / `*.test.json` in a
directory, and returns one verdict. Channel sends are blocked throughout.

Exit **0** = every scenario passed, **1** = an assertion failed, **12** = a
scenario file is malformed, **10–15** = couldn't run (auth, network, a
server error). The error contract is in `fruxon guides show fruxon-agent-mode`.

## Strict keys

Every level of a scenario file accepts only the keys listed below. An
unknown key anywhere — top level, a setup item, a step, a `turn` / `fire`
body, a responder or its `match`, an `expect` item or a `reply_judge` — is
exit 12. The message names each offending key by path and lists what that
level allows, all in one go:

```
unknown key 'draft' (allowed: name, agent, revision, proposal, timeout_s, setup, steps, responders, expect);
unknown key 'steps[0].turn.use_draft' (allowed: as, text, await, background, revision, proposal)
```

Nothing is provisioned and no session is opened before the file validates.

## Top level

```yaml
name: refund-flow            # optional; defaults to the file name
agent: support-bot           # required: an agent id, or ${agent.<ref>.id} from setup
revision: draft              # optional: deployed (default) | draft | proposal
proposal: 0f3c2a4e-…         # optional: an improvement card id (implies revision: proposal)
setup: []                    # optional: resources to create first, torn down after
steps: []                    # what to send, in order
responders: []               # scripted answers to consult / approval gates
expect: []                   # assertions over the whole run
timeout_s: 120               # accepted; not enforced by the runner yet
```

## Choosing the revision

Which code the steps run. Sent exactly as `agents sandbox turn` /
`agents sandbox fire` send `--draft` / `--proposal`.

| `revision` | Runs | Sent as |
| --- | --- | --- |
| `deployed` (default) | the agent's deployed revision | no `revisionPolicy` |
| `draft` | **your** unpublished draft (drafts are per user: the one belonging to the token's user) | `revisionPolicy: DRAFT` |
| `proposal` + `proposal: <card>` | an improvement card's change, applied in memory to the deployed revision | `revisionPolicy: PROPOSAL` + the card id |

- `proposal: <card>` on its own means `revision: proposal`. `revision:
  proposal` without a card id, or `proposal` beside `revision: draft` /
  `deployed`, is exit 12.
- **A numbered revision (`revision: 3`) is refused** (exit 12): the sandbox
  runs the deployed revision, your draft or a proposal, nothing else. To test
  an older revision, `fruxon agents draft pull <agent> --revision N`, `draft
  push`, and run with `revision: draft`.
- A `turn` or `fire` step may carry its own `revision` / `proposal`; that
  step runs it instead of the scenario's choice. A step with neither runs the
  scenario's.
- A `draft` run with no draft fails with the server's 400 (check with
  `fruxon agents draft status <agent>`). A `proposal` run is for agent
  admins, and fails when the card has no change waiting.

## Steps

Each step is a single-key mapping, `turn` or `fire`.

```yaml
steps:
  - turn:
      as: ${participant.tester.id}   # required: the participant speaking
      text: "Why was I charged twice?"
      await: true                    # optional: force consult / approval gates to suspend (so responders answer them)
      background: false              # optional: force async tools to run in the background instead
      revision: draft                # optional: this step only
  - fire:
      trigger: daily-digest          # required: a trigger bound to the agent
      sample_payload: {…}            # optional: the synthesized event body (integration-event triggers)
      set: {region: EU}              # optional: override resolved input parameters
      await: true
      proposal: 0f3c2a4e-…           # optional: this step only
```

A step ends on the run's terminal `turn_complete` (`replied`, `silent` or
`failed`). A `suspended` turn parks on a gate; the runner answers it from
`responders` and keeps listening for the resumed run.

## Responders

The first responder whose `on` and `match` fit a gate answers it. `times`
caps how often one fires. A gate no responder matches ends the scenario with
an `unhandled_consult` / `unhandled_approval` failure.

```yaml
responders:
  - on: consult                      # required: consult | approval
    match: {advisor: finance, "question~": "refund"}   # consult: advisor, question~ (regex)
    answer: "Approved up to $50."    # the reply sent back
    # decline: true                  # decline instead (answer becomes the reason)
    # run_advisor: true              # let the advisor agent answer for real
    times: 1
  - on: approval
    match: {tool: issue_refund, gate: tool, "message~": "refund"}   # approval: tool, gate, message~
    decision: approve                # approve (default) | reject
    reason: "over limit"             # sent with a reject
```

`match` values are case-insensitive substrings; keys ending in `~` are
regular expressions.

## Expect

Each item is a single-key mapping. Assertions read every frame of the run.

| Kind | Passes when |
| --- | --- |
| `reply~: <regex>` | the replies match the regex |
| `reply_contains: <text>` | the replies contain the text (case-insensitive) |
| `reply_equals: <text>` | the replies equal the text (trimmed) |
| `outcome: replied\|silent\|failed` | the last step ended that way |
| `consulted: [advisor…]` / `not_consulted` | each advisor was (not) consulted |
| `tool_called: [tool…]` / `tool_not_called` | the agent did (not) call each tool |
| `tool_refused: [tool…]` / `tool_not_refused` | each tool's result was (not) `refused` — a rejected or expired approval |
| `blocked: [target…]` | a send to each target was blocked by the sandbox |
| `no_blocked: true` | no send was blocked |
| `delegated: [advisor…]` | a `delegate_to_participant` call named each advisor |
| `reply_judge: {metric, min_score}` | an eval metric (id, key or name) scores the reply at least `min_score` |

## Setup — resources created first, deleted after

Each setup item is a single-key mapping naming its type, with a `ref`. Later
items, `agent`, and the steps reference what it created as
`${<type>.<ref>.<field>}` — `id` always, plus the fields below. Everything
except `seed` is **deleted after the run, even on failure**; `--keep` leaves
it for debugging.

```yaml
setup:
  - asset:                      # a knowledge asset, uploaded
      ref: catalog
      file: ./catalog.pdf       # required; relative to the scenario file
      name: Catalog             # optional
      vectorize: true           # default true
      application: <app id>     # default: the scenario agent's Application (required when setup creates the agent)
      wait: true                # wait for ingestion to finish
      timeout_s: 300            # how long to wait (default 300)
  - agent:                      # an agent + a revision, deployed
      ref: bot
      create: ./agent.json      # required: a CreateAgent body (may use ${refs})
      revision: ./rev.json      # required (or `draft:`): a CreateAgentRevision body
      deploy: true              # default true
                                # → ${agent.bot.id}, ${agent.bot.revision}
  - participant:                # a participant, inline body or from a file
      ref: tester
      displayName: Scenario tester
      kind: PERSON
      audience: INTERNAL
      agentIds: [support-bot]   # the agents that answer this participant
      addresses: []
      bind: support-bot         # optional: add to an agent's consult roster (one id or a list)
      # file: ./participant.json  — the body from a file instead; then only ref, file, bind are allowed
  - seed:                       # simulated data in a SIMULATED config's sandbox store
      ref: crm
      integration: hubspot
      config: <SIMULATED config id>
      reset: true               # clear the store first
      entities:                 # imported as written
        - {entityType: contact, entityId: c1, payload: {name: Ada}, scope: null}
      generate: {type: contact, prompt: "20 B2B contacts", count: 20, scope: null}
                                # → ${seed.crm.inserted}; not torn down (only sandbox runs read it)
```

An inline participant body takes the `participants create` fields: `kind`,
`audience`, `displayName`, `email`, `relatedAgentId`, `avatarFileId`,
`addresses`, `agentIds`, `consultAllowed`, `description`, `expertise`, `area`,
`bio`, `preferredLanguage`, `preferences`, `environmentId`, `accounts`,
`displayNameSource`, `bioSource`, `environmentSource`. Their values are the
server's to validate.

## A throwaway tester the agent answers

A sandbox turn needs a participant the agent answers. Sending as a real
person drags their real addresses and bindings into the test. Until a
built-in tester exists, create one in `setup` — bound to the agent, with no
addresses, so nothing can reach a real channel — and delete it afterwards:

```json
{
  "name": "greets-the-tester",
  "agent": "support-bot",
  "revision": "draft",
  "setup": [
    {"participant": {"ref": "tester", "displayName": "Scenario tester", "kind": "PERSON",
                     "audience": "INTERNAL", "agentIds": ["support-bot"], "addresses": []}}
  ],
  "steps": [{"turn": {"as": "${participant.tester.id}", "text": "Hi, who am I talking to?"}}],
  "expect": [{"outcome": "replied"}, {"no_blocked": true}]
}
```

The tester is a real participant while the scenario runs (it shows in
`fruxon participants list`) and is deleted at the end; `--keep` leaves it.

## The result

`-o json` (the default in agent mode) prints one document on stdout:

```json
{"passed": true, "total": 1, "passed_count": 1,
 "results": [{"name": "greets-the-tester", "agent": "support-bot", "passed": true,
   "revisionPolicy": "DRAFT",
   "turns": [{"step": 1, "kind": "turn", "revisionPolicy": "DRAFT", "outcome": "replied",
              "executionRecordId": "8d1f…", "agentRevision": 7}],
   "assertions": [{"kind": "outcome", "passed": true, "detail": ""}],
   "failures": [], "error": null,
   "setup_refs": {"participant.tester": "p_…"}, "teardown_errors": [],
   "transcript": [/* frames, as `agents sandbox stream` prints them */]}]}
```

- `revisionPolicy` (+ `recommendationId` for a proposal) is the scenario's
  choice; each `turns` entry says what that step asked for, which run it
  ended with (`executionRecordId`, for `agents executions tree`) and the
  `agentRevision` that run executed, read from its execution record. Either
  is left out when the server did not name the run.
- `--junit <file>` writes the same per step as `<properties>` on each
  testcase: `revisionPolicy`, `step.N.revisionPolicy`,
  `step.N.agentRevision`, `step.N.executionRecordId`.
- `setup_refs` maps each `<type>.<ref>` to the id it created;
  `teardown_errors` lists anything teardown could not delete (it does not
  fail the scenario, but the resource is still there).
