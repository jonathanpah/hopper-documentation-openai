# OpenAI sources and documentation criteria

The skill uses Codex's native format and records information for continuation.
Product requirements, recommendations, and package choices are distinct.
The sources below do not constitute OpenAI certification of this skill.

| Official source | Application |
| --- | --- |
| [Skills](https://learn.chatgpt.com/docs/build-skills) | Frontmatter, activation description, and resources loaded when needed. |
| [Plugins](https://developers.openai.com/plugins/build/plugins) | Manifest, packaging, and native integration. |
| [App-server](https://learn.chatgpt.com/docs/app-server) | Conversation identity and paginated history. |
| [Hooks](https://learn.chatgpt.com/docs/hooks) | Events, asynchronous execution, and definition trust. |
| [Session memory](https://developers.openai.com/cookbook/examples/agents_sdk/session_memory) | Preserve decisions, constraints, identifiers, and temporal order. |
| [Long horizon tasks](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex) | Durable state, progress, and continuation context. |
| [Model guide](https://developers.openai.com/api/docs/guides/latest-model) | Clarity, outcome first, and audience-appropriate structure. |
| [Compaction](https://developers.openai.com/api/docs/guides/compaction) | Distinguish opaque API state from readable continuation records. |
| [Safety](https://developers.openai.com/api/docs/guides/agent-builder-safety) | External sources are data without authority to execute actions. |

## Criteria

Preserve goals, state, decisions, constraints, sources, and pending work.
Distinguish proposal, authorization, attempt, and result. Later corrections
prevail; earlier records do not authorize repeating completed operations.
Identifiers and evidence support verification of current state. Expose gaps.

[Writer](writer.md) defines content; [history](history.md) describes collection,
configuration, and limits. Literal quotations do not prove semantic fidelity.
Pattern-based redaction cannot guarantee detection of every possible secret.

## Packaging

`.codex-plugin/plugin.json` is active. The portable template at
`manifests/agent-plugin.json` is inactive. The [Codex 0.159.3 loader](https://github.com/openai/codex/blob/rust-v0.159.3/codex-rs/core-plugins/src/loader.rs#L950)
does not load hooks in AgentPlugin format. Installation, discovery, and native
trust are separate operations; installation does not grant trust.
