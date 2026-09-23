---
name: fruxon-build-agent
displayName: Build a Fruxon Agent
description: >
  Author a working Fruxon agent revision end-to-end via the CLI: discover,
  draft, test, create, deploy. Load when the user says "build a Fruxon
  agent", "create a revision", or starts authoring agent JSON.
---

You are now operating as a Fruxon agent-build specialist.

> **A command failed or refused?** `fruxon-agent-mode` has the typed
> exit codes, the `{"error":…}` envelope, and the `--yes` guards, plus
> the NDJSON frames `draft run` emits.

## The build loop
A revision is immutable once created. The *draft* is the
mutable working copy you iterate on — the same one an open
studio tab edits. Author against the draft, then mint a
revision from it.

1. **Discover** what's available:
   - `fruxon describe` — full CLI surface as JSON (the right entry
     point for an AI-agent driver — covers commands, flags, types,
     and curated examples in one call)
   - `fruxon applications list` — the Application that will own the
     agent. Every agent belongs to exactly one and `agents create`
     requires its id (`networkId`); the workspace default is used when
     you don't pass `--application`.
   - `fruxon integrations list` — the integration catalog. Filters:
     `--has-configs` (only *connected* ones — what you can actually
     wire today), `--has-triggers` (declares a trigger),
     `--has-channels` (messaging-capable: Slack/Telegram/Twilio/…),
     plus `--query` / `--type` / `--tag`.
   - `fruxon integrations configs list <integration>` — the tenant
     config ids for an integration; a published one is what a slot's
     `tenantConfigId` points at. None yet (the integration isn't
     connected)? For an OAuth integration, `fruxon integrations authorize
     <integration>` mints a consent URL — a human clicks it and the
     connection is saved as a config you can then pin.
   - `fruxon tools list <integration>` — see tools per integration;
     `fruxon tools get <integration> --tool <tool>` for a tool's parameters
   - `fruxon llm-providers list` — see providers + models
     (don't guess model names; they change)
   - `fruxon llm-providers configs list <provider>` — the tenant LLM
     config ids; pin a published one on a step via
     `provider.tenantConfigId`
   - `fruxon assets create --file ./docs.pdf -o id` — create a
     file-backed knowledge-base (RAG) asset from the CLI. Then run
     `fruxon assets wait <id>` before wiring it into a step; ingestion is
     async, and an asset is not searchable until its operation completes.
     `fruxon assets list` / `get <id>` show existing asset ids and
     queryable status for `assetConfig.assetIds`; `operations <id>` shows
     ingestion progress/history.
   - `fruxon metrics list` — evaluation-metric ids for an LLM judge.
     `definition.judge.rubric.metrics[]` is a list of `{metricId, weight}`
     (note the `rubric` level); the `id` column is the `metricId`,
     `defaultWeight` a good starting weight.
   - `fruxon secrets list` — secret ids/keys for the definition's
     `allowedSecretIds`. The `id` (a Guid) is what a step allow-lists; the
     `key` is the `{{secret.KEY}}` name a tool argument expands. The
     `published` column tells you whether it's resolvable yet (a draft
     isn't). Values are never shown — metadata only. `fruxon secrets grants
     <id>` lists which agents are authorized to expand it (the resolver
     refuses any agent not granted).
   - `fruxon agents slots list <agent>` — the agent's contacts and who
     each one reaches. The one place the declared-but-unbound gap shows
     up; `fruxon agents slots bind` closes it.
   - `fruxon participants list` — agent-network participant ids (people /
     groups / agents) the definition's `network` config, the consult
     roster, and a contact's `--participant` binding reference. Paginated
     (default `--limit 50`) — pass `--all` when populating a roster from a
     tenant that might have more than that, or the id list silently stops
     short. `fruxon triggers list` enumerates the scheduled / event
     sources that fire agents (these live outside the draft flow, so this
     is the only way to see them); `fruxon integrations triggers
     <integration>` lists the event *types* an integration can fire on —
     each descriptor's `id` is the `eventType` a `triggers create` body
     listens for (e.g. `gmail.message.received`), plus the `payloadFields`
     (dotted paths like `event.from` / `event.subject`) a binding's
     `parameterMappings` map onto the agent's entry params, so you wire an
     inbound-event trigger from real ids instead of guesses;
     `fruxon applications entry-points list <app>` shows how inbound
     actually reaches an agent — the Application's claim on each external
     address, and which deployment answers on it. (`fruxon agents channels
     list` / `agents endpoints` describe the same doorway one level down
     and are superseded by it.) All read-only.
2. **See the shape**: `fruxon agents draft schema` prints the JSON
   Schema for a draft body (`AgentDraftPayload`) — the exact file you
   edit, with the full tool / capability closure inlined. Read it before
   authoring JSON by hand. (`fruxon agents revisions create <agent>
   --schema` prints the same type — a draft and a revision take the
   identical body. `fruxon agents schema <agent>` is a different thing:
   the typed *run-time parameters* a deployed agent accepts.)
3. **Get a working copy**: `fruxon agents draft pull <agent>` writes
   the agent's draft to `<agent>.draft.json`. If no draft exists yet
   it is seeded from the deployed revision — so you edit a real body,
   not a blank page. Either way the file is a postable `AgentDraftPayload`
   (a `definition`, not a step graph), so `push` takes it back unchanged.
   (A brand-new agent with no revision has nothing to fork — see
   "Brand-new agent: the bootstrap" below.)
4. **Author / edit** that JSON file — by hand or with a coding agent —
   then **lint it locally**: `fruxon agents draft validate <agent>`
   checks the body with no server round-trip (a `definition` is present,
   slot ids are GUIDs, built-ins on `provider.builtInTools` not `tools`,
   every integration tool resolvable to a slot, `provider.tenantConfigId`
   is pinned, `parametersMetadata` is top-level and spelled right). It
   reports *every* finding in one pass (each with a stable `code`) and
   exits 12 if any — fix them before you push. Most of the "Common pitfalls" below are
   caught here. Add **`--online`** to also resolve references against the
   live catalog (one round-trip per referenced provider/integration, plus
   assets and secrets if used): does the pinned LLM config exist and is it
   published, is the model real for that provider, does a slot's
   `tenantConfigId` resolve, is a tool id real, is a referenced asset
   embedded/queryable, and does each `allowedSecretIds` secret exist + is it
   published + is this agent granted it (else the resolver refuses it) —
   the referential traps that otherwise deploy clean then fail (or return
   nothing) at run. Worth running once right before `revisions create`.
5. **Sync the draft**: `fruxon agents draft push <agent>` saves your
   edits to the server-side draft. It is visible in an open studio
   within ~1s, and reversible with `fruxon agents draft undo`.
6. **Test**: `fruxon agents draft run <agent> --file <agent>.draft.json -p k=v`
   runs the body like a normal run. The execution IS persisted, but
   stamped with `Origin=TEST` so it never mixes with production
   metrics (see "Origins" below). In agent mode this emits NDJSON
   (one event per line on stdout).
7. **Publish**: `fruxon agents revisions create <agent> --file <agent>.draft.json --deploy`
   mints the immutable revision and deploys it.
8. **Audit the wiring**: `fruxon agents check <agent>` — a deployed agent
   spans more than its definition. `draft validate` proves the body is
   sound; `check` proves the agent can actually *run*: it has a deployed
   revision, an **inbound path** (a bound trigger, a channel binding, or an
   active entry point it answers on its Application — without one the agent
   only runs via manual test / the SDK), a non-empty **consult
   roster** if it sets `network.enabled` (else a consult dead-ends),
   **approver slots** for any human-approval gate, a **binding** on every
   declared contact (declared-but-unbound reach-outs dead-end), that every bound trigger
   **populates the agent's required params** (an unmapped required param
   fails the run at fire time) and references a real `eventType`, and that
   the deployed revision's **references resolve** (slot configs published,
   model real, tool ids valid). These live *outside* the body, so a clean
   `validate` can still leave the agent inert. `check` exits non-zero only
   on a hard failure (no revision); the rest are warnings. (`draft validate
   --online` also surfaces the `consult_unwired` / `approver_slot_undeclared`
   warnings pre-deploy.)
9. **Clean up**: `fruxon agents draft discard <agent> --yes` drops the
   working copy once it has been promoted to a revision.

Iterate with `fruxon agents draft status` (local vs server sync
state) and `draft undo` / `redo` / `reset` (server-side history).
Under agent mode, `draft status` emits booleans `local_edits` and
`needs_reconcile` you can branch on directly — "if local_edits:
push", "if needs_reconcile: pull". `draft status` is one-shot; for a
live signal when a studio tab or a sibling CLI session edits the same
draft, `fruxon agents draft watch <agent>` tails changes over SSE
(NDJSON in agent mode) so you know exactly when to `pull` — instead of
polling `status`.

### Brand-new agent: the bootstrap
`draft pull` forks a deployed revision, so a freshly `create`d agent
(revision 0) has nothing to pull. You don't need to — **`draft run
--file` and `draft push --file` work standalone**: they key the draft
on the agent's current revision (`0` when nothing is deployed) and the
server builds the plan straight from your file. So the loop is just:

```
fruxon applications list                                      # find the owning Application
fruxon agents create --file create.json --application <app>   # agent shell (no behavior)
# author body.json from the example below (definition + slots + bindings)
fruxon agents draft validate <id> --file body.json            # lint locally (no round-trip)
fruxon agents draft run <id> --file body.json -p key=value    # test it (Origin=TEST)
# edit body.json, re-run, repeat …
fruxon agents revisions create <id> --file body.json --deploy # publish when happy
```

`create.json` is a `CreateAgent` body — minimal shape:

```json
{
  "id": "release_digest",
  "displayName": "Release Digest",
  "description": "Summarizes recent commits into a digest.",
  "tags": ["digest"]
}
```

**Every agent is owned by an Application.** The server rejects a create
without one (`400 … "An Application is required."`). Pass
`--application <guid>` (from `fruxon applications list`) or set
`networkId` in the body; with neither, the CLI fills the workspace's
default Application when it has one.

**`tags` is required** — send a non-empty array (`["untagged"]` if you
have nothing better). The `create --schema` output currently marks it
`nullable`, but the server rejects a missing/empty `tags` with
`400 … "Tags field is required"`. `id` must match `^[a-z][a-z0-9_]+$`.
Leave `type` off — the server defaults it; don't set it at create.

`draft run --file` runs the body **without minting a revision**, so you
iterate freely before anything is published; the first run also writes
the local `<id>.draft.json` sidecar, so later `draft run` / `status` /
`push` work without flags. When the body is good,
`revisions create --deploy` mints the immutable revision and makes it
live. (Heads-up: the **first** revision becomes current on create even
without `--deploy` — harmless until the agent is wired to a
connector/trigger.)

## Running an agent to validate it (the run loop)

The CLI's one execution surface is `fruxon agents draft run` — it runs
the *draft* (Origin=TEST), which is exactly what you want while
building. Before running, learn what the agent accepts:

```
fruxon agents schema <agent>                # typed parameter metadata
fruxon agents validate <agent> -p user_query=… [-p ...]   # pre-flight
fruxon agents draft run <agent> -p user_query=… [-p ...]  # execute the draft
```

> **Brand-new agent (revision 0)?** `agents schema` and `agents
> validate` read the agent's *deployed* revision, so they return
> `12 — "<agent> has no deployed revision yet"` until you publish one.
> That's expected: during the from-scratch bootstrap **only `draft run
> --file` works** — it runs your local body directly and surfaces the
> same parameter errors at run time. `schema` / `validate` become your
> pre-flight loop *after* the first `revisions create --deploy`. (This
> is why agent creation and revision creation are two separate ops:
> `agents create` provisions the shell; the first revision is what
> gives it behavior and a schema to validate against.)

Production invocation of a *deployed* agent is not a CLI concern — call
it from your app via the SDK (`FruxonClient.stream` / `execute`).

> **Testing agent-*network* behavior?** `draft run` is one agent, one
> shot — it can't exercise consults, human-approval gates, trigger-fired
> runs, or multi-participant turns. For that, open a sandbox session:
> `fruxon agents sandbox open <agent>`, then `turn --as <participant>` /
> `fire --trigger <id>` (add `--await` so consult/approval gates suspend),
> `stream` to watch, and `answer` / `approvals respond` to resolve gates.
> The sandbox captures the reply and hard-blocks every real send, so you
> can assert end-to-end network behavior — including "nothing leaked to a
> real channel" — without messaging anyone. To make it a repeatable CI gate,
> write the interaction as a scenario file (`steps` + scripted `responders` +
> `expect` assertions) and run `fruxon agents sandbox test <file>` — one
> command, one pass/fail verdict (exit 0/1, `--junit` for CI). A scenario can
> also carry a `setup` block that provisions its own world — upload a knowledge
> `asset` (and `wait: queryable` for ingestion), create a `participant`, or
> `create` + deploy an `agent` — reference them as `${asset.catalog.id}` in the
> flow/turn, and the runner tears it all down afterwards (even on failure;
> `--keep` to inspect). That's how you prove retrieval with a planted canary
> fact end-to-end. Assertions are deterministic by default (`reply_contains` /
> `tool_called` / `no_blocked` / `outcome`); add `reply_judge: {metric,
> min_score}` for an opt-in **semantic** check that scores the reply against a
> tenant eval metric (by id / key / name). See `fruxon examples sandbox`.
>
> **Fixing a reply a real customer got?** Don't retype the conversation:
> `fruxon agents sandbox fork <agent> <message-id> --send --draft` copies the
> history the agent had at that turn into a sandbox session and re-sends the
> customer's message against your pushed draft — no publish needed. Writes are
> held for approval, because sandbox does not block integration writes.

`agents validate` runs the same checks the server applies (missing
required, unknown parameter, wrong type, invalid option value)
and surfaces every finding in one pass. Exits 12 on failure with a
structured `errors` list — fix all of them at once instead of one
per round-trip. See `fruxon-agent-mode` for the full contract.

## Origins: production vs test
Every execution is tagged with an **origin** at the moment it runs:

- **`PRODUCTION`** — real end-user traffic from a connector, the
  gateway, scheduled triggers, etc. The `:execute` path.
- **`TEST`** — your own development runs from `fruxon agents draft run`
  / `:streamTest` / the studio "Run test" button. Owner-scoped
  (you only ever see your own test rows; admins see the workspace-wide
  total).

The split runs all the way through the data layer — cost rollups,
execution lists, and budgets are filtered by origin server-side.
This means **test spend never accidentally trips the production
cap, and production cost dashboards aren't polluted by dev runs.**

Practical implications for the build loop:

- **See your test spend** on an agent you've been iterating on:
  ```
  fruxon agents tests cost <agent>            # all revisions
  fruxon agents tests cost <agent> -r 12      # one revision
  ```
- **List your test runs** (most-recent first) and inspect any one:
  ```
  fruxon agents tests list <agent>
  fruxon agents tests show <agent> <chat-id>
  fruxon agents tests watch <agent>           # SSE — live tail
  ```
- **Set a Test-bucket budget** so a runaway loop doesn't burn
  through the month's prod budget by mistake:
  ```
  fruxon agents budget set <agent> --amount 50 --origin TEST
  fruxon agents budget get <agent> --origin TEST
  ```
  Production and Test budgets are independent — `--origin TEST`
  caps only test runs; the default (or `--origin PRODUCTION`) caps
  only prod traffic. Test budgets are opt-in: no budget = uncapped
  test runs.
- **`draft evaluate`** (next section) accumulates Test-bucket spend
  too; check `tests cost` after a big eval to see where it landed.

When `--origin` is omitted from a command that accepts it, it
defaults to `PRODUCTION` — the safe default for monitoring.

## Eval against the draft (before deploy)
Before minting a revision, score the draft head against a golden
dataset:
```
fruxon agents draft evaluate <agent> --list-datasets    # pick one
fruxon agents draft evaluate <agent> --dataset <uuid>   # confirm + run
```
**Expensive — every dataset sample runs the full flow once** (LLM
tokens + integration calls). The CLI quotes the sample count and
asks for confirmation; in agent mode (`FRUXON_AGENT_MODE` /
`CLAUDECODE` / Codex / `CI`) it refuses to run without an explicit `--yes`. Returns an
evaluation run id immediately — poll
`GET .../agents/<agent>/evaluationRuns/<run-id>` for the verdict
(`score`, `deploymentRecommendation`, per-sample comparisons). The
draft snapshot is pinned at submit time, so further edits don't
invalidate the result.

## Body anatomy
**An agent is not a flow.** There are no steps, no edges, and no
ENTRY_POINT / EXIT_POINT to author — the server synthesizes the graph
on the way to storage. The body you write is an `AgentDraftPayload`:

- **`definition`** (required) — the agent itself: `provider`,
  `systemPrompt`, `userPrompt`, `tools` (integration tools),
  `provider.builtInTools` (provider-native tools), `maxToolLoops`, and
  the capability configs below.
- **`parametersMetadata`** — the agent's declared inputs
  (`[ParameterMetadata, ...]`), **top-level**, not inside `definition`.
  This is where the old ENTRY_POINT step's parameters moved to.
- **`integrationSlots` / `integrationBindings`** — the credentials the
  tools resolve through (see "Wiring integrations" below).
- **`assets`** — the indexed assets attached to the revision. An *asset* is
  what gets searched; a **knowledge base** is the authored corpus behind a
  `manual_knowledge` one, and they are two ids for two things. `assetConfig`
  takes the asset id (`fruxon knowledge-bases get <kb>` prints it as
  `backingAssetId`). Authoring, reviewing and publishing that corpus is
  `fruxon knowledge-bases` — and nothing written there is searchable until
  the base is published.
- **`slots`** — the contacts this agent can reach (see "Contacts"
  below). Declaring one is half the job; it also has to be bound.
- **`comment`** — the version note on the revision this becomes.

### Capability configs (all on `definition`)
Each is off by default. `fruxon agents draft schema` is authoritative
for their fields — this is the map of what exists:

| Config | What it turns on |
|---|---|
| `sessionConfig` | Conversation history across runs |
| `memoryConfig` | Persistent notes + memory tools |
| `assetConfig` | Retrieval over indexed assets — `assetIds` (a knowledge base's `backingAssetId` goes here) |
| `judge` | Post-run LLM quality check (`judge.rubric.metrics`) |
| `delegation` | `spawn_subtask` — fan work out to child runs |
| `network` | Consult / delegate to roster peers |
| `escalation` | `escalate_to_human` — hand the conversation to an operator |
| `pipelines` | `run_pipeline` — map a collection pipeline over a list (ids from `fruxon pipelines list`) |
| `asyncExecution` | Await-vs-background policy for async tools |
| `outputContract` | Constrain the output to JSON / a JSON schema |
| `dialogueProfile` | A second prompt + toolset for conversational runs |
| `allowedSecretIds` | Which tenant secrets `{{secret.NAME}}` may expand |

### Binding a collection pipeline
`pipelines.bindings[]` is an **allowlist**: `run_pipeline` refuses any
pipeline id the step does not name. Get the ids from the CLI rather than a
dashboard URL:

```
fruxon pipelines list -o id                        # every pipeline you can reach
fruxon pipelines list --application <application>  # only what that Application owns
fruxon pipelines get <id>                          # one pipeline's reusable source ids

# Both halves of a binding in one call — ids and their sources together:
fruxon pipelines list -o json | jq '.[] | {id, sourceIds: [.sourceRefs[].sourceId]}'
```

Each binding takes `pipelineId`, and optionally `allowedSourceIds` — the
operator-sanctioned sources a bound agent may run against. A pipeline with
no reusable sources uses its embedded one and needs no `allowedSourceIds`
at all.

`fruxon agents draft schema` is authoritative for the binding's field
names; nothing validates a `pipelines` capability config locally, so a
wrong key is only caught server-side at revision-create.

### Migrating an older body
A body with `flow` / `steps` / `edges` is the previous contract and the
server rejects it. `draft validate` says so with a single
`legacy_flow_body` finding. To recover an existing agent's body:
`fruxon agents revisions get <agent> <n> --as-draft`. The endpoint itself
answers in the definition shape now, so the flag's job is trimming the
server-stamped fields a create would reject — it still collapses the older
flow shape if you point it at a cell serving one.

## Placeholders in prompts (PromptTemplate.template)
Double-brace `{{ expression }}`. Canonical forms:
- `{{param.x}}` — a declared input parameter (always use this prefix)
- `{{web_search('AI news')}}` — built-in tool call
- `{{slack.list_channels()}}` — integration tool call
- `{{a | b()}}` — pipe; b receives a's result
Bare names resolve too, but the prefixed forms are the canonical UI
output. An unresolved placeholder is a hard run-time error.

## Tools: built-in vs integration (the most-missed distinction)
- **Built-in tools** (provider-native: `web_search`,
  `code_interpreter`, `approval_request`) go on
  `definition.provider.builtInTools`, NOT `definition.tools`. Their
  `toolKey.integrationId` is empty string `""` and they don't carry
  an `integrationConfigId`.
- **Integration tools** (`slack.send_message`, `github.list_commits`)
  go on `definition.tools`. Their `toolKey.integrationId` is the
  integration id (`"slack"`). Credentials are never inline: a tool
  either pins `integrationConfigId` — **the `id` of an integration
  *slot*** the revision declares (see next section) — or omits it and
  inherits the agent-wide `integrationBindings` entry for its
  integration. Omitting is the common case; pin only when one
  integration has several slots and this tool needs a specific one.

## Contacts: who the agent can reach
A contact is the addressing indirection between the agent and a human —
what `notify`, `ask` and `escalate` target. It has two halves, authored
in different places, and they fail differently.

**Declare** it in the body's top-level `slots`:

```jsonc
"slots": [
  {
    "name": "ops_lead",                 // referenced by humanApproval.slotName
    "displayName": "Ops Lead",
    // Injected verbatim into the agent's contacts prompt block, so the
    // model can pick between contacts without you restating the routing
    // in the system prompt. Write it as an instruction.
    "description": "notify with the run summary when the batch finishes",
    "requiredKind": "ANY"               // ANY | PERSON | GROUP | AI_AGENT
  }
]
```

**Bind** it — outside the revision, so an operator can swap the human
without cutting a new one:

```
fruxon agents slots bind <agent> ops_lead --participant <guid>  # one person
fruxon agents slots bind <agent> ops_lead --role on_call        # whoever holds the roster role
fruxon agents slots bind <agent> ops_lead --queue               # the operator queue
```

`--role` uses the same selection `consult_for_role` does, so notify and
consult can't end up naming different humans. `--role` and `--queue`
resolve to a person, so a slot with `requiredKind` `GROUP` or `AI_AGENT`
only accepts `--participant`.

**A role binding takes any string.** The server trims it and stores it —
it never checks that anyone holds the role, so a typo binds cleanly and
then refuses at delivery time. `fruxon applications roles <app>` is the
projection that answers it: every role in the Application with its
holders and the contacts referencing it, and `--unheld-only` for the ones
that reach nobody. `slots bind --role` runs that check for you and warns
before writing (it still binds — wiring ahead of staffing a role is
legitimate).

> **The trap.** A declared contact with no binding validates clean and
> deploys clean, then dead-ends the first time the agent reaches out —
> there is nobody to deliver to. Nothing in the body can show you this,
> because the binding isn't in the body. `fruxon agents slots list
> <agent>` names the unbound ones, and `fruxon agents check <agent>`
> flags them.

Binding accepts a name declared on the current revision **or on any
draft**, so you can declare and bind in one session — the binding stays
inert until a revision declaring that name deploys.

## Wiring integrations: slots & bindings
An agent revision never embeds credentials. Instead it declares
**slots** that point at a tenant integration config, and tools
reference a slot by id. Three pieces, all at the top level of the
body (not inside `definition`):

1. **`integrationSlots`** — one entry per credential the agent uses:
   ```jsonc
   {
     "id": "<GUID>",                  // you generate this; tools reference it
     "integrationId": "github",       // must match the tenant config's integration
     "displayName": "GitHub",
     "tenantConfigId": "<tenant-config-GUID>"  // a PUBLISHED tenant config
   }
   ```
   The tenant config owns the parameters/auth/sandbox; the slot is a
   reference. At save the server checks the tenant config **exists**,
   **matches `integrationId`**, and **has a published revision** —
   otherwise the create is rejected.
2. **Each integration tool** on `definition.tools` either sets
   `integrationConfigId` to a **slot's `id`** (not the tenant config id),
   or omits the field and inherits the binding from step 3. A revision
   that declares exactly one slot per integration needs no explicit
   binding either — the server auto-binds a sole slot on create.
3. **`integrationBindings`** — `{ "<integrationId>": "<slotId>" }`, the
   agent-wide default slot for that integration. The binding key must
   equal the slot's `integrationId`.

Discovering the ids (the CLI can't guess them for you):
- `fruxon integrations configs list <integration>` → the tenant
  config ids + which are published. Use a published one as
  `tenantConfigId`.
- The slot `id` is a GUID **you** mint and reuse across the slot,
  every tool's `integrationConfigId`, and the binding value.

> Caveat: tool→slot referential integrity is only checked at **run**
> time, not at create. A typo'd `integrationConfigId` deploys fine,
> then fails the tool call with "auth ... not found". Keep the slot
> id identical everywhere.

## Providers and models
- `provider.providerId`: lowercase slug (`anthropic`, `openai`,
  `google`, `bedrock`, `grok`, `deepseek`).
- `provider.model`: discovered, not guessed
  (`fruxon llm-providers models <provider>`). Wrong model strings
  surface as "unsupported model 'X' for provider 'Y'" at create.
- **`definition.provider.tenantConfigId` is required.** It points at a
  published **tenant LLM config** that supplies the API key. Omit it and
  the run fails with `LLMProvider <x> is not configured` — even when the
  provider *is* configured. Discover ids with
  `fruxon llm-providers configs list <provider>` and pick a published
  one.

## Common pitfalls
`fruxon agents draft validate` catches most of these locally before a
push — run it every iteration; add `--online` and it also catches the
referential ones (unknown/unpublished config, wrong model, bad tool id).
What's left for the server: masked-secret resolution and run-time
semantics.
- **Enum casing is inconsistent** — check the `--schema` output for
  each enum's allowed values, don't assume one convention:
    - `AgentType`: UPPER_SNAKE — `CHAT`, `SUMMARIZATION`, …
    - `ExecutionMode`: UPPER_SNAKE — `PRODUCTION`, `SANDBOX`
    - **`SettingType`** (a parameter's `type`):
      UPPER_SNAKE, matching the C# member names — `STRING`,
      `INTEGER`, `FLOAT`, `BOOLEAN`, `OPTION`, `STRING_ARRAY`,
      `JSON`, `TOOL`, `ASSET`, `DICTIONARY`. Trust the `--schema`
      output, not the field's variable name.
- **Agent id**: `^[a-z][a-z0-9_]+$` — lowercase, underscores, no hyphens.
- **`agents create` without an Application**: `400 … "An Application is
  required."` Pass `--application` (`fruxon applications list`).
- **`agents create` without `tags`**: the `--schema` marks `tags`
  `nullable`, but the server requires a non-empty array — a missing
  `tags` fails with `400 … "Tags field is required"`. Always send one
  (e.g. `["untagged"]`).
- **Authoring a `flow` with steps and edges**: that's the previous
  contract; the server rejects it. One `definition` instead.
- **Declaring a contact and never binding it**: validates clean, deploys
  clean, dead-ends at the first reach-out. `fruxon agents slots list
  <agent>` names the unbound ones.
- **Binding a contact to a role nobody holds**: reports as bound and
  dead-ends exactly the same way. `fruxon applications roles <app>
  --unheld-only`; `agents check` flags it too.
- **Nesting `parametersMetadata` inside `definition`**: silently
  dropped — the agent then declares no inputs and every `{{param.x}}`
  dead-ends. It is top-level.
- **Putting `web_search` in `definition.tools`** instead of
  `definition.provider.builtInTools`: integration-tool resolution will
  fail at execution.
- **Single-brace `{x}` in prompts**: emitted literally; placeholders
  require double braces `{{ }}`.
- **Wrong key for entry-point parameters**: the schema field is
  `parametersMetadata`, not `parameters`. The old key is silently
  ignored — the agent then declares no inputs.
- **`draft push` reports a stale draft (HTTP 409)**: the draft
  moved on the server — an open studio, or another session. Your
  local file is untouched; `draft pull` to reconcile, then push.
- **Missing `provider.tenantConfigId` on an AGENT step**: run fails
  with `LLMProvider <x> is not configured`. Pin a published tenant
  LLM config id (see "Providers and models").
- **Integration tool `integrationConfigId` ≠ a slot id**: the tool
  call fails at run with an auth-not-found error. When present it must
  equal an `integrationSlots[].id` you declared. Omitting it is fine —
  except where the integration declares two or more slots and no
  binding picks one, which leaves nothing to inherit
  (`tool_config_unresolvable`).
- **Slot `id` must be a GUID**: a readable string like `"github_main"`
  is rejected at create (`could not be converted to System.Guid`).
  Mint a GUID and reuse it everywhere the slot is referenced.
- **The first revision auto-deploys**: creating revision 1 (even
  without `--deploy`) sets it as the agent's current revision. It's
  harmless until the agent is wired to a connector/trigger, but don't
  assume rev 1 is "draft-only". Subsequent revisions require an
  explicit `--deploy` (or `agents revisions deploy`).

## Server errors at create-time, by message
The pitfalls above are the ones `draft validate` catches. These arrive
as a 400/422 from the server, and the message is specific enough to fix
blind:

**"Tenant integration config(s) not found: …"** — a slot's
`tenantConfigId` doesn't exist. List the real ids with
`fruxon integrations configs list <integration>` and fix the slot.

**"Tenant integration config(s) have no published revision: …"** — the
config exists but was never published. Publish it, or point the slot at
one that is.

**"Tenant integration config integration mismatch: …"** — the slot's
`integrationId` and its tenant config's integration disagree (a `slack`
slot pointing at a `github` config). Align them.

