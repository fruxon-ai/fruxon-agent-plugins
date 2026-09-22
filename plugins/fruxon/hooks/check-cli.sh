#!/usr/bin/env bash
# SessionStart hook: tell Claude when the fruxon CLI is missing or older
# than the release these skills were synced from. Silent when all is well,
# so it costs no context in the common case.

plugin_version=$(sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" | head -1)

if ! command -v fruxon >/dev/null 2>&1; then
  echo "The fruxon plugin is enabled but the fruxon CLI is not on PATH. Before running any fruxon command, ask the user to install it: \`uv tool install fruxon\` (or \`pipx install fruxon\`), then \`fruxon login\`."
  exit 0
fi

installed=$(fruxon --version 2>/dev/null | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
[ -z "$installed" ] || [ -z "$plugin_version" ] && exit 0

# Warn only when the installed CLI is older than the skills' release.
oldest=$(printf '%s\n%s\n' "$installed" "$plugin_version" | sort -V | head -1)
if [ "$installed" != "$plugin_version" ] && [ "$oldest" = "$installed" ]; then
  echo "The installed fruxon CLI is $installed, but the fruxon plugin's skills document $plugin_version. Some commands in the skills may not exist yet; suggest \`uv tool upgrade fruxon\` (or \`pipx upgrade fruxon\`) if a command is missing."
fi
exit 0
