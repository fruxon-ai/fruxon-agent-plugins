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
>
> **`--yes` is the human's confirmation, not yours.** A command shown here
> with `--yes` deletes, spends, sends, or changes something live: tell the
> human what it will do and add `--yes` only once they agree
> (`fruxon-agent-mode`, "Interactive guards").

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
     you don't pass `--application`. For a new one, `fruxon applications
     create --name <name> -o json` prints its `id` — create it before the
     agent, since an agent can't be moved into it from the CLI.
   - `fruxon integrations list` — the integration catalog. Filters:
     `--has-configs` (only *connected* ones — what you can actually
     wire today), `--has-triggers` (declares a trigger),
     `--has-channels` (messaging-capable: Slack/Telegram/Twilio/…),
     plus `--query` / `--type` / `--tag`.
   - `fruxon integrations configs list <integration>` — the tenant
     config ids for an integration; a published one is what a slot's
     `tenantConfigId` points at. None yet (the integration isn't
     connected)? `fruxon integrations connect <integration>` creates the
     config and prints a link: give it to the user, who signs in to Fruxon
     and either types the credential (an API key, token, password, or a
     custom method's fields; Stripe, most REST APIs) on a Fruxon page, which tests it and publishes the config, or,
     for an OAuth integration (Gmail, Google Sheets…), signs in to the
     provider, and the account is connected and the config published
     (`--scope` for what to ask; `authorize` is the same for OAuth).
     Nothing is connected until they use the link. Never ask for the
     secret in chat. `-o json` gives `configId` (pin it once the user says it is
     filled) and `url`; `--param name=value` sets a required connection
     setting such as a subdomain, `--config <id>` fills an existing config.
     A messaging channel is connected the same way. For WhatsApp,
     `fruxon integrations connect whatsapp_cloud -o json`: the link's page
     runs Meta's signup instead of asking for a token (the user picks the
     number and sets its PIN; `pageNote` in the JSON says so), and
     publishes the config. Once the user says it is done, put the agent on
     the number with `fruxon applications entry-points connect <app>
     --config <configId> --agent <agent>`.
   - `fruxon tools list <integration>` — see tools per integration;
     `fruxon tools get <integration> --tool <tool>` for a tool's parameters
   - `fruxon llm-providers list` — see providers + models
     (don't guess model names; they change). A provider marked
     **hosted — no config needed** (surface `FRUXON_HOSTED`, e.g.
     `fruxon_managed_gemini`) runs on Fruxon's credential, billed to the
     workspace's token balance: omit `provider.tenantConfigId` and skip
     the next step.
   - `fruxon llm-providers configs list <provider>` — the tenant LLM
     config ids; pin a published one on the definition via
     `provider.tenantConfigId`. `vertex_ai_gemini` and `vertex_ai_maas`
     share `vertex_ai`'s credential: agents on them pin a `vertex_ai` config,
     which the list shows (its `providerId` reads `vertex_ai`), and a new
     one is created under `vertex_ai`. `configs test <provider> <id>` probes a
     config's credentials; `configs publish` ships a draft — and switches
     every agent already on that config, so it asks first (`--yes` under
     an agent driver). None for the provider yet? `fruxon llm-providers
     connect <provider>` creates the config and prints a link: give it to
     the user, who signs in and types the API key on a Fruxon page, which
     tests it with the provider and publishes the config. Never ask for the
     key in chat. `-o json` gives `configId` and `requestId`; pin the
     `configId` once `fruxon llm-providers link-status <provider>
     <configId> <requestId>` says `FILLED`. `--param name=value` sets a
     required setting (Bedrock's `region`, Vertex's `project_id` and
     `location`); `--config <id>` fills an existing config
   - `fruxon assets create --file ./docs.pdf --application <app> -o id` —
     create a file-backed knowledge-base (RAG) asset from the CLI. Every
     asset belongs to one Application: use the agent's (`fruxon agents get
     <agent>` shows it); a key bound to an Application may leave
     `--application` out. Then run
     `fruxon assets wait <id>` before wiring it into an agent; ingestion is
     async, and an asset is not searchable until its operation completes.
     `fruxon assets list` / `get <id>` show existing asset ids and
     queryable status for `assetConfig.assetIds`; `operations <id>` shows
     ingestion progress/history. To change an uploaded file's contents,
     `fruxon assets replace-file <id> --file ./new.md --yes --wait` keeps
     the id, so nothing needs re-attaching; don't delete and re-create.
   - `fruxon metrics list` — evaluation-metric ids for an LLM judge.
     `definition.judge.rubric.metrics[]` is a list of `{metricId, weight}`
     (note the `rubric` level); the `id` column is the `metricId`,
     `defaultWeight` a good starting weight.
   - `fruxon secrets list` — secret ids/keys for the definition's
     `allowedSecretIds`. The `id` (a Guid) is what the definition allow-lists; the
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
     short. `fruxon triggers list` enumerates the scheduled / event /
     webhook sources that fire agents (these live outside the draft, so this
     is the only way to see them); `fruxon integrations events
     <integration>` lists the event *types* an integration can fire on —
     each descriptor's `id` is the `eventType` a `triggers create` body
     listens for (e.g. `google_gmail.message.received`), plus the `payloadFields`
     (dotted paths like `payload.from` / `payload.message_attributes.subject`) a binding's
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
   (one `definition`), so `push` takes it back unchanged.
   (A brand-new agent with no revision has nothing to fork — see
   "Brand-new agent: the bootstrap" below.)
4. **Author / edit** that JSON file — by hand or with a coding agent —
   then **lint it locally**: `fruxon agents draft validate <agent>`
   checks the body with no server round-trip (a `definition` is present,
   slot ids are GUIDs, built-ins on `provider.builtInTools` not `tools`,
   every integration tool resolvable to a slot, `provider.tenantConfigId`
   is pinned, `parametersMetadata` is top-level and spelled right, every
   `prefetch` call within the platform's rules — see "Prefetch" below). It
   reports *every* finding in one pass (each with a stable `code`) and
   exits 12 if any — fix them before you push. Most of the "Common pitfalls" below are
   caught here. Add **`--online`** to also resolve references against the
   live catalog (one round-trip per referenced provider/integration, plus
   assets and secrets if used): does the pinned LLM config exist and is it
   published, is the model real for that provider, does a slot's
   `tenantConfigId` resolve, is a tool id real, is a referenced asset
   embedded/queryable, does each `allowedSecretIds` secret exist + is it
   published + is this agent granted it (else the resolver refuses it), and
   can each prefetched tool actually run before the model (its labels, its
   parameter names, its required parameters) —
   the referential traps that otherwise deploy clean then fail (or return
   nothing) at run. Worth running once right before `revisions create`.
   Writing or reworking the system prompt? Run
   `fruxon agents system-blocks <agent>` first, to see what the platform
   already adds around it — see "Platform blocks" below.
5. **Sync the draft**: `fruxon agents draft push <agent>` saves your
   edits to the server-side draft. It is visible in an open studio
   within ~1s, and reversible with `fruxon agents draft undo`.
6. **Test**: `fruxon agents draft run <agent> --file <agent>.draft.json -p k=v`
   runs the body like a normal run. The execution IS persisted, but
   stamped with `Origin=TEST` so it never mixes with production
   metrics (see "Origins" below). In agent mode this emits NDJSON
   (one event per line on stdout).
   **`--file` writes the server draft** — the server can only run its
   stored draft, and that draft is what `revisions create` publishes.
   The pulled file is pushed like `draft push`. To run any *other* body
   (a control, the previous revision, an A/B variant), pass
   `--restore` so the draft you're about to ship is put back after the
   run; without `--restore` or `--yes` the CLI refuses in agent mode.
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
   model real, tool ids valid, prefetched tools still prefetchable). These live *outside* the body, so a clean
   `validate` can still leave the agent inert. `check` exits non-zero only
   on a hard failure (no revision); the rest are warnings. (`draft validate
   --online` also surfaces the `consult_unwired` / `approver_slot_undeclared`
   warnings pre-deploy.)
9. **Clean up**: `fruxon agents draft discard <agent> --yes` drops the
   working copy once it has been promoted to a revision. Offer it; run it
   once the human agrees.

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
iterate freely before anything is published. It does save the body as
the agent's server draft; when nothing was pulled yet, the first run
also starts tracking `body.json` (sidecar `.fruxon/agents/<id>.meta.json`),
so later `draft run` / `status` / `push` work without flags. Once a file
is tracked, running a *different* file needs `--restore` (one-off) or
`--yes` (keep it in the draft). When the body is good,
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
> agent body or a turn, and the runner tears it all down afterwards (even on failure;
> `--keep` to inspect). That's how you prove retrieval with a planted canary
> fact end-to-end. Assertions are deterministic by default (`reply_contains` /
> `tool_called` / `no_blocked` / `outcome`); add `reply_judge: {metric,
> min_score}` for an opt-in **semantic** check that scores the reply against a
> tenant eval metric (by id / key / name). See `fruxon examples sandbox`.
>
> **Testing memory across sessions?** A sandbox session has no memory by
> default — nothing is recalled, writes are discarded. Open each session with
> `fruxon agents sandbox open <agent> --keep-memory`: it gets real memory in a
> separate sandbox realm that later `--keep-memory` sessions recall and live
> runs never see. Tell session A a fact and `close` it; open session B with
> `--keep-memory` and ask — the agent should recall. A session opened without
> the flag should not (your control). `fruxon agents memory list <agent>
> --realm SANDBOX` shows what was stored; `fruxon agents memory reset-sandbox
> <agent> --yes` gives the next test a clean slate.
>
> **Fixing a reply a real customer got?** Don't retype the conversation:
> `fruxon agents sandbox fork <agent> <message-id> --send --draft --wait` copies
> the history the agent had at that turn into a sandbox session, re-sends the
> customer's message against your pushed draft — no publish needed — and
> follows the turn until it ends. Writes are held for approval, because sandbox
> does not block integration writes. Prefer this to `agents draft run` for a
> conversational agent: a draft run is not a conversation, so the agent is not
> offered conversation tools such as `chat.stay_silent`, and a reply it gives
> there can be silence in the real chat.
>
> **Your own integration's tools answer `{simulated: true, fallback:
> "no_classification"}` in a sandbox turn?** A sandbox turn may not reach
> production on a tool's say-so. A tool your workspace wrote (custom, MCP
> import, code) is not trusted on its `READ_ONLY` label alone, and the
> config's `sandboxMode: NONE` doesn't change that. Such a call goes to the
> simulator, and with no classification for the tool the simulator only
> echoes the arguments back. To let a read run live against the real
> config, confirm it on the step's binding:
> `{"toolKey": {...}, "safeToRepeat": true}`. That works only on a tool
> labelled `READ_ONLY`, and not next to `humanApproval` or `repeatGuard`;
> `draft validate` checks it. Don't set it on a tool that changes
> anything: it also lets the call repeat on a retry.

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
- **Check and adjust the Test-bucket budget.** Every agent is created
  with enforced Test caps of $5 a day, $20 a week and $50 a month; a
  run is refused once any one is spent, and the daily one usually
  trips first during heavy iteration:
  ```
  fruxon agents budget list <agent>
  fruxon agents budget set <agent> --origin TEST --period WEEKLY --amount 60
  fruxon agents budget set <agent> --origin TEST --period DAILY --amount 20
  ```
  Production and Test budgets are independent — `--origin TEST`
  caps only test runs; the default (or `--origin PRODUCTION`) caps
  only prod traffic. `--period` defaults to `MONTHLY`. The windows
  stay ordered daily ≤ weekly ≤ monthly, so raise the longer one
  first. Caps reset at 00:00 UTC (weeks start Monday).
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
**Expensive — every dataset sample runs the draft agent once** (LLM
tokens + integration calls). The CLI quotes the sample count and
asks for confirmation; in agent mode (`FRUXON_AGENT_MODE` /
`CLAUDECODE` / Codex / `CI`) it refuses to run without an explicit `--yes`.
Tell the human the sample count and that each sample is a paid run, and
add `--yes` only once they agree. Returns an
evaluation run id immediately — wait for the verdict with
`fruxon agents evaluations get <agent> <run-id> --wait` (`score`,
`deploymentRecommendation`), and read each sample's comparison with
`fruxon agents evaluations samples <agent> <run-id>`. The
draft snapshot is pinned at submit time, so further edits don't
invalidate the result.

## Body anatomy
**An agent is one definition** — no steps or edges to author. The body
you write is an `AgentDraftPayload`:

- **`definition`** (required) — the agent itself: `provider`,
  `systemPrompt`, `userPrompt`, `tools` (integration tools),
  `provider.builtInTools` (provider-native tools), `maxToolLoops`, and
  the capability configs below.
- **`parametersMetadata`** — the agent's declared inputs
  (`[ParameterMetadata, ...]`), **top-level**, not inside `definition`.
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
| `delegation` | `spawn_subtask` / `spawn_subtasks` — fan work out to parallel copies of this agent (see "Parallel sub-tasks" below) |
| `network` | Legacy switch for consult / delegate — the tools now follow the bound peers (see "Delegation" below) |
| `escalation` | `escalate_to_human` — hand the conversation to an operator |
| `asyncExecution` | Await-vs-background policy for async tools |
| `outputContract` | Constrain the output to JSON / a JSON schema |
| `dialogueProfile` | A second prompt + toolset for conversational runs |
| `allowedSecretIds` | Which tenant secrets `{{secret.NAME}}` may expand |
| `skills` | Instruction packs the agent loads on demand via `activate_skill` (`[{skillId}]`; author with `fruxon skills create`) |
| `prefetch` | Up to 3 read-only tool calls made before the first model call of a conversation turn (see "Prefetch" below) |

### Escalation reaches a desk, not the agent
`escalation.enabled` lets the agent hand a conversation to a person — and
tell the customer it did. Who that person is lives outside the body: the
agent's Application has an **escalation desk** per channel (operator ladder
+ working-hours schedule). A desk with no operators reaches nobody while the
agent still says it handed off. Before relying on it:

```bash
fruxon escalations policy <agent>                      # empty ladder = nobody
fruxon escalations operators candidates --agent <agent>  # internal people who can be operators
fruxon escalations operators add <id> --agent <agent>  # a desk only takes the Application's operators
fruxon escalations set-policy <agent> --operator <id>  # staff the desk (Application-wide)
# no desk at all? make one and attach it ('other' = no-channel chats, or an entry point id):
fruxon escalations desks create --agent <agent> --name "Front desk" --operator <id> --attach other
fruxon agents check <agent>                            # "Escalation" row; draft validate --online warns too
```

**A sandbox escalation is a rehearsal.** In `agents sandbox turn` the desk
is resolved and the agent hears the outcome, but nobody is paged and nothing
reaches `fruxon escalations list` — the tool frames carry `"rehearsal": true`
and the text output says "escalation rehearsed". `escalations list
--include-rehearsals` lists them on servers that support it.

### Going live on a channel: webhook and strangers
A connected messaging channel answers only when two things outside the body
are right. The provider must know where to deliver: `entry-points connect`
registers the webhook for providers Fruxon can register itself (Telegram) and
reports `webhook.status` (`INSTALLED`, `ALREADY_INSTALLED`, `UNVERIFIED`,
`MANUAL_INSTALL_REQUIRED`, `FAILED`); if it is not installed, `fruxon
integrations configs webhook rotate <integration> <config> --yes` mints and
registers a fresh one. And a
channel on `REQUEST_ACCESS` (the default) holds every new sender until
someone approves them:

```bash
fruxon integrations configs webhook inspect telegram <config>   # registeredToThisConfig: false = nothing arrives
fruxon access-requests list --agent <agent>                    # who is waiting
fruxon access-requests approve <id>                            # let one in
fruxon applications update <app> --unknown-senders PROVISION   # or stop queueing new senders at all
fruxon agents check <agent>                                    # "Inbound path" fails with no webhook; "Unknown senders" warns
fruxon integrations configs health whatsapp_cloud <config>    # can the WhatsApp number send? exits 12 when not ("Channel health" row in agents check)
```

**Hours live in two places, for two things.** The agent's own opening
hours — what it tells customers ("we're open Sun–Thu 8–20") — belong in its
prompt or a knowledge-base article. A **working-hours schedule** governs only
the human hand-off: whether an escalation reaches an operator now or is
handled as after-hours. Create one and attach it to the desk:

```bash
fruxon working-hours create --name Clinic --tz Asia/Jerusalem \
    --hours "sun-thu 08:00-20:00" --hours "fri 08:00-13:00"
