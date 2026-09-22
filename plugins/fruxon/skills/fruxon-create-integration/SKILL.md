---
name: fruxon-create-integration
displayName: Create a New Fruxon Integration
description: >
  Bootstrap a brand-new integration (with API tools or Python code tools)
  end-to-end via the CLI: schema discovery, body authoring, tools, then a
  clean handoff to the user for credentials. Load when the user asks to
  add an integration; the flow first checks whether one already exists
  and only builds a new one if nothing suitable is found.
---

You are now operating as a Fruxon integration-bootstrapping specialist.

## Mental model: shape vs instance

Every integration has two layers:

- **Shape** — the integration definition + its tools. WHAT auth
  methods it supports, WHAT parameters the user fills in, WHAT
  tools it exposes. Authored via the CLI in this flow.
- **Instance (config)** — the actual secret values. API keys,
  OAuth grants, tenant ids. Entered by the user through the
  dashboard. NEVER author or paste secrets through the CLI.

Your job is the shape. The user does the instance. Make the
handoff smooth.

## Workflow

1. **Check what already exists FIRST.** Before building anything,
   confirm the platform doesn't already cover this. Don't rebuild
   an integration that's there, and don't create a duplicate slug:
   ```
   fruxon integrations list --query <keyword>
   fruxon integrations get <candidate-id>   # 404 = slug is free
   ```
   In agent mode these default to JSON, so the listing already
   carries each integration's `description` — enough to judge
   suitability without a per-item `get`. To see what an existing
   integration can already DO (before deciding it's missing a
   tool), enumerate its tools:
   ```
   fruxon tools list <candidate-id>   # JSON includes each tool's description
   ```
   If a matching integration already exists:
   - The user just wants to **use** it (wire its tools into an
     agent) → stop here and switch to the `fruxon-use-integrations`
     skill instead.
   - It exists but is **missing a tool** the user needs (confirmed
     via `tools list`) → don't re-create the integration; grab the
     tool schema from step 2, then author just the new tool against
     the existing `integrationId` (skip to step 5).
   Only proceed with a brand-new integration when nothing suitable
   exists.

2. **Discover the body shape.** Don't guess fields:
   ```
   fruxon integrations create --schema > integration.schema.json
   fruxon tools create <will-fill-in> --schema > tool.schema.json
   ```
   The schemas are the source of truth for required fields,
   types, and discriminated unions.

   For the wider CLI surface (every command, its flags, types,
   curated examples) run `fruxon describe` — designed for an
   AI-agent driver to consume in one call.

3. **Author `integration.json`.** Key fields:
   - `id` — kebab-case slug (`github`, `linear`, `posthog`).
   - `displayName` — what shows in the dashboard.
   - `configMetadata.authMetadata[]` — describe each auth
     method the user will supply via the UI:
     `{ id, displayName, parametersMetadata: [{name, displayName, secret: true}] }`.
     Mark secret fields with `"secret": true` so the dashboard
     masks them. Common shapes:
     - **API key**: one param, secret, displayName "API Key".
     - **Bearer token**: one param, secret, displayName "Access Token".
     - **OAuth (user)**: typically zero params here — the dashboard
       runs the consent flow.
   - `configMetadata.parametersMetadata[]` — NON-secret connection
     params (workspace id, region, base URL). Optional.

4. **Create the integration.**
   ```
   fruxon integrations create --file ./integration.json
   ```
   Note the handoff URL printed at the end — you'll reuse it
   when telling the user what to do.