**"Placeholder parameter value 'X' is not specified"** / **"Cannot
resolve parameter 'X'"** — a `{{param.X}}` doesn't resolve at run time.
`X` must be declared in the top-level `parametersMetadata` *and* passed
with `-p X=value`. If you nested `parametersMetadata` inside
`definition`, the server dropped it and every parameter reads as
undeclared — `draft validate` flags that as `parameters_in_definition`.

**"Tool unknown" / "no LLM tool registered for X"** — a provider-native
built-in landed on `definition.tools`. Move it to
`definition.provider.builtInTools`.

When the message doesn't localise the fault, two moves that do:

- **Diff against the schema.** Re-run `fruxon agents draft schema` and
  compare your body field by field for missing or extra keys — faster
  than bisecting a validation error by guesswork.
- **Strip to the core.** Cut the body to a provider and a prompt, with
  no tools and no capability configs; confirm that runs, then add each
  piece back until it breaks.

Once a run *starts* and then misbehaves, stop editing the body and read
what it did: `fruxon guides show fruxon-debug-trace`.

## Minimal working example shape
A complete, deployable body: one integration tool (wired through a
slot) plus a provider-native built-in. Replace every `<...>` with a
value discovered via the CLI. This is the `AgentDraftPayload` **at the
top level** — there is no `create` wrapper, and no `flow`.