fruxon escalations set-policy <agent> --working-hours <schedule-id>
```

### Starting an agent on an integration event

An `INTEGRATION_EVENT` trigger runs the agent when an integration emits an
event: a Google Meet transcript is ready, a calendar event changed, a
Stripe payment succeeded. Every integration's events are a fixed catalog;
`eventType` must be one of them, and the server refuses anything else
(a guessed `google_meet.conference.ended` would otherwise never fire).

```bash
fruxon integrations events google_meet        # what it emits, needs, and its payload fields
fruxon integrations configs list google_meet  # the connection to listen on (integrationConfigId)
```

Google Meet emits `google_meet.transcript.ready` (a few minutes after a
transcribed meeting ends, once the transcript is readable) and
`google_meet.notes.ready` (a meeting with Gemini notes and no transcript).
There is no plain "meeting ended" event: an agent that follows up on a
meeting wants the transcript, and this fires when it can be read. Bind the
agent to both to cover every meeting once. For meetings scheduled in
Calendar (not created by Fruxon) the connection needs the "Read your
existing meetings" scope.

```json
{
  "kind": "INTEGRATION_EVENT",
  "displayName": "Meeting follow-up",
  "integrationId": "google_meet",
  "integrationConfigId": "<config id>",
  "eventType": "google_meet.transcript.ready",
  "filter": {
    "match": "ALL",
    "conditions": [
      {"path": "payload.message_attributes.duration_minutes", "operator": "GREATER_THAN", "value": "10"}
    ]
  },
  "bindings": [{
    "agentId": "meeting-follow-up",
    "parameterMappings": [
      {"parameterName": "conference_record", "kind": "PAYLOAD_PATH",
       "value": "payload.message_attributes.conference_record"},
      {"parameterName": "transcript_name", "kind": "PAYLOAD_PATH",
       "value": "payload.message_attributes.transcript_name"}
    ]
  }]
}
```

`fruxon triggers create --file meeting_follow_up.json --application <guid>`.
The agent then reads the transcript with the Meet tool
`meet_transcript_read` and the attendees with `meet_participant_list`,
passing `conference_record`.

Try it before a real meeting: `fruxon integrations events google_meet
--sample google_meet.transcript.ready > meet.json` writes a payload built
from the catalog's examples; pass it to `fruxon agents sandbox fire
<session> --trigger <trigger> --sample-payload meet.json`. The sample's
ids are examples, so a tool that reads the real transcript will not find
them: edit in a real `conference_record` to read a real meeting.

### Skills: what to move out of the prompt
A skill is loaded only when the model decides its description applies, so
anything that must hold on *every* run — red lines, routing, the order of
tool calls — stays in `systemPrompt`. Move the long per-case detail (one
procedure per team, say) into skills, and write each `description` as the
condition for loading it. Skill content is read live, not pinned to the
revision: `fruxon skills update` changes every agent using it on its next run.

### Migrating an older body
A body with `flow` / `steps` / `edges` is an older contract and the
server rejects it. `draft validate` says so with a single
`legacy_flow_body` finding. To recover an existing agent's body:
`fruxon agents revisions get <agent> <n> --as-draft`. The endpoint itself
answers with the definition, so the flag's job is trimming the
server-stamped fields a create would reject.

## Platform blocks: don't restate them
The model never sees `systemPrompt` alone. The platform adds blocks around
it — identity, `<knowledge_base>`, `<natural_silence>`,
`<escalate_to_human>`, `<who_you_are_talking_to>`,
`<looked_up_before_this_turn>` and more — each switched on by a setting or
by the kind of run. A prompt that restates one pays for it on every call
and drifts when the platform's wording changes.

- **Before writing or reworking a system prompt, see them** for this agent:

  ```
  fruxon agents system-blocks <agent>                             # the pulled draft, unpushed edits included
  fruxon agents system-blocks <agent> --run-kind all              # which kinds of run carry which block
  fruxon agents system-blocks <agent> --block escalate_to_human   # what a block already says
  ```

- **Don't restate a block.** If `<escalate_to_human>` already says when and
  how to hand over, the prompt says only what is particular to this agent.
- **Reference a block by its tag only when the prompt has to say something
  about it** ("treat `<who_you_are_talking_to>` as the account holder").
  Tags are what the platform keeps stable; a block's prose is not.
- **Never copy block text out of a trace.** Most of a trace's
  `systemInstructions` is platform blocks (`executions trace --show-system`
  labels them); pasted into the prompt, every one is sent twice.
- **To see whether the model follows an instruction**, a block's or the
  prompt's, ask it directly with no agent around it: `fruxon llm-providers
  configs complete <provider> <config> --model <model> --system @prompt.md
  -m '<a user turn>'` runs one completion on the config the agent pins and
  records nothing. The model samples, so run a case several times before
  judging it.
- **Before `push`, run `fruxon agents system-blocks <agent> --check`.** It
  exits 12 when the reference lint flags a tag the prompt names (renamed, or
  a block this agent never gets) or when the draft's plan can't be built.

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
  an `integrationConfigId`. Which ones exist depends on the provider:
  the managed Gemini provider (`fruxon_managed_gemini`, the wallet)
  offers exactly one, `google_search` —
  `{"toolKey": {"integrationId": "", "id": "google_search"}}`.
  It combines with function tools (integration tools, `code_executor`)
  on every current Gemini model (Gemini 3+). Servers that predate the
  F-038 fix refuse that mix; if a run fails saying built-in and
  function tools can't be combined, drop one side or move the search
  into its own step.
- **Fruxon's code tool, `code_executor` / `execute`** is *not* a
  provider built-in: it is a Fruxon tool, so it goes on
  `definition.tools` like an integration tool, with no
  `integrationConfigId` and no config to create:

  ```json
  { "toolKey": { "integrationId": "code_executor", "id": "execute" } }
  ```

  The model sees it as `code_executor__execute` and writes Python 3.12
  for it (`code`, plus optional `timeout_seconds` 1–120, `packages`,
  `files`, `output_files`; assign to `result` to return data). Each
  call runs in a fresh sandbox with **no network** and no credentials;
  it is `READ_ONLY`, so it fits under any action-type ceiling. Its one
  way out is the agent's own tools:

  ```python
  from fruxon import call_tool
  issues = call_tool("sentry__list_issues", organization_slug="acme", project_slug="checkout-api")
  result = len(issues.get("items", []))
  ```

  `call_tool` takes the model-facing name `<integrationId>__<toolId>`,
  passes every parameter as a string (lists and objects as JSON
  strings), and only reaches tools attached to **this** agent — a tool
  behind an approval gate, confirmation, repeat guard or pinned
  parameters is refused (the agent must call it directly). In a sandbox
  run those calls go through the simulated configs like any other.
- **Integration tools** (`slack.send_message`, `github.list_commits`)
  go on `definition.tools`. Their `toolKey.integrationId` is the
  integration id (`"slack"`). Credentials are never inline: a tool
  either pins `integrationConfigId` — **the `id` of an integration
  *slot*** the revision declares (see next section) — or omits it and
  inherits the agent-wide `integrationBindings` entry for its
  integration. Omitting is the common case; pin only when one
  integration has several slots and this tool needs a specific one.

## Prefetch: lookups before the first model call
`definition.prefetch` lists up to **3** read-only tool calls the platform
makes on a conversation's turn *before* the model's first call. The results
reach the model in its instructions, as a `<looked_up_before_this_turn>`
block, so it starts from the answer instead of spending a model call
(about five seconds) asking for it.

Use it for a lookup that needs no input from the model:

- **Who the customer is.** A lookup whose parameter is pinned on the
  binding (`phone_number` = `{{sender.address.texterchat}}`), with
  `minLetters: 0` so it runs on the first turn even if that's just "hi", and
  `keepForConversation: true` so later turns see the result without calling
  again. A kept result is capped at 4000 characters unless `maxResultChars`
  says otherwise.
- **A knowledge search on the customer's words.** `assets.search_assets`
  with `query` = `{{turn.message_text}}`. It needs no `tools[]` entry; it
  comes with `assetConfig.enabled`. Use it only when the prompt doesn't push
  the model to search again anyway. On 2026-10-04 a prompt that told the
  model to run several queries of its own made it ignore the prefetched
  search, so the call was pure cost.

```json
"definition": {
  "tools": [
    {
      "toolKey": {"integrationId": "restigo", "id": "get_users_by_phone"},
      "safeToRepeat": true,
      "pinnedParameters": [{"name": "phone_number", "value": "{{sender.address.texterchat}}"}]
    }
  ],
  "assetConfig": {"enabled": true, "assetIds": ["<asset id>"]},
  "prefetch": [
    {
      "toolKey": {"integrationId": "restigo", "id": "get_users_by_phone"},
      "arguments": {},
      "minLetters": 0,
      "keepForConversation": true,
      "maxResultChars": 2000
    },
    {
      "toolKey": {"integrationId": "assets", "id": "search_assets"},
      "arguments": {"query": "{{turn.message_text}}"}
    }
  ]
}
```

The rules. `draft validate` checks them; the ones marked *online* need
`--online`, because they read the tool's definition:

- The tool is one of `definition.tools`, because the call runs under that
  binding (its pins, config and credentials). The exception is
  `assets.search_assets` with `assetConfig.enabled`. Each tool at most once,
  at most 3 calls.
- The call must change nothing. No `humanApproval`, `repeatGuard` or
  `durableEffect` on the binding. *Online:* the tool is synchronous,
  labelled `READ_ONLY`, and trusted: a platform (`PREDEFINED`) or agent
  tool, or a tenant tool whose binding sets `safeToRepeat: true`.
- `arguments` is parameter name → template, at most 20. A template may use
  only `{{turn.message_text}}` (the customer's own words this turn),
  `{{sender.*}}` and `{{venue.*}}`. It can't use a run parameter or a
  secret. Don't set a parameter the binding pins. *Online:*
  every argument is a real parameter, and every required parameter is given
  or pinned.
- `minLetters` is 0–10000, default 15. The call waits for a turn whose
  customer text has that many letters, so a greeting or an emoji doesn't set
  it off. `maxResultChars` is 200–50000, or omitted.

When it runs: on a conversation turn only, not on an API, trigger or
workflow run, and not in a spawned subtask. Each call runs once per conversation, on
the first turn that passes `minLetters`, and is retried on the next one if it
failed. The calls share a 3-second budget; one that fails or runs over is
left out and the turn goes on. In the lab it runs only with **Confirm tool
writes** off: a turn that holds writes for confirmation shows what was kept
but runs nothing. Evaluation replays never run it.

`draft push` doesn't validate, and neither does the server's draft save, so
the lab can run a prefetch nothing has checked, and a call the runner
refuses is skipped without an error. Run `draft validate --online` before
you push. `fruxon agents check` re-checks a deployed revision's prefetched
tools, because a tool's label can change after the agent was saved.

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

## Delegation: one agent asks another
A lead agent can hand a question to another agent in the workspace — a
**peer** — and carry on with its answer (an incident responder asking a
log-analyst agent what the logs show). The peer stays its own agent and
answers with its **deployed** revision, so deploy it first.

**1. Make the peer a participant bound to the lead, on its consult
roster.** One `AI_AGENT` participant per peer:

```json
{
  "kind": "AI_AGENT",
  "displayName": "Log analyst",
  "relatedAgentId": "log-analyst",
  "agentIds": ["incident-responder"],
  "consultAllowed": true,
  "description": "Reads application logs and reports what failed, when, and how often.",
  "expertise": ["logs", "error rates"]
}
```

```bash
fruxon participants create -f log-analyst.json
fruxon agents roster incident-responder     # the peer must be listed, kind AI_AGENT
```

`relatedAgentId` is the peer, and `agentIds` binds it to the lead
(`[lead]`): for an `AI_AGENT` participant the binding alone puts the peer
on the lead's roster. `consultAllowed` is what matters for a *person*
advisor; on an AI peer it's ignored, so leaving it in is harmless.
Nothing checks `relatedAgentId`: a wrong id surfaces
only as `no_answer` at run time. `displayName`, `description` and
`expertise` are what the lead's model reads when it picks whom to ask.

**2. `definition.network.enabled`.** The tools follow the bound peers,
not this flag — a lead with a consult-allowed peer gets them either way.
Set `"network": {"enabled": true}` anyway: `fruxon agents check` and
`draft validate --online` use it to warn when the roster is empty.

**3. Say when to ask in the lead's prompt.** The lead gets `ask` (traced
as `system__ask`) and `delegate_to_participant`, plus a
`<consult_roster>` block listing its peers. `ask` takes `to` (the peer's
display name or `participant_id`) and a self-contained `question` — the
peer sees nothing else, not the conversation or the user.

**What happens at run time.** `ask` **suspends** the lead's run until the
peer answers; the reply comes back as the tool's result (`outcome`, and
the answer in `summary`; `no_answer` if the peer failed). Asks run
**sequentially**: two `ask`s in one turn run one peer after the other,
each picked up on a ~15 s cycle, so the lead waits for the sum. A peer
can't `ask` a third agent (depth 1). If the parts don't need to be
separate agents, use **parallel sub-tasks** instead (next section): two
independent investigations of one incident took about 10 minutes as two
sequential asks and under 90 seconds as one `spawn_subtasks` call.

**`delegate_to_participant` doesn't wait.** It returns `delegated` at
once; the peer answers on a side thread (it sees `question` and
`context_for_advisor`, not the conversation), and the lead runs again
with the answer and passes it on in its own voice. Use it when the user
shouldn't wait in silence; use `ask` when the lead needs the answer to
reply. At most 3 in flight per conversation; dropped if the conversation
has ended by the time the answer arrives.

**Conversations only.** Delegation runs end to end when the lead is
answering a conversation — a channel message, a chat, or a **sandbox
session**. A plain `:execute` run (`fruxon agents draft run`, the API, a
schedule or trigger with no conversation) doesn't reach the peer: the ask
waits until it expires. Test it in the sandbox:

```bash
S=$(fruxon agents sandbox open incident-responder -o id)
fruxon agents sandbox turn "$S" --as <your-participant-id> \
  --text "checkout-api error rate jumped to 8% at 14:05 UTC. What happened?" --await --wait
