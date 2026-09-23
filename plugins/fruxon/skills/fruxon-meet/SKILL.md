---
name: fruxon-meet
displayName: Meet Fruxon
description: >
  Orientation to Fruxon — what an agent / revision / definition / integration is,
  and the fruxon CLI's main entry points. Load when starting any task that
  involves authoring or operating Fruxon agents.
---

You are now operating with knowledge of how Fruxon works.

## The core nouns
- **Agent** — a named workflow. Identified by a lowercase-snake id
  (e.g. `research_assistant`). Has metadata and a current deployed revision.
- **Revision** — an immutable snapshot of an agent's behavior: its
  definition, parameter schema, integration slots, assets, contacts.
  You create a new revision to change behavior, then deploy it.
- **Definition** — what the agent does: its provider and model, its
  prompts, the tools it may call, and the capability configs (memory,
  knowledge base, consult, escalation, judge, …). An agent is a single
  definition, not a graph — there are no steps or edges to author.
  Its inputs are declared alongside it in `parametersMetadata`.
- **Application** — the container that owns agents and workflows.
  Every agent belongs to exactly one, and `agents create` requires it.
- **Contact** — a named human the agent can reach (notify / ask /
  escalate). The definition declares it in `slots`; a *binding* outside
  the revision says who actually receives — a participant, a roster
  role, or the operator queue. Declared but unbound = the reach-out
  dead-ends at run time; bound to a role nobody holds = the same
  dead-end, wearing a green badge (`fruxon applications roles`).
- **Integration** — a connection to a third-party service (Slack,
  GitHub, Jira, …) carrying credentials. **Tools** are the operations
  that integration exposes; agents pin them per-revision.

## The CLI surface — main entry points
```
fruxon describe                        # whole CLI tree as JSON (for AI agents)
fruxon examples [topic]                # curated runnable snippets
fruxon agents list / get / create --application <app>
fruxon agents schema <agent>           # typed parameter metadata
fruxon agents validate <agent> -p k=v  # pre-flight a payload (no execution)
fruxon agents revisions create [--deploy] / deploy / get [--as-draft]
fruxon agents draft pull / push / status / run / evaluate / undo / redo / reset / discard
fruxon agents draft schema             # the draft-body (AgentDraftPayload) JSON Schema — author against it
fruxon agents draft validate <id>      # lint the definition locally, before push
fruxon agents draft run <id> -p key=value  # execute the draft (CLI's one run surface)
fruxon agents check <agent>            # audit a deployed agent is wired to run end-to-end (trigger/roster/contacts/refs)
fruxon agents slots list/bind/unbind <agent>  # contacts — the humans notify/ask/escalate reach
fruxon agents executions list <agent>  # past executions, newest-first (find a record id)
fruxon agents executions get|trace|result <agent> <record-id>  # one execution: summary | steps | output
fruxon agents topics list <agent>      # the agent's conversation threads (--state/--participant)
fruxon agents topics messages <agent> <topic>  # the actual transcript of one conversation
fruxon agents topics sessions <agent> <topic>  # its episodes — why each one ended
fruxon agents inbox <agent>            # what the agent is paying attention to (focal/home topics)
fruxon agents approvals list <agent>   # pending human-in-the-loop approvals a run is blocked on
fruxon agents approvals respond <agent> <id> --approve|--reject  # answer the gate (needs --yes in agent mode)
fruxon agents memory list <agent> --subject <s>  # what the agent remembers (filter by subject/search/scope)
fruxon agents memory forget-subject <agent> <s>  # GDPR-forget a subject (needs --yes in agent mode)
fruxon agents sandbox open/turn/fire/stream/answer/close  # drive a network sandbox e2e (captures+blocks real sends)
fruxon agents sandbox fork <agent> <message-id> --send --draft  # replay a real bad reply against your draft, same history
fruxon agents sandbox test <file|dir>  # run scenario e2e tests of an agent (exit 0 pass / 1 fail; --junit)
fruxon integrations list / create
fruxon integrations authorize <integration>  # mint an OAuth connect link for a human to click (auto-detects the method)
fruxon integrations triggers <integration>  # event types (+ payload paths) an integration can fire an agent on
fruxon tools list <integration> / create
fruxon assets create/list/get/wait/delete  # the indexed RAG assets an agent's assetConfig attaches
fruxon assets search/documents/chunks <a>  # what the INDEX holds — distinct from the authored corpus below
fruxon knowledge-bases list / get / create / update  # the authored, reviewable corpus behind a manual_knowledge asset
fruxon knowledge-bases publish <kb>    # the step that makes authored knowledge findable; only PUBLISHED documents travel
fruxon knowledge-bases documents / document / add-document / edit-document <kb>  # the articles themselves
fruxon knowledge-bases review-queue / revisions / evidence <kb>  # what needs a human, who changed what, where it came from
fruxon knowledge-bases correct <kb> <doc> -i "what is wrong"  # let the editor agent fix it; it MAY decline, which writes nothing
fruxon knowledge-bases consolidate <kb>  # queue a report of near-duplicate clusters; a standalone pass NEVER merges
fruxon knowledge-bases apply <kb> <run> --cluster <id>  # merge the clusters you accepted from that report (--all for every one)
fruxon knowledge-bases source list / preview / sync / pause / resume <kb>  # the pipelines that write articles; a built source lands PAUSED
fruxon metrics list                    # evaluation-metric ids for an LLM judge (judge.rubric.metrics)
fruxon triggers list / create / bind / fire  # autonomy: fire agents on schedule/event (write surface)
fruxon triggers preview-shape / test-source <t>  # dry-run a work shape: what each stage sends, what the door lists (--count for how much, startFrom for the first after:, FILTERED for what door.skipWhen drops, and each record as door.projection will store it)
fruxon triggers ledger funnel / items / cursor <t>  # the work items an automation admitted, what it extracted, what it cost
fruxon triggers ledger passes <t>      # every time it fired: admitted / dispatched / completed / runs / cost per pass
fruxon triggers ledger redrive / ignore / settle <t> <item>  # act on a stuck item (--yes-gated)
fruxon triggers ledger redrive-many / ignore-many <t>  # the same over a selection (--id/--stage/--status, confirmed count)
fruxon triggers ledger exclusions <t>   # every reason items were set aside, with counts — the list --ignore-reason is picked from
fruxon triggers ledger redrive-many <t> --ignore-reason "<recorded reason>"  # undo the exclusions one revised instruction made
fruxon triggers ledger batches <t> --open-only  # what it is waiting on a human for; read `delivery` — UNDELIVERABLE means nobody was asked
fruxon triggers set-stages <t> --file + triggers revisions list / restore  # edit a work shape, and undo it
fruxon participants list / create / enable / disable / delete  # agent-network participants (--yes-gated delete)
fruxon applications list / get / roles # the container that owns agents; `roles` = who holds each roster role
fruxon applications entry-points list [<app>]  # how inbound reaches an agent; no <app> = every claimed address
fruxon applications entry-points connect/attach/move/detach <app>  # wire a doorway (connect prints the webhook URL once)
fruxon environments list / get / create / update / archive  # end-customer environments (slugs runs attribute to)
fruxon capabilities list / create / update / delete  # consult-routing vocabulary
fruxon participants bind / roster <p> <agent> + fruxon agents roster <agent>  # consult wiring
fruxon consult-pins list / create / delete  # deterministic capability→participant overrides
fruxon guides list / show <id>         # this catalog — CLI playbooks
fruxon skills list / show <id>         # product skills attached to agents
fruxon completion {bash|zsh|fish}      # shell completion script
```

