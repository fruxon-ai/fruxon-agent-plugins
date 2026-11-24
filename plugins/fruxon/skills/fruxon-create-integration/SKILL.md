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

> **`--yes` is the human's confirmation, not yours.** A command shown here
> with `--yes` deletes, spends, sends, or changes something live: tell the
> human what it will do and add `--yes` only once they agree
> (`fruxon-agent-mode`, "Interactive guards").

## Mental model: shape vs instance

Every integration has two layers:

- **Shape** — the integration definition + its tools. WHAT auth
  methods it supports, WHAT parameters the user fills in, WHAT
  tools it exposes. Authored via the CLI in this flow.
- **Instance (config)** — the actual secret values. API keys,
  OAuth grants, tenant ids. Entered by the user on a Fruxon page:
  the dashboard, or the page a credential link opens. NEVER author
  or paste secrets through the CLI.

Your job is the shape. The user does the instance. Make the
handoff smooth.

## Workflow

1. **Check what already exists FIRST.** Before building anything,
   confirm the platform doesn't already cover this. Don't rebuild
   an integration that's there, and don't create a duplicate slug:
   ```
   fruxon integrations list --query <keyword>
   fruxon integrations get custom_<slug>    # 404 = slug is free
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

   **Does the API publish an OpenAPI / Swagger spec?** (Try
   `/openapi.json`, `/swagger.json`, `/v3/api-docs`, or ask the
   user.) Then don't hand-write the tools — import them:
   ```
   fruxon integrations create --from-openapi https://api.acme.example/openapi.json --out ./acme
   ```
   It fetches the spec (URL, file, or `-`; JSON, or YAML with
   PyYAML installed — a spec on localhost works too, the CLI
   fetches it), parses it with the dashboard's importer, and
   writes `./acme/integration.json` + one `./acme/tools/<id>.json`
   per operation: `{{baseUrl}}` URL templates, path/query params,
   JSON body templates, `successStatusCodes` from the declared
   2xx responses, and `actionType` (`READ_ONLY` for GET,
   `REVERSIBLE` for PUT/PATCH, `IRREVERSIBLE` for POST/DELETE).
   Nothing is created yet. The integration id defaults to
   `custom_<slug of info.title>`; `--id custom_acme` overrides it.

   Then **review the folder** before creating anything:
   - Delete tool files the agent shouldn't have (admin, bulk
     delete, internal endpoints). Fewer tools = a better agent.
   - Check each `actionType`: a POST that only searches is
     `READ_ONLY`; a DELETE you can undo is `REVERSIBLE`.
   - Fill in what the printed notes ask for: auth methods that
     didn't map (HTTP bearer/basic map automatically; an API key
     or OAuth scheme must be added to
     `configMetadata.authMetadata` per step 3), and `baseUrl`'s
     `defaultValue` when the spec names no absolute server.
   - Give terse operations a `description`: the model picks
     tools by it.

   Then create the integration and every tool in one go:
   ```
   fruxon integrations create --from-dir ./acme
   ```
   Re-running it skips what already exists, so after fixing a
   tool file that failed, just run it again. Continue at step 7.

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
   - `id` — `custom_` followed by a snake_case slug (`custom_github`,
     `custom_acme_crm`). The prefix is required — the server rejects a
     custom integration id without it — and keeps custom ids from ever
     colliding with a built-in integration.
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
     - **OAuth app**: the customer's own OAuth app on their
       identity server, people signing in to it or the app
       signing in as itself. See **OAuth app auth** below.
     - **Sign-in token exchange**: the API has no key or static
       token — you POST a login and send back what it returns.
       The params here are the login the user types; the
       exchange is declared in `authSettings`. See **Token
       exchange auth** below.
     Add `"testPath"` to a method to make its credentials
     verifiable: a relative, side-effect-free GET under the
     `baseUrl` connection parameter (`"/me"`) that the server
     calls with the credentials the user supplied. Relative is
     enforced, so the probe can never leave the `baseUrl` host.
     Without one the credentials store unverified and
     `integrations verify` refuses the method — declare it
     wherever the API has a cheap identity endpoint. Valid for
     `API_KEY`, `BEARER_TOKEN`, `BASIC_AUTH`, and a `CUSTOM`
     method naming an `authProviderName` (the probe then runs
     that provider's own exchange, so a pass means a real tool
     call authenticates the same way).
   - `configMetadata.parametersMetadata[]` — NON-secret connection
     params (workspace id, region, base URL). Optional. A method
     with a `testPath` needs `baseUrl` here — that is what the
     probe path hangs off.

   ## No-credentials integration (code tools only)

   For code tools that only work on data the agent passes in —
   parsing, scoring, reshaping — there is nothing to authenticate.
   Declare no auth method at all:
   ```json
   {
     "id": "custom_incident_utils",
     "displayName": "Incident utils",
     "configMetadata": { "authMetadata": [] }
   }
   ```
   `"authMetadata": []` is the shape the server accepts. Don't
   add a method of `"type": "NONE"` — it is refused. Leave
   `testPath` out; there is nothing to probe.

   Such an integration **still needs a config** before an agent
   can use its tools: an agent binds a tool through a config, and
   with no credentials there is no link for the user to open.
   Create the config, then publish it once the user agrees:
   ```
   echo '{"displayName":"Default","parameters":{}}' \
     | fruxon integrations configs create custom_incident_utils --file - -o json   # note the configId
   fruxon integrations configs publish custom_incident_utils <config-id> --yes
   ```
   Publishing needs `--yes` in agent mode, and that is the user's
   confirmation, not yours: tell them the config makes the
   integration's tools usable by agents in the workspace, and add
   `--yes` only once they say yes. Skip the handoff in step 7 —
   there is nothing for the user to connect.

   ## Token exchange auth

   For an API whose auth is "POST a login, read a token out of
   the response, then send that token as a header" — no API key,
   no OAuth. Declare it; there is nothing to add to the backend.

   On the auth method set:
   - `"type": "CUSTOM"`
   - `"authProviderName": "token_exchange"` — the only provider
     name a custom integration may use.
   - `"userCredentialAuthType"` — the shape the user actually
     types and the platform stores: `BASIC_AUTH` (username +
     password), `API_KEY`, or `BEARER_TOKEN`. Required. The
     credential-entry page renders this, so you do NOT write
     `parametersMetadata` for it.
   - `"authSettings": { "parameters": { ... } }` — the exchange.

   The `authSettings.parameters` keys:
   - `login_path` — **relative** path under the `baseUrl`
     connection parameter, e.g. `"/jwtlogin"`. Relative is
     enforced on save and again on every exchange: an absolute
     URL is rejected, so a login can never be POSTed to a host
     other than the one the tools already call. `baseUrl` must
     be declared in `parametersMetadata`.
   - `login_method` — `POST` (default), `PUT` or `PATCH`.
   - `body_format` — `form` (default, form-urlencoded) or
     `json`.
   - `body.<field>` — one body field per key, each value a
     `{{placeholder}}` template. In `json` mode a dotted field
     name nests (`body.user.email`).
   - `login_header.<name>` — an extra header on the login
     request only, same templating.
   - `token_path` — dotted path to the token in the response,
     e.g. `"data.auth_token"`.
   - `header_name` (default `Authorization`), `header_scheme`
     (default `Bearer`; `"none"` sends the token as the whole
     header value) and `header_value_prefix` — how the token
     rides on every subsequent call.
   - A token lifetime, at least one of: `jwt_expiry: "true"`
     (read the `exp` claim out of the JWT), `lifetime_path`
     (a seconds-to-live field in the response, OAuth's
     `expires_in`), or `lifetime_seconds` (fixed). Plus
     `expiry_margin_seconds` (default 60) to re-sign-in that
     early. One is required — without it the login would run on
     every single tool call.
   - `rejected_status_codes` — statuses that mean the credential
     was refused rather than the endpoint failing. Default
     `401`.
   - `failure_path` / `failure_value` / `failure_message` — a
     field in a 200 response that means the login cannot
     succeed (a `otp_required: true` for an account with
     two-factor sign-in). `failure_message` is what the operator
     is shown, and is required when `failure_path` is set.

   Templates resolve the integration's connection parameters by
   their flat names, plus the stored credential under a
   `credential.` prefix: `{{credential.username}}`,
   `{{credential.password}}`, `{{credential.api_key}}`,
   `{{credential.token}}` — whichever the declared
   `userCredentialAuthType` offers. A template naming anything
   else is rejected on save. Never put a credential value in
   `authSettings` itself; it holds templates only.

   A full example — a management console that signs in with
   email and password and returns a long-lived JWT:
   ```json
   {
     "id": "console_login",
     "displayName": "Console login",
     "description": "Sign in with your console email and password.",
     "type": "CUSTOM",
     "authProviderName": "token_exchange",
     "userCredentialAuthType": "BASIC_AUTH",
     "testPath": "/branches",
     "authSettings": {
       "parameters": {
         "login_path": "/jwtlogin",
         "body_format": "form",
         "body.email": "{{credential.username}}",
         "body.password": "{{credential.password}}",
         "body.remember_me": "1",
         "token_path": "data.auth_token",
         "header_scheme": "Bearer",
         "jwt_expiry": "true",
         "expiry_margin_seconds": "3600",
         "failure_path": "data.otp_required",
         "failure_message": "This account uses a one-time code, which an unattended integration cannot complete."
       }
     }
   }
   ```

   The token is cached per credential until its margin, so the
   login runs once, not per call. `testPath` works here like
   anywhere else, and the probe runs this exchange — a pass
   means a real tool call signs in the same way.

   Your tools then declare NO `Authorization` header, exactly as
   for `BEARER_TOKEN` — see **Placeholders** below.

   ## OAuth app auth

   For an API behind the customer's own identity server (Auth0,
   Okta, Entra, Keycloak, …). On the auth method set
   `"type": "O_AUTH2"` and the app in
   `"authSettings": { "parameters": { ... } }`:
   - `grant_type` — who signs in:
     - `authorization_code` (the default): **people sign in**. A
       person connects an account in the dashboard (or through a
       credential link), and tools act as that account. Needs
       `authorization_url` and `token_url`. Keep `use_pkce:
       "true"`; with it the app may have no client secret.
     - `client_credentials`: **the app signs in as itself**. Fruxon
       gets a token with the client ID and secret whenever a tool
       runs; there is no account to connect, no credential link,
       and every person using the agent acts as the app. For
       server-to-server APIs. Needs `token_url`, `client_id` and
       `client_secret`, and is application level only.
   - `token_url`, `authorization_url` — https only.
   - `client_id`; `client_secret` — returned masked (`••••••••`)
     on every read, and sending the mask back keeps it.
   - `default_scopes` — a JSON list as a string:
     `"[\"openid\",\"email\"]"`.
   - `token_parameters` — extra fields on every token request,
     as a JSON object string: `"{\"audience\":\"https://api.acme.example\"}"`.
     They can't replace a field Fruxon sends itself
     (`grant_type`, `client_id`, `client_secret`, …).
   - `client_authentication` — `body` (default) or `basic`.
   - `authorization_parameters`, `revocation_url`, `use_pkce` —
     people signing in only.

   **The client secret is a secret.** Never write it into a
   file yourself. A client-credentials method can't be saved
   without it, so either hand the user the values below to add
   the method in the dashboard (Edit integration → Authentication
   methods → OAuth app → "Fruxon signs in as the app"), or write
   the file with `client_secret` as `"<paste here>"` and have the
   user fill it in and run `fruxon integrations create` (or
   `update`) themselves. Never run it with the placeholder: it
   would be saved as the secret.

   Auth0 machine-to-machine app (the API's identifier goes in
   `audience`):
   ```json
   {
     "id": "acme_m2m",
     "displayName": "Acme API (app)",
     "type": "O_AUTH2",
     "testPath": "/v1/health",
     "authSettings": {
       "parameters": {
         "grant_type": "client_credentials",
         "token_url": "https://acme.eu.auth0.com/oauth/token",
         "client_id": "<client id>",
         "client_secret": "<paste here>",
         "token_parameters": "{\"audience\":\"https://api.acme.example\"}"
       }
     }
   }
   ```

   Entra app registration calling Microsoft Graph with
   application permissions (one `.default` scope):
   ```json
   {
     "id": "graph_app",
     "displayName": "Northwind Entra app",
     "type": "O_AUTH2",
     "testPath": "/v1.0/organization",
     "authSettings": {
       "parameters": {
         "grant_type": "client_credentials",
         "token_url": "https://login.microsoftonline.com/<tenant id>/oauth2/v2.0/token",
         "client_id": "<application (client) id>",
         "client_secret": "<paste here>",
         "default_scopes": "[\"https://graph.microsoft.com/.default\"]"
       }
     }
   }
   ```

   A client-credentials method's config needs no connect step:
   the user adds the config in the dashboard and presses Test,
   which fetches a token (and calls `testPath` with it when set),
   or checks it with `fruxon integrations verify`. Your tools
   declare NO `Authorization` header, as for any OAuth method.

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
     `WRITE`. Defaults to `READ_ONLY` when omitted. Only a
     `READ_ONLY` tool can be marked `safeToRepeat` on an agent
     (a retry after a lost result) — the agent's revision is
     refused otherwise. Declare `READ_ONLY` explicitly on any
     pure-function code tool you want repeated.
   - `parametersMetadata[]` — inputs the agent passes when
     calling the tool. Each has `name`, `type`, `displayName`,
     `description`, and optional `required`, `secret`,
     `defaultValue`. **Every parameter needs a `type`**
     (`STRING`, `INTEGER`, `FLOAT`, `BOOLEAN`, `JSON`, … — the
     full list is in `tools create --schema`). An untyped
     parameter saves fine but fails every agent run that has
     the tool: "Unspecified is not supported as an LLM tool
     parameter".

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
       {"name": "visibility", "type": "STRING", "description": "all|public|private"}
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
     "parametersMetadata": [{"name": "diff", "type": "STRING", "required": true}]
   }
   ```
   Parameters are injected as named Python variables at the
   top of the script — reference them directly (`diff` above,
   no `kwargs` dance). Assign to `result` to return data.
   Optional `packages: ["requests", ...]` installs PyPI deps
   into the sandbox; `timeoutSeconds` is 1–120 (default 60).

   **How values arrive.** Each value is typed by what it looks
   like, not by the parameter's declared `type`:
   - `true` / `false` / `null` → `True` / `False` / `None`.
   - A number → `int` or `float`.
   - Valid JSON starting with `{` or `[` → an already-parsed
     `dict` / `list`. Don't `json.loads()` it again — that
     raises `TypeError`.
   - Anything else → `str`.
   So a `STRING` parameter the agent fills with `"42"` arrives
   as the int `42`. Write the script to accept either
   (`str(x)`, `isinstance(x, dict)`) where it matters.

   **Parameters carry data, not code.** Write a custom code
   tool when the script is fixed and only the data varies.
   Never treat a parameter as code to run.

   **Changing a code tool.** Edit the JSON and update it in
   place — the same file shape as create, with the whole
   `descriptor.codeTool` (code, timeoutSeconds, packages,
   resultType) and `parametersMetadata`:
   ```
   fruxon tools update <integration-id> <tool-id> --file ./<tool>.json
   ```
   It's a wholesale replace, not a patch: a field you leave out
   is reset. The stored tool decides its kind, so a body with an
   API descriptor (or none) is refused with 400 — send
   `descriptor.codeTool`.

