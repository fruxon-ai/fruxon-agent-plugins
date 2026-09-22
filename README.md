# Fruxon plugin for Claude Code

Lets Claude Code build, run, and debug [Fruxon](https://fruxon.com) agents
through the `fruxon` CLI.

## Install

1. Install the CLI and sign in:

   ```bash
   uv tool install fruxon   # or: pipx install fruxon
   fruxon login
   ```

2. In Claude Code, add this marketplace and install the plugin:

   ```
   /plugin marketplace add fruxon-ai/fruxon-claude-plugin
   /plugin install fruxon@fruxon
   ```

## What's inside

| Skill | Use it to |
| --- | --- |
| `fruxon-agent-mode` | Learn the CLI's contract for AI drivers: JSON output, NDJSON streams, exit codes, error envelopes |
| `fruxon-build-agent` | Author, validate, and ship an agent |
| `fruxon-debug-trace` | Diagnose a failed or odd execution from its trace |
| `fruxon-create-integration` | Create a new integration |
| `fruxon-use-integrations` | Wire existing integrations into an agent |
| `fruxon-meet` | Get oriented on Fruxon's concepts and commands |

Claude loads a skill when your request matches it; you can also ask for
one by name. A session-start check tells Claude if the CLI is missing or
older than the skills.

## How it stays current

The skills are written alongside the CLI in the Fruxon SDK and ship in its
PyPI wheel. A daily workflow ([`sync.yml`](.github/workflows/sync.yml))
copies them from the latest release and sets the plugin version to match.
To sync by hand:

```bash
python scripts/sync_skills.py
```

Changes to the skills belong in the SDK, not here; edits in this repo are
overwritten on the next sync.

## License

MIT