## The schema-first principle
Two layers of "schema" — use the right one for the job:

- **Request-body schema** — for write commands taking `--file` (`agents
  create`, `revisions create`, `integrations create`, …), pass `--schema`
  to print the JSON Schema for the body, sourced from the live OpenAPI
  spec. Use before authoring a body.
- **Agent parameter schema** — for the parameters a deployed agent
  expects, run `fruxon agents schema <agent>`. Returns names, types,
  required flags, single-select options, defaults. Use before
  constructing a `fruxon agents draft run` payload, and pair with `fruxon
  agents validate <agent> -p key=value` to pre-flight without burning an
  execution slot.

Don't guess; discover.

## When to load other Fruxon guides
Run `fruxon guides show <id>`:
- **fruxon-agent-mode** — the CLI's machine contract: typed exit
  codes, the error envelope, `--yes` guards, and the JSON / NDJSON
  output shapes. Load it when a command fails or refuses, or when you
  parse a stream.
- **fruxon-build-agent** — the build-an-agent loop end-to-end.
- **fruxon-create-integration** — bootstrapping a brand-new
  integration (with API or Python tools) from scratch.
- **fruxon-use-integrations** — wiring already-existing tools
  into an agent.
- **fruxon-debug-trace** — working out why a run did what it did,
  from its execution trace.

## Guides vs skills (don't conflate)
- **Guides** (`fruxon guides`) — local CLI-driver playbooks, shipped
  in the SDK wheel, no auth, no network. This file is one. They tell
  *you* (or an LLM) how to drive the CLI.
- **Skills** (`fruxon skills`) — a Fruxon *product* feature. A skill
  is a tenant-scoped resource (instructions + tools) that attaches to
  an agent revision so the agent loads it at execution time. Lives
  in the backend, browsable via `fruxon skills list`.
