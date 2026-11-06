# Fruxon

Build, run, and debug [Fruxon](https://fruxon.com) agents from Claude Code.
Fruxon is a platform for designing, testing, deploying, and monitoring AI
agents. This plugin teaches Claude to drive the `fruxon` command-line tool,
so you can ask for an agent in plain language and have Claude draft it,
test it against real inputs, publish a revision, and work out why a run
went wrong from its execution trace.

## Requirements

- A Fruxon account and workspace
- The `fruxon` CLI, installed and signed in:

  ```bash
  uv tool install fruxon   # or: pipx install fruxon
  fruxon login
  ```

Then install the plugin inside Claude Code:

```
/plugin install fruxon --marketplace fruxon-ai/fruxon-agent-plugins
```

The plugin does not install the CLI for you. If it is missing or older than
the skills, a check at the start of each session tells Claude, and Claude
asks you to install or upgrade it.

## Skills

| Skill | Use it to |
| --- | --- |
| `fruxon-meet` | Get oriented on Fruxon's concepts and the CLI's main commands |
| `fruxon-build-agent` | Author, test, publish, and deploy an agent revision |
| `fruxon-use-integrations` | Wire connected tools (Slack, GitHub, Jira, Drive…) into an agent |
| `fruxon-create-integration` | Create a new integration with API or Python code tools |
| `fruxon-debug-trace` | Diagnose a failed or surprising run from its trace |
| `fruxon-agent-mode` | Read the CLI's JSON output, NDJSON streams, exit codes, and error envelopes |

Claude loads a skill when your request matches it, or you can ask for one by
name.

## What the plugin runs and sends

The plugin itself contains only instructions (the skills). It runs no
hooks in Claude, stores nothing and makes no network calls of its own.

- **The `fruxon` CLI**, which Claude runs when you ask it to, talks to the
  Fruxon API (`https://api.fruxon.com` by default) as the workspace you
  signed in to with `fruxon login`. It sends what the command you asked for
  needs: agent definitions, test inputs, integration settings.
- **Credentials** stay with the CLI: `fruxon login` keeps your API key in
  the operating system's keychain, or in `~/.fruxon` where no keychain is
  available. Integration secrets, such as a third-party
  access token, are entered by you on app.fruxon.com, not passed through
  Claude.
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