# --draft runs the lead's draft; the peer always runs its deployed revision.
# Resolve a pending ask yourself (the stream's pending_consult frame carries the operationId):
fruxon agents sandbox answer "$S" <operationId> --run-advisor --yes
```

Full reference: https://docs.fruxon.com/guides/agents/delegation/

## Parallel sub-tasks: one agent fans out
`definition.delegation` lets the agent split work into parts that run
**at the same time**:

```json
"delegation": { "enabled": true, "deadlineMinutes": 15, "allowNestedSpawn": false }
```

- The agent gets **`spawn_subtask`** (one part) and **`spawn_subtasks`**
  (a list of prompts in one call, one array of results back, in order).
  The platform also adds a prompt block telling it when to fan out.
- Each sub-task is a **copy of the same agent** — same revision (a
  sandbox draft run's sub-tasks run that draft), same integration tools —
  with **no conversation history**: its prompt is all it sees, so make
  each prompt self-contained and copy ids exactly. It can't `ask`,
  delegate, escalate or write memory. The copies run **in parallel**, as
  background runs, and the agent resumes when all have finished.
- **`deadlineMinutes`**: how long the agent waits for each sub-task before
  it counts as timed out. 30 by default, clamped to 1 minute–24 hours.
- **250** sub-tasks per run in total, across all batches. Width per call
  is your plan's concurrency limit: a wider `spawn_subtasks` is refused
  (`batch_too_wide`), not trimmed, so send long lists in batches.
- **`allowNestedSpawn`** (default `false`): a sub-task can't start
  sub-tasks of its own unless this is on (`nested_spawn_disabled`).
  Nesting stops at **depth 3** (`max_depth`).
- Needs a **queued** run: a conversation turn, a sandbox session, a
  schedule or a trigger. A synchronous API `:execute` call runs inline
  and the spawn tools refuse (`not_queued`).
- Sub-tasks can't target a different agent yet.

Tell the agent how to split, e.g. *"Start both investigations in ONE
`spawn_subtasks` call with two self-contained prompts (service, incident
time, symptom in each), then write the summary from both results."*

### Which one

| The job | Use |
|---|---|
| The same work over many items (each competitor, invoice, document) | Sub-tasks |
| Independent parts of one job, and the user is waiting | Sub-tasks |
| A specialist several agents reuse | Delegation (`ask`) |
| A peer with different guardrails, model or access the lead must not have | Delegation (`ask`) |
| A specialist with its own evaluations and revisions | Delegation (`ask`) |
| Hand a question to a specialist and keep talking to the user | Delegation (`delegate_to_participant`) |

You can't have separate specialist agents *and* parallel work in one job
today. Full guide: https://docs.fruxon.com/guides/agents/sub-agents/#choosing-for-a-real-job

## Simulate first: integrations with no credentials yet
You can build and exercise an agent's integration flow before anyone has
connected the real service. A config with `sandboxMode: SIMULATED` answers
every tool call a **sandbox** run makes from a simulated store; production
runs never read it.

```bash
# 1. A simulated config, published, no credentials (one step):
fruxon integrations configs create google_calendar --simulated -o json   # → id
# 2. Seed the store it answers from (or `sandbox import --file entities.json` — the entity
#    types, id templates and payload shapes it takes: `fruxon integrations configs sandbox schema google_calendar`):
fruxon integrations configs sandbox generate google_calendar <config> \
    --type event --count 15 --prompt "Clinic appointments next week, 20-minute slots, some gaps" \
    --context ./kb/services-and-hours.md   # facts the data must agree with (the agent's KB text)
