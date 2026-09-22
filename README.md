# Fruxon plugin for Claude Code and Codex

Lets Claude Code and Codex build, run, and debug [Fruxon](https://fruxon.com)
agents through the `fruxon` CLI.

## Install

1. Install the CLI and sign in:

   ```bash
   uv tool install fruxon   # or: pipx install fruxon
   fruxon login
   ```

2. Add this marketplace and install the plugin.

   **Claude Code**, inside a session:

   ```
   /plugin marketplace add fruxon-ai/fruxon-agent-plugins
   /plugin install fruxon@fruxon
   ```

   **Codex**, from a terminal:

   ```bash
   codex plugin marketplace add fruxon-ai/fruxon-agent-plugins
   codex plugin add fruxon@fruxon
   ```

   or run `/plugins` inside Codex and pick **Fruxon**.

## What's inside

| Skill | Use it to |
| --- | --- |
| `fruxon-agent-mode` | Learn the CLI's contract for AI drivers: JSON output, NDJSON streams, exit codes, error envelopes |
| `fruxon-build-agent` | Author, validate, and ship an agent |
| `fruxon-debug-trace` | Diagnose a failed or odd execution from its trace |
| `fruxon-create-integration` | Create a new integration |
| `fruxon-use-integrations` | Wire existing integrations into an agent |
| `fruxon-meet` | Get oriented on Fruxon's concepts and commands |

The agent loads a skill when your request matches it; you can also ask for
one by name. A session-start check tells it when the CLI is missing or older
than the skills. Under either tool the CLI switches itself to agent mode
(JSON output, NDJSON streams, typed exit codes) with no setup; for Codex
that needs fruxon 0.14.1 or later.

## How it stays current

The skills are written alongside the CLI in the Fruxon SDK and ship in its
PyPI wheel. A daily workflow ([`sync.yml`](.github/workflows/sync.yml))
copies them from the latest release and sets both manifests' version to match.
To sync by hand:

```bash
python scripts/sync_skills.py
```

Changes to the skills belong in the SDK, not here; edits in this repo are
overwritten on the next sync.

## Layout

One plugin serves both tools; each reads its own manifest and ignores the other's.

| Path | Read by |
| --- | --- |
| `.claude-plugin/marketplace.json` | Claude Code marketplace |
| `.agents/plugins/marketplace.json` | Codex marketplace |
| `plugins/fruxon/.claude-plugin/plugin.json`, `hooks/hooks.json` | Claude Code plugin |
| `plugins/fruxon/plugin.json`, `hooks/codex-hooks.json` | Codex plugin |
| `plugins/fruxon/skills/` | Both |

## License

MIT
