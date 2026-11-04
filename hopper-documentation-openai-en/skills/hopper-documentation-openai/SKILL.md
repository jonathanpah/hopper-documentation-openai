---
name: hopper-documentation-openai
description: Documents the current Codex conversation in 7 documents (index, full conversation, simplified conversation, decisions, implemented functions, pending items and handoff) in the project's docs-by-hopper-documentation-openai folder. Use when the user asks to document or record the conversation, save progress or write a handoff. Do not use to explain, review or edit this skill.
---

# hopper-documentation-openai

## What the skill produces

The skill records the current conversation in 7 Markdown documents in the project's `docs-by-hopper-documentation-openai` folder. Each conversation has a subfolder identified by the first turn's date and conversation code.

- The index lists the reading order and project conversations.
- The full conversation preserves messages by appending. The program hides secrets and records each tool use in 1 line.
- The simplified conversation rewrites the content in short sentences, with source references for each paragraph.
- Decisions, implemented functions and pending items have identifiers, sources and statuses. Implemented functions include any completed delivery.
- The handoff covers the goal, current state, next step, decisions, authorizations, constraints, findings, pending items, gaps and instructions to resume.

The program copies the full conversation. The writer uses `gpt-6-luna` with `xhigh` effort, isolated from tools, following [writing-rules.md](writing-rules.md) and [templates.md](templates.md). The program validates the response, numbers items and writes the documents.

The hook copies before every compaction and starts the same run in a detached process. With automatic migration enabled, the first run migrates old handoffs and deletes them only after internal verification. Configured exclusions skip automatic migration.

## How the skill runs

1. Start the command below in this response. Replace `<this skill folder>` with the directory containing this `SKILL.md`. Use the Codex command tool in the background with a short initial wait.

   ```sh
   python3 "<this skill folder>/scripts/hopper_documentation_openai.py" rodada --conversa "$CODEX_THREAD_ID"
   ```

2. Say in 1 sentence that documentation started in the background.
3. Follow the same process until it finishes. If the tool returns a session identifier, use it to retrieve the remaining output.
4. Repeat the last line of program output to the user without changing its text, including failures or no new content.

If the session sandbox blocks the required access, the program reports `Documentation failed: the session sandbox blocked the required access.` Repeat that line. Preserve session permissions and report the program's result.

Let the program write the documents. Preserve the writer's model and effort. Requests to explain, review or edit this skill, or to explain what a handoff is, call only for that analysis or edit, without running documentation.
