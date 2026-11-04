# Document templates

The program writes the headers, the block titles and the final identifiers. You write the content. Use `N1`, `N2`… for new items in any field; the program replaces those references with the final identifiers.

Cite only messages from the new segment or before it and items that exist in the folder. Use `N1`, `N2`… for new items in this response. To discuss what comes after the new segment, write without an identifier. During migration, cite old files and items, since the messages do not exist.

## Document 3, simplified conversation

The `conversa_simplificada` field is the body of 1 block. It starts with the subject line and continues with short paragraphs. Each paragraph ends with the source messages in parentheses, separated by commas. A range uses the form `M3-4e5f6a7b a M7-4e5f6a7b`.

```markdown
**Subject: failure of the automatic Codex record.**

The automatic Codex record failed before compaction. The program rejected 2 quotes that were not identical in the conversation. (M1-4e5f6a7b)
```

When the segment brings nothing relevant, return `nada_relevante` equal to `true` and leave `conversa_simplificada` empty.

## Documents 4, 5 and 6, items

Each item of `itens_novos` has `tipo` (`D` decision, `F` implemented function, `PD` pending item), `texto` (1 or 2 sentences), `origem` (messages of the new segment or existing items), `situacao` and, only in pending items, `recomendacao` and `depende_de`. An "implemented function" is any delivery finished in the conversation: code, configuration, document or process.

Allowed statuses:

| Type | Statuses |
| --- | --- |
| D, decisions | `in force`, `replaced by <ID>`, `revoked in <M-ID>` |
| F, implemented functions | `done`, `replaced by <ID>`, `undone in <M-ID>` |
| PD, pending items | `open`, `closed in <M-ID> (<short reason>)` |

How the program writes an item:

```markdown
### PD1-4e5f6a7b
Choose the chart format.

- Recommendation: compare bars and lines.
- Depends on: the user choosing the chart format.
- Source: M66-4e5f6a7b
- Status: open
- Run range: M56-4e5f6a7b a M80-4e5f6a7b
```

To change the status of an item that already exists, including one from another conversation of the same folder, use `mudancas`, with the identifier, the new status and the source. The source of a new item or a change is a message from the new segment or an existing item, never a message from an earlier segment. During migration, the source is the old file name.

## Document 7, handoff

The 9 keys of the `handoff` field become the 9 sections, in this order: Goal; Topics and current state; Next step; Decisions and authorizations in force; Constraints in force; Findings and discarded approaches; Pending items and commitments; Gaps; How to resume. Write each section in short paragraphs, each with the source messages in parentheses. The handoff is rewritten in full on every run: include what still holds from the previous handoff.

## Summary

The `resumo` field has up to 80 characters and goes to the folder index, in the "Subject" column.

## Migration

Return `handoffs_antigos`, with 1 entry per conversation in this part's files. Each entry contains `conversa`, `resumo` of up to 80 characters and `handoff` with the 9 keys. The program calculates dates from the oldest handoff file name. Do not include `data` in the response.

Each new item also includes `conversa`. Sources cite the supplied old file names. Cite source files in handoff paragraphs. Preserve what still applies from `handoff_anterior` when a conversation continues in another part.

`sem_conteudo` lists only handoffs with fewer than 200 useful characters, excluding headings and references. The program checks the count. An intermediate handoff with 200 or more characters must be a source of an item or handoff. The program classifies `index.md` and `.state` without sending them to the writer. Symbolic links are not read.