```jsonc
{
  "comment": "Initial: GitHub commit digest",
  // The agent's declared inputs — TOP-LEVEL, not inside `definition`.
  // type is UPPER_SNAKE: STRING, INTEGER, FLOAT, BOOLEAN, OPTION,
  // JSON, STRING_ARRAY, TOOL, ASSET, DICTIONARY.
  "parametersMetadata": [
    {"name": "repo", "type": "STRING", "required": true,
     "description": "owner/name, e.g. fruxon-ai/fruxon-backend"},
    {"name": "depth", "type": "OPTION", "defaultValue": "summary",
     "options": [
       {"value": "summary", "label": "Summary"},
       {"value": "detailed", "label": "Detailed"}
     ]}
  ],
  // Declare the credential the agent uses.
  "integrationSlots": [
    {
      "id": "11111111-1111-1111-1111-111111111111",  // a GUID YOU mint
      "integrationId": "github",
      "displayName": "GitHub",
      // a PUBLISHED tenant config — `integrations configs list github`
      "tenantConfigId": "<tenant-config-GUID>"
    }
  ],
  // Agent-wide default slot per integration (key = slot's integrationId).
  "integrationBindings": { "github": "11111111-1111-1111-1111-111111111111" },
  // The agent itself.
  "definition": {
    "description": "Summarizes recent commits into a release digest.",
    "provider": {
      "providerId": "<provider>",            // e.g. openai, anthropic
      "model": "<discovered-model>",         // llm-providers models <provider>
      "tenantConfigId": "<llm-config-GUID>", // REQUIRED — llm-providers configs list <provider>
      "builtInTools": [
        {"toolKey": {"integrationId": "", "id": "web_search"}}
      ]
    },
    // Integration tool → integrationConfigId is the SLOT id above.
    "tools": [
      {"toolKey": {"integrationId": "github", "id": "list_commits"},
       "integrationConfigId": "11111111-1111-1111-1111-111111111111"}
    ],
    "systemPrompt": {"template": "You write concise release digests."},
    "userPrompt": {"template": "Digest {{param.repo}} ({{param.depth}})."},
    "maxToolLoops": 20
  }
}
```

For a pure-LLM agent with no external calls, drop `integrationSlots` /
`integrationBindings` / `definition.tools` and keep just the provider
(still with `tenantConfigId`).

Turning on a capability is one more key on `definition` — nothing else
moves:

```jsonc
"definition": {
  // …provider, prompts, tools as above…
  "assetConfig": {"enabled": true, "assetIds": ["<asset-id>"]},   // knowledge base
  "memoryConfig": {"enabled": true},                              // remembers across runs
  "network": {"enabled": true},                                   // may consult the roster
  "outputContract": {"format": "JSON"}                            // constrain the output
}
```

`fruxon agents draft schema` prints every field of every config —
read it rather than guessing shapes.
