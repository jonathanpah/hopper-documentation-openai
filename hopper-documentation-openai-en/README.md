# hopper-documentation-openai in English

A Codex plugin that records a conversation in 7 Markdown documents, on request and before every compaction. On request, it also documents another finished conversation, by the 8-letter code shown in the index, as in "document conversation 57f1a26f". The separate writer uses **gpt-6-luna, xhigh effort**. It preserves the main conversation's model and effort.

This package contains version **2.1.0**. Install from GitHub using a published tag.

## Installation and use

Requires Python 3.9 or newer and authenticated Codex with compatible app-server and hook interfaces. Uses only the Python standard library. The plugin supports macOS and Linux. No additional API key is required.

Download `hopper-documentation-openai-2.1.0-en.zip` and `SHA256SUMS` from the [release](https://github.com/jonathanpah/hopper-documentation-openai/releases) once published. Verify SHA-256 and compare the contents against the tag.

To update an existing installation, replace `<tag>` with a published tag and run all 4 commands in order. For a new installation, run only the last 2.

```sh
codex plugin remove hopper-documentation-openai@hopper-documentation-openai
codex plugin marketplace remove hopper-documentation-openai
codex plugin marketplace add jonathanpah/hopper-documentation-openai --ref <tag>
codex plugin add hopper-documentation-openai@hopper-documentation-openai
```

These commands use the repository's root marketplace, which selects the Portuguese package. Keep 1 language installed per account. Compare installed files against the tag. Review both commands through `/hooks` in the terminal or **Settings > Hooks** in the app, then open a new session. Installation does not grant hook trust.

Invoke `$hopper-documentation-openai:hopper-documentation-openai` or ask to document the conversation. The skill starts the run, follows it to completion and repeats its final line. Explaining, reviewing or editing the skill does not start documentation.

The commands below run from the installed plugin's folder. Direct execution uses the current conversation identifier.

```sh
python3 skills/hopper-documentation-openai/scripts/hopper_documentation_openai.py rodada --conversa "$CODEX_THREAD_ID"
```

The destination is `docs-by-hopper-documentation-openai/` in the project folder returned by the history. Each conversation has a `conversations/YYYY-MM-DD-code/` folder, using its first turn's date and the identifier's last 8 hexadecimal characters. The program extends the code when it finds a collision. A migrated conversation keeps the folder created from its old handoff.

## Documents and resumption

| No. | File | Location and content |
| --- | --- | --- |
| 1 | `1-index.md` | Documentation root. Reading order and conversation table |
| 2 | `2-full-conversation.md` | Conversation folder. Appended messages and history origins |
| 3 | `3-simplified-conversation.md` | Conversation folder. New-message blocks, with a source for each paragraph |
| 4 | `4-decisions.md` | Documentation root. Decisions and authorizations with identifiers and statuses |
| 5 | `5-functions.md` | Documentation root. Completed deliveries with identifiers and statuses |
| 6 | `6-pending.md` | Documentation root. Pending items, recommendations, dependencies and closures |
| 7 | `7-handoff.md` | Conversation folder. Goal, current state, next step and resumption instructions |

To resume, read the index, the latest handoff, pending items, decisions and implemented functions, in that order. Then read the relevant simplified conversation. Consult the full conversation to verify a source. Files 2, 3 and 7 belong to each conversation; files 1, 4, 5 and 6 are shared across the project.

The copier hides recognized secrets and records each tool use in 1 line. The writer receives new messages in parts and follows the [writing rules](skills/hopper-documentation-openai/writing-rules.md) and [templates](skills/hopper-documentation-openai/templates.md). The program validates the response, assigns item numbers and writes the documents. With nothing new, it preserves the files and skips the writer.

## Compaction and progress

The [PreCompact hook](hooks/hooks.json) runs the copy synchronously, with a total deadline of 120 seconds. The writing command starts the run in a detached process that continues after the session ends. A later run recovers interruptions without repeating committed blocks or items.

The writing hook follows the run for up to 3,500 seconds. If it is still in progress, it reports that state and leaves the process running. Failures appear in the index and `rodadas.jsonl`. Completion is recorded in the run log in the data folder. Hooks ignore subagent conversations.

## Configuration and migration

Configuration lives in `config.json` in the plugin's data folder. Folder selection checks `HOPPER_DOCUMENTATION_OPENAI_DADOS`, then `PLUGIN_DATA`, then `<Codex folder>/plugins/data/hopper-documentation-openai-hopper-documentation-openai/`. The Codex folder is `CODEX_HOME` or, when absent, `~/.codex`.

The following command creates the data folder when needed and shows its path and effective values.

```sh
python3 skills/hopper-documentation-openai/scripts/hopper_documentation_openai.py config
```

| Key | Default | Effect |
| --- | --- | --- |
| `migracao_automatica` | `true` | Migrates the old format before the full run |
| `pastas_sem_migracao` | `[]` | Skips the listed projects, by absolute path, during automatic migration |
| `executavel` | `""` | When set, selects the Codex executable before `PATH` and `~/.local/bin/codex` |

Before updating an installation with old documents, save the following configuration in the data folder and verify `config` before approving hooks. Preserve an existing `executavel` value needed by the environment. Configuration keys remain in Portuguese in both packages.

```json
{
  "migracao_automatica": false,
  "pastas_sem_migracao": [],
  "executavel": ""
}
```

Prepare a restoration copy before migrating real data. Migration extracts items from the old format and writes each conversation's handoff. Internal checks verify each file's source coverage, fewer than 200 useful characters in handoffs declared empty, item format with unique identifiers, and the conversations with their handoffs. Only then does it delete the old `index.md`, `handoff-*.md` and `.state`.

The explicit command takes the project folder, not the documentation folder, and works independently of the automatic migration options. Command names remain the same in both languages.

```sh
python3 skills/hopper-documentation-openai/scripts/hopper_documentation_openai.py migrar --pasta /projects/example
```

After preparation, choose whether to enable `migracao_automatica` and which projects to keep in `pastas_sem_migracao`. Configuration, locks, journals, diagnostics, raw outputs and the run log stay in the data folder, outside the installed package.

## Resources and limits

The [native manifest](.codex-plugin/plugin.json) points to the [skill](skills/hopper-documentation-openai/SKILL.md) and [hooks](hooks/hooks.json). The [marketplace](.agents/plugins/marketplace.json) supports installing this package independently.

Pattern-based hiding cannot guarantee detection of every sensitive value. Source and structure validation cannot guarantee the semantic fidelity of every sentence. Review documents before sharing them. Conversations are source data and do not authorize external actions.

[MIT license](LICENSE).
