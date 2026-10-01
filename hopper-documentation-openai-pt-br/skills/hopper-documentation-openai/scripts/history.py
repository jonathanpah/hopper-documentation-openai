"""Leitura do histórico estruturado do Codex, sem iniciar turnos de modelo."""

import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import time

from redaction import mask


class HistoryError(Exception):
    pass


class AppServer:
    def __init__(self, executable="codex", cwd=None, timeout=30, arguments=None, environment=None):
        self.timeout = timeout
        self.sequence = 0
        self.buffer = bytearray()
        self.notifications = []
        self.process = subprocess.Popen(
            [executable, "app-server", "--listen", "stdio://"] +
            (arguments if arguments is not None else ["--disable", "hooks"]),
            cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, env=environment,
        )
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        try:
            self.call("initialize", {
                "clientInfo": {"name": "hopper_documentation_openai", "version": "0.1.0"},
                "capabilities": {"experimentalApi": True},
            })
            self.send({"method": "initialized"})
        except BaseException:
            self.close()
            raise

    def send(self, value):
        self.process.stdin.write((json.dumps(value) + "\n").encode())
        self.process.stdin.flush()

    def call(self, method, params):
        self.sequence += 1
        request_id = self.sequence
        self.send({"id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            while b"\n" in self.buffer:
                line, _, rest = self.buffer.partition(b"\n")
                self.buffer[:] = rest
                if not line:
                    continue
                value = json.loads(line)
                if "method" in value:
                    self.notifications.append(value)
                if value.get("id") == request_id:
                    if "error" in value:
                        raise HistoryError(mask(str(value["error"]))[-1500:])
                    return value.get("result")
            if self.selector.select(max(0, deadline - time.monotonic())):
                chunk = os.read(self.process.stdout.fileno(), 65536)
                if not chunk:
                    raise HistoryError("O app-server encerrou antes de responder.")
                self.buffer.extend(chunk)
        raise HistoryError("Tempo de leitura do app-server excedido.")

    def drain(self, timeout=1):
        if self.selector.select(timeout):
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if chunk:
                self.buffer.extend(chunk)
        while b"\n" in self.buffer:
            line, _, rest = self.buffer.partition(b"\n")
            self.buffer[:] = rest
            if line:
                value = json.loads(line)
                if "method" in value:
                    self.notifications.append(value)
        return self.notifications

    def close(self):
        self.selector.close()
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        for stream in (self.process.stdin, self.process.stdout):
            stream.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def normalize_item(item, turn):
    kind = item.get("type")
    role = kind
    if kind == "userMessage":
        role = "user"
        text = "\n".join(c.get("text", "") for c in item.get("content", [])
                         if c.get("type") == "text")
        # Estes blocos são contexto injetado do host, não falas do usuário.
        if text.lstrip().startswith(("# AGENTS.md instructions", "<environment_context>",
                                    "<user_instructions>", "<external_codex_apps_open_page>")):
            return None
    elif kind == "agentMessage":
        role = "assistant"
        text = item.get("text", "")
    elif kind == "commandExecution":
        text = json.dumps({k: item.get(k) for k in (
            "command", "cwd", "status", "processId", "exitCode", "aggregatedOutput")},
            ensure_ascii=False)
    elif kind == "fileChange":
        text = json.dumps({"status": item.get("status"), "changes": item.get("changes")},
                          ensure_ascii=False)
    elif kind in ("dynamicToolCall", "mcpToolCall"):
        text = json.dumps({k: item.get(k) for k in (
            "namespace", "server", "tool", "arguments", "status", "success",
            "contentItems", "result", "error") if k in item}, ensure_ascii=False)
    else:
        # Não coleta raciocínio, resumos opacos de compactação ou mídia binária.
        return None
    if not text.strip():
        return None
    identity = item.get("id")
    if not identity:
        raise HistoryError("Item de histórico sem identificador estável.")
    entry = {"id": identity, "turn_id": turn["id"], "role": role,
             "timestamp": turn.get("startedAt"), "text": mask(text)}
    entry["digest"] = fingerprint(entry)
    return entry


def collect(thread_id, cwd, executable="codex", max_turns=5000):
    with AppServer(executable, cwd) as server:
        thread = server.call("thread/read", {"threadId": thread_id, "includeTurns": False})["thread"]
        if thread.get("id") != thread_id:
            raise HistoryError("Identidade da conversa não corresponde ao pedido.")
        if Path(thread.get("cwd", "")).resolve() != Path(cwd).resolve():
            raise HistoryError("O diretório da conversa não corresponde ao diretório solicitado.")
        cursor, seen_cursors, turns = None, set(), []
        while True:
            page = server.call("thread/turns/list", {
                "threadId": thread_id, "cursor": cursor, "limit": 50,
                "sortDirection": "asc", "itemsView": "full",
            })
            turns.extend(page.get("data", []))
            if len(turns) > max_turns:
                raise HistoryError("Histórico excede max_turns; ajuste o limite sem omitir páginas.")
            cursor = page.get("nextCursor")
            if not cursor:
                break
            if cursor in seen_cursors:
                raise HistoryError("Cursor de paginação repetido.")
            seen_cursors.add(cursor)
        entries = []
        for turn in turns:
            for item in turn.get("items", []):
                entry = normalize_item(item, turn)
                if entry:
                    entries.append(entry)
        return {"thread_id": thread_id, "cwd": str(Path(cwd).resolve()),
                "coverage": "Histórico nativo paginado até o fim das páginas disponíveis nesta coleta.",
                "entries": entries, "turn_count": len(turns)}
