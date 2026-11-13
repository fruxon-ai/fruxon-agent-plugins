# Fruxon

Build, run, and debug [Fruxon](https://fruxon.com) agents from your coding
assistant. Fruxon is a platform for designing, testing, deploying, and
monitoring AI agents. This plugin teaches the assistant to drive the
`fruxon` command-line tool, so you can ask for an agent in plain language
and have it drafted, tested against real inputs, published as a revision,
and diagnosed from its execution trace when a run goes wrong.

The plugin works in Claude Code and in Codex.

## Requirements

- A Fruxon account and workspace
- The `fruxon` CLI, installed and signed in:

  ```bash
  uv tool install fruxon   # or: pipx install fruxon
  fruxon login
  ```

The plugin does not install the CLI for you. The skills tell the assistant
what to run; if the `fruxon` command is missing, the assistant will ask you
to install it. Keep the CLI current with `uv tool upgrade fruxon` (or
`pipx upgrade fruxon`), since the skills describe the latest release.

## Install

**Claude Code**, inside a session:

```
/plugin install fruxon --marketplace fruxon-ai/fruxon-agent-plugins
```

**Codex**: install **Fruxon** from the Plugins Directory, or add this
repository as a marketplace from a terminal and install from there:

```bash
codex plugin marketplace add fruxon-ai/fruxon-agent-plugins
```

then run `/plugins` inside Codex and pick **Fruxon**.

## Skills

| Skill | Use it to |
| --- | --- |
| `fruxon-meet` | Get oriented on Fruxon's concepts and the CLI's main commands |
| `fruxon-build-agent` | Author, test, publish, and deploy an agent revision |
| `fruxon-use-integrations` | Wire connected tools (Slack, GitHub, Jira, Drive…) into an agent |
| `fruxon-create-integration` | Create a new integration with API or Python code tools |
| `fruxon-debug-trace` | Diagnose a failed or surprising run from its trace |
| `fruxon-agent-mode` | Read the CLI's JSON output, NDJSON streams, exit codes, and error envelopes |

The assistant loads a skill when your request matches it, or you can ask
for one by name.

## What the plugin runs and sends

The plugin itself contains only instructions (the skills). It runs no
hooks, stores nothing and makes no network calls of its own.

- **The `fruxon` CLI**, which the assistant runs when you ask it to, talks
  to the Fruxon API (`https://api.fruxon.com` by default) as the workspace
  you signed in to with `fruxon login`. It sends what the command you asked
  for needs: agent definitions, test inputs, integration settings.
- **Credentials** stay with the CLI: `fruxon login` keeps your API key in
  the operating system's keychain, or in `~/.fruxon` where no keychain is
  available. Integration secrets, such as a third-party
  access token, are entered by you on app.fruxon.com, not passed through
  the assistant.
- **Usage telemetry**: once signed in, the CLI reports which command ran and
  whether it succeeded to the Fruxon API, never argument values, output, or
  your key. Turn it off with `fruxon config set telemetry false` or
  `DO_NOT_TRACK=1`. Details are in the [privacy policy](https://fruxon.com/privacy-policy).

## Support

Contact the Fruxon team at [fruxon.com/contact](https://fruxon.com/contact).
Bugs in the plugin itself can also go to
[github.com/fruxon-ai/fruxon-agent-plugins/issues](https://github.com/fruxon-ai/fruxon-agent-plugins/issues).

## License

MIT
