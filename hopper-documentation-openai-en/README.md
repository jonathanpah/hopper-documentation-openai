# hopper-documentation-openai — English

A Codex plugin that records conversations for continuation, preserving state,
decisions, sources, and pending work. The separate writer uses **GPT-6 Luna,
xhigh effort**. It preserves the main conversation's model and effort.

## Installation and use

Requires Python 3.9+ and authenticated Codex with the native history and hook
interfaces described in [history and limits](skills/hopper-documentation-openai/references/history.md).
No additional API key or Python dependencies.

Keep this package in a permanent directory:

```sh
codex plugin marketplace add /absolute/path/to/this-package
codex plugin add hopper-documentation-openai@hopper-documentation-openai
```

Review both definitions through `/hooks` and trust only the reviewed definitions.
Enable the native `hooks` feature if disabled. Installation does not grant trust.
A new session loads the installed skill.

Invoke `$hopper-documentation-openai:hopper-documentation-openai` or ask to record
the conversation. For direct execution, provide its identity and directory:

```sh
python3 skills/hopper-documentation-openai/scripts/hopper_documentation.py run --thread-id ID --cwd DIRECTORY
```

`PreCompact` records in the background before manual or automatic compaction.
`SessionStart` supplies recent records from the same conversation. Destination:
`DIRECTORY/docs-by-hopper-documentation-openai`. With no new information, the
writer is not called. Recording can finish after compaction; immediate resumption
can receive an earlier record.

Optional configuration: `~/.config/hopper-documentation-openai/config.json`.
`python3 skills/hopper-documentation-openai/scripts/hopper_documentation.py config`
shows effective values. The model is never silently substituted.

## Resources and verification

`.codex-plugin/plugin.json` is the active manifest. Installed runtimes do not
yet load hooks in the portable format. `manifests/agent-plugin.json` preserves
the portable template for a future migration requiring new verification. Resources are in
`skills/hopper-documentation-openai`; hooks in `hooks/hooks.json`. This package
targets Codex and does not declare a Claude installation.

See [OpenAI sources](skills/hopper-documentation-openai/references/openai-research.md)
and the execution limits above.