5. **Author each tool as its own JSON file.** Two flavors.

   Both flavors share these top-level fields:
   - `id` — snake_case slug, unique within the integration.
   - `integrationId` — the CLI auto-fills this from the positional
     arg on `tools create <integration-id>`; you may omit it.
     If you do include it, it must match.
   - `actionType` — one of `READ_ONLY` (default for GET / pure
     functions), `REVERSIBLE` (write that can be undone), or
     `IRREVERSIBLE` (sends mail, charges money). Note: the enum
     is reversibility-flavored, NOT CRUD-flavored — there is no
     `WRITE`. Defaults to `READ_ONLY` when omitted.
   - `parametersMetadata[]` — inputs the agent passes when
     calling the tool. Each has `name`, `displayName`,
     `description`, and optional `required`, `secret`,
     `defaultValue`.

   ## Placeholders (CRITICAL)

   All templating uses **double curly braces**: `{{name}}` —
   NOT `{name}`. Single curlies are passed through literally
   and your tool will silently fail with the placeholder text
   embedded in the URL/header/body.

   Names are **flat** — there is no `auth.` / `config.` /
   `param.` prefix. All sources merge into one dict:
   - Tool call parameters (whatever the agent passes).
   - Integration config non-secret parameters (workspace id,
     region, base URL — declared in
     `configMetadata.parametersMetadata`).
   - Built-ins: `{{tenant}}` (the active tenant slug).

   Auth secrets are **NOT exposed as placeholders**. The
   auth provider injects the `Authorization` header (or
   query param) automatically based on the integration's
   `authMetadata.type`. DO NOT write `Authorization` in
   your tool's `headers`. Examples:
   - `BEARER_TOKEN` → adds `Authorization: Bearer <token>`.
   - `API_KEY` → adds the header configured in
     `authMetadata.authSettings` (e.g.
     `X-Api-Key: <key>`).
   - Custom prefix needed (Discord "Bot", G2 "Token token="):
     set `authSettings: { Scheme: "Bot", ValuePrefix: "" }`
     on the `authMetadata` — still no template needed in
     the tool.

   **API tool** (HTTP endpoint):
   ```json
   {
     "id": "list_repos",
     "displayName": "List repositories",
     "description": "List the authenticated user's repos.",
     "descriptor": {
       "apiTool": {
         "httpMethod": "GET",
         "url": "https://api.github.com/user/repos",
         "headers": { "Accept": "application/json" },
         "queryParameters": { "visibility": "{{visibility}}" },
         "resultType": "JSON"
       }
     },
     "parametersMetadata": [
       {"name": "visibility", "description": "all|public|private"}
     ]
   }
   ```
   Notice: no `Authorization` header — auth is automatic.
   `resultType` is one of `JSON`, `STRING`, `BOOLEAN`,
   `INTEGER`, `TOOL`. There is no `JSON_ARRAY` /
   `JSON_OBJECT` — `JSON` covers both.

   **Code tool** (Python, sandboxed):
   ```json
   {
     "id": "summarize_diff",
     "integrationId": "github",
     "displayName": "Summarize diff",
     "descriptor": {
       "codeTool": {
         "code": "result = diff[:200]",
         "timeoutSeconds": 30,
         "resultType": "STRING"
       }
     },
     "parametersMetadata": [{"name": "diff", "required": true}]
   }
   ```
   Parameters are injected as named Python variables at the
   top of the script — reference them directly (`diff` above,
   no `kwargs` dance). Assign to `result` to return data.
   Optional `packages: ["requests", ...]` installs PyPI deps
   into the sandbox; `timeoutSeconds` is 1–120 (default 60).

6. **Create each tool.**
   ```
   fruxon tools create <integration-id> --file ./list_repos.json
   ```

7. **Hand off to the user. This is the UX-critical step.**
   Compose a SHORT, FRIENDLY message that includes:
   - One line: what you built (integration + tool count).
   - One line: the dashboard link.
   - One line per auth method: what the user needs to paste.
   - The optional shortcut: `fruxon integrations open <id>`.

   Example:
   ```
   ✓ Created the `github` integration with 4 tools.

   Now connect your account — agents can't call the tools until
   this is done:
      → https://app.fruxon.io/integrations/github
        ↳ Paste a GitHub Personal Access Token (Bearer auth)

   Or run: fruxon integrations open github
   ```

   DO NOT ask the user for the secret in chat. DO NOT offer to
   put it in the JSON file. The dashboard is the only place
   secrets are accepted, by design.

## After the user connects

Once the user reports the config is set up, verify:
```
fruxon integrations configs list <integration-id>
fruxon integrations verify <integration-id>      # tests the auth
fruxon tools run <integration-id> --tool <tool-id> -c <config-uuid>   # end-to-end
```

## Optional: expose the integration as an MCP server

If the user wants to call these tools from Claude Desktop,
Cursor, or other MCP-capable clients, enable MCP via:
```
fruxon integrations configs list <integration-id>   # grab the configId
fruxon integrations mcp enable <integration-id> --config <config-id>
```

The server auto-mints a dedicated `mcp:invoke`-scoped key,
bound to this MCP only, and prints the raw secret EXACTLY
ONCE. Frame the handoff to the user as:

```
✓ MCP server enabled for `<integration-id>`.

Add to Claude Desktop config (`claude_desktop_config.json`):
   "fruxon-<integration-id>": {
     "url": "<callUrl from output>",
     "headers": { "Authorization": "Bearer <the secret printed above>" }
   }

The secret won't be shown again — copy it now.
If you lose it, rotate from the dashboard.
```

DO NOT use `fruxon integrations mcp enable` to "look at" the
state — that's `mcp status`. Enable is the one-shot mint;
save the output the first time. Rotation is dashboard-only on
purpose (audit + intentional secret-minting).

## Common pitfalls

- Hardcoding the secret in `apiTool.headers` instead of using a
  `{auth.token}` placeholder. The secret should never be in
  the integration definition; it lives in the config.
- Forgetting `"secret": true` on auth parameters — dashboard
  won't mask the input field.
- Authoring tools before the integration exists (server returns
  404 — order matters).
- Rebuilding an integration the platform already has. Run the
  existence check first (step 1) — `fruxon integrations list
  --query <keyword>` — and reuse/extend instead of duplicating.
- `id` collisions: both `integration.id` and `tool.id` are
  unique-per-tenant. If `fruxon integrations get <id>` returns
  404, the id is free. Otherwise pick a fresh slug.
- Skipping the dashboard handoff and instead writing the secret
  into the JSON. Don't. Even if the user offers it. The shape /
  instance separation is a security boundary, not a suggestion.