6. **Create each tool.**
   ```
   fruxon tools create <integration-id> --file ./list_repos.json
   ```

7. **Hand off to the user. This is the UX-critical step.**
   Get the user a link that connects it:
   - **API key, bearer token or username + password** shared by the
     workspace (an APPLICATION-level method):
     `fruxon integrations connect <integration-id> -o json` creates the
     config and returns its `configId` and a `url`. The page it opens
     takes the secret, tests it and publishes the config. Required
     connection settings go in as `--param name=value`.
   - **OAuth** shared by the workspace: the same command,
     `fruxon integrations connect <integration-id> -o json` (`--scope`
     for what to ask). Whoever opens the link signs in to the provider,
     and the account is connected and the config published.
   - **Per-user credentials** (each person connects their own): nothing
     to fill now; each user is asked on first use.

   Compose a SHORT, FRIENDLY message that includes:
   - One line: what you built (integration + tool count).
   - The link, and one line on what the user will be asked to paste
     (or, for OAuth, which account to sign in with).
   - The fallback: the dashboard (`fruxon integrations open <id>`).

   Example:
   ```
   ✓ Created the `github` integration with 4 tools.

   Now connect your account — agents can't call the tools until
   this is done. Open this link, sign in to Fruxon and paste a
   GitHub Personal Access Token:
      → https://app.fruxon.com/credential-entry#t=…

   Or connect it in the dashboard: fruxon integrations open github
   ```

   DO NOT ask the user for the secret in chat. DO NOT offer to
   put it in the JSON file. A Fruxon page (the link's, or the
   dashboard) is the only place secrets are accepted, by design.

