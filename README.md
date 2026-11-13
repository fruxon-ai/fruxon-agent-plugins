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

   **Codex**: install **Fruxon** from the Plugins Directory, or add this
   repository as a marketplace from a terminal:

   ```bash
   codex plugin marketplace add fruxon-ai/fruxon-agent-plugins
   ```

   then run `/plugins` inside Codex and pick **Fruxon**.

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
one by name. The plugin runs no hooks and does not install or check the CLI;
keep `fruxon` current so it matches the skills. Under either tool the CLI
switches itself to agent mode (JSON output, NDJSON streams, typed exit
codes) with no setup; for Codex that needs fruxon 0.14.1 or later.

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
| `plugins/fruxon/.claude-plugin/plugin.json` | Claude Code plugin |
| `plugins/fruxon/plugin.json` | Codex plugin |
| `plugins/fruxon/skills/` | Both |
| `plugins/fruxon/.claude-plugin/icon.png` | Claude Code plugin directory listing |
| `plugins/fruxon/assets/icon.png` | Codex listing (`logo` and `composerIcon` in `plugin.json`) |
| `plugins/fruxon/README.md`, `LICENSE` | Both directory listings |

## License

MIT