fruxon integrations configs sandbox entities google_calendar <config> --type event
# 3. Pin it on the agent's slot (tenantConfigId = <config>), push the draft, then:
S=$(fruxon agents sandbox open <agent> -o id)
fruxon agents sandbox turn "$S" --as <participant> --text "Can I book Tuesday morning?"
```

**Seeding exact entities: get the `scope` right.** `sandbox import`
takes `{"entities": [{entityType, entityId, payload, scope?}]}`. The
`scope` is the values of the type's **scope params**, in the order
`sandbox schema` lists them, joined with `:` — `sandbox schema` prints
the shape as `scope key` (e.g. `{organization_slug}:{project_slug}`). A
type with no scope params takes no scope. The simulator builds the same
key from each tool call's parameters, so an entity imported under any
other scope is stored fine and never found:

```bash
fruxon integrations configs sandbox schema sentry --type issue
#   issue
#      scope      organization_slug, project_slug
#      scope key  {organization_slug}:{project_slug}
cat > sentry-seed.json <<'JSON'
{"entities": [
  {"entityType": "project", "scope": "acme", "entityId": "checkout-api",
   "payload": {"id": "1", "slug": "checkout-api", "organization": {"slug": "acme"}}},
  {"entityType": "issue", "scope": "acme:checkout-api", "entityId": "4821",
   "payload": {"id": "4821", "title": "TimeoutError: payment provider did not answer in 30s",
               "status": "unresolved", "project": {"slug": "checkout-api"}}}
]}
JSON
fruxon integrations configs sandbox import sentry <config> -f sentry-seed.json
fruxon integrations configs sandbox entities sentry <config> --type issue --scope acme:checkout-api
```

`sentry__list_issues` with `organization_slug=acme`,
`project_slug=checkout-api` now lists issue 4821. If the agent can't
find a seeded entity, compare its scope with the parameters in the tool
call's trace.

Writes the agent makes land in the store too, so the next turn sees them.
`sandbox snapshot --name …` saves a state and `sandbox restore` returns to
it; `sandbox reset --yes` empties it. Re-importing ids the store already
holds exits 13 naming them: reset first, or `sandbox import --mode upsert`
to overwrite them. In a scenario file (`agents sandbox
test`), a `seed` setup step does step 2 for you:

```yaml
setup:
  - seed: {ref: week, integration: google_calendar, config: <config>, reset: true,
           generate: {type: event, prompt: "a busy clinic week", count: 15}}