## After the user connects

Once the user reports the config is set up, verify:
```
fruxon integrations configs list <integration-id>   # published: true?
fruxon tools run <integration-id> --tool <tool-id> -c <config-uuid>   # proves the saved credential works
```

Pick a READ_ONLY tool for the `tools run` check. `fruxon integrations
verify` is not a check of a saved config: it takes `--file` with an
unsaved `VerifyAuthConfigRequest` (the credential itself), which the
user would have to hand you, so don't use it here.

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

## Removing what you built

A test integration, or one built wrong, comes out in two steps — configs
first, since the server keeps an integration while any config references it:
```
fruxon integrations configs list <integration-id>                  # note each config id
fruxon integrations configs delete <integration-id> <config-id> --yes
fruxon integrations delete <integration-id> --yes                  # its tools go with it
```
Both ask first and need `--yes` in agent mode: name what will be
deleted and add `--yes` only once the human agrees. A config an agent's
current revision, a participant or an active trigger still uses is
refused: point that at another config first. Only delete what you (or
the user, in this conversation) created — never someone's live config.

## Common pitfalls

- Hardcoding the secret in `apiTool.headers` instead of using a
  `{auth.token}` placeholder. The secret should never be in
  the integration definition; it lives in the config.
- A tool parameter with no `type`. It saves, then every agent
  run that has the tool fails before the first model call.
- Forgetting `"secret": true` on auth parameters — dashboard
  won't mask the input field.
- Authoring tools before the integration exists (server returns
  404 — order matters).
- Rebuilding an integration the platform already has. Run the
  existence check first (step 1) — `fruxon integrations list
  --query <keyword>` — and reuse/extend instead of duplicating.
- `id` collisions: both `integration.id` and `tool.id` are
  unique-per-tenant. If `fruxon integrations get <id>` returns
  404, the id is free. Otherwise pick a fresh slug (keeping the
  `custom_` prefix).
- Skipping the dashboard handoff and instead writing the secret
  into the JSON. Don't. Even if the user offers it. The shape /
  instance separation is a security boundary, not a suggestion.
