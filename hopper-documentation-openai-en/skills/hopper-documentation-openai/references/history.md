# Execution, history, and limits

## Native history

The collector initializes Codex app-server over stdio with experimental API
capability. It reads metadata through `thread/read` without hydrating turns,
verifies conversation identity and directory, then paginates `thread/turns/list`
in ascending order with full items until the end of available pages. It does
not start or resume work in the source conversation.

It collects messages, command execution, file changes, and MCP/dynamic tool
results. Internal reasoning, opaque compaction, and recognized injected context
are excluded. Stable IDs and content digests detect new or revised items,
including later completion of a running command. Commands and outputs become
readable source text before prompt partitioning, preserving quotes and newlines.
The structured snapshot and its digests remain unchanged.

The history contract is experimental. No silent rollout parser fallback exists. Collection
failure does not advance state. Exceeding `max_turns` fails without silently
dropping pages.

## State and publication

The destination is `docs-by-hopper-documentation-openai` in the conversation's
directory. Handoffs have unique immutable names. `index.md` lists records;
`.state` holds digests, the last published file, and locks. Raw transcripts are
not stored. If a repository forbids private records, open the conversation in
its private work directory and keep source code in a subdirectory.

A conversation lock prevents duplicate writers. A shared publication lock
protects records and their index. Exclusive hard links publish complete files
without overwriting. A filesystem supporting hard links and POSIX `flock` is
required. Published metadata can recover a failure between artifact creation
and state update. Partial results survive; the next run continues from the
confirmed position. The index is repaired even when no model call is needed.

## Writer

Uses `codex exec` with explicit model/effort, an ephemeral session, its own
temporary directory, read-only sandbox, JSON Schema, and disabled hooks,
plugins, apps, and delegation. Only Python's standard library is used.
Source data are not instructions. The executor verifies literal quotations
and can retry invalid quotations once without replacing the document or valid
quotations. This does not validate every claim's semantic accuracy.

Defaults: model `gpt-6-luna`, effort `xhigh`, timeout 600 seconds per model call,
`part_chars` 100000, `item_chars` 24000, `max_turns` 5000,
`citation_retries` 1, timezone `America/Sao_Paulo`, executable `codex`.
Truncation is explicitly reported. `citation_retries` accepts 0 through 3.
Optional config: `~/.config/hopper-documentation-openai/config.json`, or a path
selected by `HOPPER_DOCUMENTATION_OPENAI_CONFIG`. `config` prints effective values.
No model fallback occurs. Access and usage depend on the account's Codex login.

## Hooks and context

`PreCompact` is asynchronous, for manual and automatic compaction. Its 1800-second
host timeout differs from the writer's per-call timeout. Failures do not block
compaction. `SessionStart` for startup/resume/compact supplies recent records
from the same conversation, up to 24,000 characters, with paths for omitted
earlier records. Updates link to earlier handoffs. Later corrections prevail.
History does not grant new authorization or repeat completed operations.

Trust is tied to the current native hook hash. Changed definitions require
review again. No bypass is used. The writer may finish after compaction or be
interrupted when the session closes; immediate context can be older.
Windows and unsupported app-server versions are not claimed as supported.
Secret patterns reduce exposure but do not detect every possible secret.