```

When the real credential arrives, `fruxon integrations connect
<integration> --config <config>` fills the same config and publishes it.

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
  `google`, `bedrock`, `grok`).
- `provider.model`: discovered, not guessed
  (`fruxon llm-providers models <provider>`). Wrong model strings
  surface as "unsupported model 'X' for provider 'Y'" at create.
- **`definition.provider.tenantConfigId` is required for every provider
  you bring a credential for** — all except the hosted ones (below). It
  points at a published **tenant LLM config** that supplies the API key.
  Omit it and the run fails with `LLMProvider <x> is not configured` — even
  when the provider *is* configured. Discover ids with
  `fruxon llm-providers configs list <provider>` and pick a published
  one; with none, `fruxon llm-providers connect <provider>` gets the
  user to fill one in through a link. `vertex_ai_gemini` and `vertex_ai_maas` share `vertex_ai`'s
  credential, so for them that is a `vertex_ai` config: their list
  includes it, and the server refuses to create a config under either.
- **Hosted providers take no config.** A provider whose surface is
  `FRUXON_HOSTED` — `llm-providers list` marks it *hosted — no config
  needed*; today `fruxon_managed_gemini`, Gemini run by Fruxon and billed
  to the workspace's token balance — has no credential and no config.
  Omit `tenantConfigId`; the server synthesises the config at run time.
  `llm-providers connect` refuses these providers, and `draft validate`
  accepts the omission.

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
- **Missing `provider.tenantConfigId` on the definition**: run fails
  with `LLMProvider <x> is not configured`. Pin a published tenant
  LLM config id (see "Providers and models"). Not for a hosted provider
  (`fruxon_managed_gemini`): it has no config, so leave the field out.
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
  assume rev 1 is "draft-only". `--deploy` on it is skipped (nothing to
  do). Subsequent revisions require an explicit `--deploy` (or `agents
  revisions deploy`), which needs the `revisions:deploy` scope — not in
  the default developer key. A 403 on the deploy step means: the revision
  exists but isn't live; have the human run `fruxon login --preset
  maintainer` (or deploy from the dashboard), then `agents revisions
  deploy <agent> <n>`.
- **The live revision is not always the newest**: after a rollback,
  newer revisions sit above the one that runs. `fruxon agents revisions
  list <agent>` marks the live one with ★, and `agents revisions deploys
  <agent>` shows who deployed what, when. Read both before building on
  `revisions get` with no number (or `--current`), which fetches the live
  revision. Every `revisions get` body leads with `isCurrent` and
  `currentRevision`, so a numbered read says whether it is the live one.

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
      "tenantConfigId": "<llm-config-GUID>", // llm-providers configs list <provider>; omit for a hosted provider
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
(still with `tenantConfigId`, unless the provider is hosted).

Turning on a capability is one more key on `definition` — nothing else
moves:

```jsonc
"definition": {
  // …provider, prompts, tools as above…
  "assetConfig": {"enabled": true, "assetIds": ["<asset-id>"]},   // knowledge base
  "memoryConfig": {"enabled": true},                              // remembers across runs
  "network": {"enabled": true},                                   // consult roster (tools follow bound peers)
  "outputContract": {"format": "JSON"}                            // constrain the output
}
```

`fruxon agents draft schema` prints every field of every config —
read it rather than guessing shapes.
