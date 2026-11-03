#!/usr/bin/env python3
"""Apoio de U2. Só biblioteca padrão, Python 3.9, interface pública C36.

Também é o executável Codex simulado. O histórico vem de
HOPPER_DOCUMENTATION_OPENAI_SIMULADO_HISTORICO (JSON de B1). A chave
opcoes controla páginas, sobreposição, atraso e inventário de skills e MCP.
HOPPER_DOCUMENTATION_OPENAI_SIMULADO_REGISTRO guarda as chamadas.
HOPPER_DOCUMENTATION_OPENAI_SIMULADO aceita um caminho, uma lista JSON ou
caminhos separados por vírgula. Cada lista tem seu contador entre processos;
o último arquivo se repete. Respostas normais são objetos do Anexo D.
Um envelope {"resposta": objeto, ...} acrescenta espera_segundos,
codigo_de_saida, stderr, texto_bruto e eventos, sem enviá-los ao programa.
Todas as esperas simuladas usam a escala de C36.

Protocolo congelado no esquema 0.166.0 e em V-U1-05 e V-U1-06.
Não importa, chama nem substitui funções internas do programa em teste.
"""

import base64
import copy
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CASOS = RAIZ / "aceite" / "casos"
SIMULADO = Path(__file__).resolve()
PREFIXO = "HOPPER_DOCUMENTATION_OPENAI_"
PACOTE = Path(os.environ.get(PREFIXO + "PACOTE", "hopper-documentation-openai-pt-br"))
if not PACOTE.is_absolute():
    PACOTE = RAIZ / PACOTE
IDIOMA = "en" if PACOTE.name.endswith("-en") else "pt-br"
SKILL_REL = Path("skills/hopper-documentation-openai")
PROGRAMA_REL = SKILL_REL / "scripts/hopper_documentation_openai.py"
SKILL = PACOTE / SKILL_REL
PROGRAMA = PACOTE / PROGRAMA_REL
CONVERSA_B1 = "01a2b3c4-5d6e-7f80-9a1b-2c3d4e5f6a7b"
CODIGO_B1 = "4e5f6a7b"
CONVERSA_OUTRA = "01a2b3c5-5d6e-7f80-9a1b-0a1b2c3d4e5f"
PASTA_DADOS = "plugins/data/hopper-documentation-openai-hopper-documentation-openai"
CHAVES_HANDOFF = ["objetivo", "pautas_e_estado", "proximo_passo", "decisoes_e_autorizacoes",
                  "restricoes", "descobertas", "pendencias", "lacunas", "como_retomar"]
TEXTOS = {
    "pt-br": {
        "conversas": "conversas", "d1": "1-indice.md", "d2": "2-conversa-integral.md",
        "d3": "3-conversa-simplificada.md", "d4": "4-decisoes.md", "d5": "5-funcoes.md",
        "d6": "6-pendencias.md", "d7": "7-handoff.md", "integral": "Conversa integral",
        "conversa": "Conversa", "projeto": "Pasta do projeto", "fuso": "Fuso dos horários",
        "origem": "Origem", "situacao": "Situação", "intervalo": "Intervalo da rodada",
        "recomendacao": "Recomendação", "depende_de": "Depende de", "oculto": "[oculto]",
        "imagem": "[imagem anexada]", "audio": "[áudio anexado]", "arquivo": "[arquivo anexado: ",
        "skill": "[skill chamada: ", "ferramenta": "Ferramenta: ", "assunto": "**Assunto: ",
        "sem_conteudo": "Sem conteúdo novo relevante.", "sem_integral": "sem conversa integral",
        "vigente": "vigente", "concluida": "concluída", "aberta": "aberta", "encerrada": "encerrada em",
        "sucesso": "Documentação concluída: ", "falha": "Documentação falhou: ",
        "nada_novo": "Documentação: nada novo.", "migracao": "migração",
        "andamento": "Documentação em andamento; o resultado fica no registro de rodadas.",
        "ultima": "Última mensagem coberta", "data": "Data da rodada", "redator": "Redator",
        "ordem": "Ordem de leitura", "tabela": "Conversas", "falhou": "falhou",
        "colunas": ["Conversa", "Início", "Última mensagem", "Última rodada", "Resultado", "Assunto"],
        "autores": ["Usuário", "Codex", "Plano", "Evento"],
        "secoes_d7": ["Objetivo", "Pautas e estado atual", "Próximo passo", "Decisões e autorizações vigentes",
                      "Restrições vigentes", "Descobertas e tentativas descartadas", "Pendências e compromissos",
                      "Lacunas", "Como retomar"],
        "secoes_skill": ["O que a skill produz", "Como a skill roda"],
        "regras": "regras-de-escrita.md", "modelos": "modelos.md",
    },
    "en": {
        "conversas": "conversations", "d1": "1-index.md", "d2": "2-full-conversation.md",
        "d3": "3-simplified-conversation.md", "d4": "4-decisions.md", "d5": "5-functions.md",
        "d6": "6-pending.md", "d7": "7-handoff.md", "integral": "Full conversation",
        "conversa": "Conversation", "projeto": "Project folder", "fuso": "Time zone",
        "origem": "Source", "situacao": "Status", "intervalo": "Run range",
        "recomendacao": "Recommendation", "depende_de": "Depends on", "oculto": "[hidden]",
        "imagem": "[image attached]", "audio": "[audio attached]", "arquivo": "[file attached: ",
        "skill": "[skill invoked: ", "ferramenta": "Tool: ", "assunto": "**Subject: ",
        "sem_conteudo": "No relevant new content.", "sem_integral": "no full conversation",
        "vigente": "in force", "concluida": "done", "aberta": "open", "encerrada": "closed in",
        "sucesso": "Documentation done: ", "falha": "Documentation failed: ",
        "nada_novo": "Documentation: nothing new.", "migracao": "migration",
        "andamento": "Documentation in progress; the result goes to the run log.",
        "ultima": "Last covered message", "data": "Run date", "redator": "Writer",
        "ordem": "Reading order", "tabela": "Conversations", "falhou": "failed",
        "colunas": ["Conversation", "Start", "Last message", "Last run", "Result", "Subject"],
        "autores": ["User", "Codex", "Plan", "Event"],
        "secoes_d7": ["Goal", "Topics and current state", "Next step", "Decisions and authorizations in force",
                      "Constraints in force", "Findings and discarded approaches", "Pending items and commitments",
                      "Gaps", "How to resume"],
        "secoes_skill": ["What the skill produces", "How the skill runs"],
        "regras": "writing-rules.md", "modelos": "templates.md",
    },
}
TEXTO = TEXTOS[IDIOMA]


def le(caminho):
    return Path(caminho).read_text(encoding="utf-8")


def json_de(caminho):
    return json.loads(le(caminho))


def grava_json(caminho, valor):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(caminho.name + ".tmp")
    temporario.write_text(json.dumps(valor, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporario.replace(caminho)


def sha256(caminho):
    return hashlib.sha256(Path(caminho).read_bytes()).hexdigest()


def linhas_json(caminho):
    if not Path(caminho).exists():
        return []
    return [json.loads(linha) for linha in le(caminho).splitlines() if linha.strip()]


def corpo_do_documento_2(texto):
    m = re.search(r"^## M1-", texto, re.M)
    return texto[m.start():] if m else ""


def mensagens(texto):
    return re.findall(r"^## (M\d+-[^\s]+) · ([^\n]+)\n<!-- registros: ([^\n]+) -->\n\n(.*?)(?=^## M\d+-[^\s]+ · |\Z)",
                      texto, re.M | re.S)


def blocos(texto):
    return re.findall(r"^## (M\d+-\S+ a M\d+-\S+)\s*$", texto, re.M)


def itens(texto):
    saida = []
    for ident, corpo in re.findall(r"^### ((?:D|F|PD)\d+-[^\s]+)\n(.*?)(?=^### |\Z)", texto, re.M | re.S):
        campos = dict(re.findall(r"^- ([^:\n]+): (.*)$", corpo, re.M))
        conteudo = [l.strip() for l in corpo.splitlines() if l.strip() and not l.startswith("- ")]
        saida.append({"id": ident, "texto": "\n".join(conteudo), "campos": campos})
    return saida


def tag(texto, nome):
    m = re.search(r"<" + re.escape(nome) + r">(.*?)</" + re.escape(nome) + r">", texto, re.S)
    return m.group(1).strip() if m else None


def ultima_linha(texto):
    linhas = [l for l in texto.splitlines() if l.strip()]
    return linhas[-1] if linhas else ""


def espera(condicao, segundos=10):
    fim = time.monotonic() + segundos
    while time.monotonic() < fim:
        if condicao():
            return True
        time.sleep(0.01)
    return bool(condicao())


def usuario(ident, texto):
    return {"id": ident, "type": "userMessage", "content": [{"type": "text", "text": texto}]}


def turno(ident, registros, hora=1773500400, status="completed", **extra):
    return dict(id=ident, startedAt=hora, status=status, items=registros, **extra)


def inventario(raiz, excluir=()):
    """Conteúdo, modo e mtime; não segue links nem usa prefixos ambíguos."""
    raiz = Path(raiz)
    saida = {}
    for pasta, dirs, arquivos in os.walk(str(raiz)):
        dirs[:] = [d for d in dirs if not any(Path(pasta, d) == e for e in excluir)]
        for nome in arquivos:
            p = Path(pasta, nome)
            if any(p == e or e in p.parents for e in excluir):
                continue
            st = p.lstat()
            conteudo = os.readlink(str(p)) if p.is_symlink() else sha256(p)
            saida[str(p.relative_to(raiz))] = (conteudo, st.st_mode, st.st_mtime_ns)
    return saida


class Ambiente:
    """Projeto, Codex e pacote isolados; todas as chamadas passam por C36."""

    def __init__(self):
        self.raiz = Path(tempfile.mkdtemp(prefix="aceite-openai-")).resolve()
        self.projeto = self.raiz / "projeto"
        self.casa = self.raiz / "casa"
        self.codex = self.raiz / "codex"
        self.dados = self.codex / PASTA_DADOS
        self.bin = self.raiz / "bin"
        for p in (self.projeto, self.casa, self.codex, self.dados, self.bin):
            p.mkdir(parents=True, exist_ok=True)
        self.dados.chmod(0o700)
        self.pacote = self.raiz / PACOTE.name
        shutil.copytree(str(PACOTE), str(self.pacote), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        self.programa = self.pacote / PROGRAMA_REL
        self.registro_simulado = self.dados / "simulado"
        self.registro_simulado.mkdir()
        self.arquivo_historico = self.dados / "historico-simulado.json"
        grava_json(self.arquivo_historico, {"thread": {"id": CONVERSA_B1, "cwd": str(self.projeto),
                                                       "historyMode": "paginated"}, "turns": []})
        self.respostas = self.dados / "respostas-simuladas"
        self.respostas.mkdir()
        self.simulado = self.dados / "codex-simulado"
        self.instala_simulado(self.simulado)
        # PATH fechado. Nunca permite que um teste chame o Codex autenticado.
        (self.bin / "python3").symlink_to(sys.executable)
        self.instala_simulado(self.bin / "codex")
        self.configura(executavel=str(self.simulado))
        self.processos = []

    def instala_simulado(self, caminho):
        caminho = Path(caminho)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text("#!" + sys.executable + "\nimport runpy\nrunpy.run_path(" +
                           repr(str(Path(__file__).resolve())) + ", run_name='__main__')\n", encoding="utf-8")
        caminho.chmod(0o755)
        return caminho

    def limpa(self):
        for p in self.processos:
            if p.poll() is None:
                p.kill()
            try:
                p.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                pass
        # Os testes de permissão sempre restauram os modos antes deste ponto.
        shutil.rmtree(str(self.raiz))

    def configura(self, **valores):
        caminho = self.dados / "config.json"
        atual = json_de(caminho) if caminho.exists() else {}
        atual.update(valores)
        grava_json(caminho, atual)

    @property
    def doc(self):
        return self.projeto / "docs-by-hopper-documentation-openai"

    def pasta_conversa(self, codigo=CODIGO_B1, data="2026-03-14"):
        return self.doc / TEXTO["conversas"] / (data + "-" + codigo)

    def d(self, n, codigo=CODIGO_B1, data="2026-03-14"):
        return (self.pasta_conversa(codigo, data) if n in (2, 3, 7) else self.doc) / TEXTO["d" + str(n)]

    def historico_b1(self, modo="paginated"):
        caso = json_de(CASOS / "b1/historico.json")
        caso["thread"]["historyMode"] = modo
        self.grava_historico(caso)
        return caso

    def grava_historico(self, caso):
        caso = copy.deepcopy(caso)
        for c in caso.get("threads", [caso]):
            c["thread"]["cwd"] = str(self.projeto)
        grava_json(self.arquivo_historico, caso)

    def acrescenta(self, novo_turno):
        caso = json_de(self.arquivo_historico)
        caso["turns"].append(copy.deepcopy(novo_turno))
        self.grava_historico(caso)

    def segunda_rodada(self):
        self.acrescenta(json_de(CASOS / "b1/segunda-rodada.json"))

    def resposta(self, nome):
        origem = CASOS / (nome if "/" in nome else "redator/" + nome)
        if origem.suffix != ".json":
            origem = origem.with_suffix(".json")
        valor = json_de(origem)
        if IDIOMA == "en":
            def traduz(v):
                if isinstance(v, list):
                    return [traduz(x) for x in v]
                if isinstance(v, dict):
                    out = {k: traduz(x) for k, x in v.items()}
                    if "situacao" in out:
                        for pt, en in [("substituída por", "replaced by"), ("revogada em", "revoked in"),
                                       ("desfeita em", "undone in"), ("encerrada em", "closed in"),
                                       ("vigente", "in force"), ("concluída", "done"), ("aberta", "open")]:
                            if out["situacao"].startswith(pt):
                                out["situacao"] = en + out["situacao"][len(pt):]
                                break
                    return out
                if isinstance(v, str):
                    return v.replace("**Assunto: ", "**Subject: ")
                return v
            valor = traduz(valor)
        destino = self.respostas / origem.relative_to(CASOS)
        grava_json(destino, valor)
        return destino

    def ambiente(self, respostas=(), escala="0.02", extra=None):
        env = {"HOME": str(self.casa), "PATH": str(self.bin), "LANG": "en_US.UTF-8", "TZ": "UTC",
               "TMPDIR": str(self.dados), "CODEX_HOME": str(self.codex), "PYTHONDONTWRITEBYTECODE": "1",
               PREFIXO + "DADOS": str(self.dados), PREFIXO + "PACOTE": str(self.pacote),
               PREFIXO + "ESCALA_DE_TEMPO": str(escala),
               PREFIXO + "SIMULADO_HISTORICO": str(self.arquivo_historico),
               PREFIXO + "SIMULADO_REGISTRO": str(self.registro_simulado),
               PREFIXO + "SIMULADO": json.dumps([str(self.resposta(r)) for r in respostas])}
        if extra:
            for k, v in extra.items():
                if v is None:
                    env.pop(k, None)
                else:
                    env[k] = str(v)
        return env

    def roda(self, *args, entrada=None, respostas=(), escala="0.02", extra=None, tempo=30):
        return subprocess.run([sys.executable, "-B", str(self.programa), *args], input=entrada,
                              capture_output=True, text=True, cwd=str(self.raiz), timeout=tempo,
                              env=self.ambiente(respostas, escala, extra))

    def inicia(self, *args, respostas=("rodada-b1",), escala="0.02", extra=None, entrada=None):
        p = subprocess.Popen([sys.executable, "-B", str(self.programa), *args], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(self.raiz),
                             env=self.ambiente(respostas, escala, extra))
        if entrada is not None:
            p.stdin.write(entrada)
        p.stdin.close()
        p.stdin = None
        self.processos.append(p)
        return p

    def rodada(self, conversa=CONVERSA_B1, respostas=("rodada-b1",), **kw):
        return self.roda("rodada", "--conversa", conversa, respostas=respostas, **kw)

    def evento(self, conversa=CONVERSA_B1, trigger="auto", **extra):
        valor = {"session_id": conversa, "transcript_path": str(self.codex / "sessions" /
                 ("rollout-2026-03-14T15-00-00-" + conversa + ".jsonl.zst")),
                 "cwd": str(self.projeto), "hook_event_name": "PreCompact", "trigger": trigger}
        valor.update(extra)
        return json.dumps(valor)

    def copia(self, conversa=CONVERSA_B1, evento=None, **kw):
        return self.roda("copia", entrada=evento or self.evento(conversa), **kw)

    def escrita(self, conversa=CONVERSA_B1, evento=None, respostas=("rodada-b1",), **kw):
        return self.roda("escrita", entrada=evento or self.evento(conversa), respostas=respostas, **kw)

    def migrar(self, respostas=("b3/redator/uma",), **kw):
        return self.roda("migrar", "--pasta", str(self.projeto), respostas=respostas, **kw)

    def formato_antigo(self, nome):
        shutil.copytree(str(CASOS / "b3" / nome), str(self.doc), symlinks=True, dirs_exist_ok=True)

    def rodadas(self):
        return linhas_json(self.dados / "rodadas.jsonl")

    def chamadas(self):
        return [json_de(p) for p in sorted(self.registro_simulado.glob("chamada-*.json"))]

    def rpc(self):
        return linhas_json(self.registro_simulado / "rpc.jsonl")

    def servidores(self):
        return [json_de(p) for p in sorted(self.registro_simulado.glob("servidor-*.json"))]


class CasoDeAceite(unittest.TestCase):
    def setUp(self):
        self.amb = Ambiente()
        self.addCleanup(self.amb.limpa)

    def novo_ambiente(self):
        amb = Ambiente()
        self.addCleanup(amb.limpa)
        return amb

    def documento(self, n, requisito, amb=None, **kw):
        caminho = (amb or self.amb).d(n, **kw)
        # Só os resultados do programa podem estar vazios. Casos de entrada usam
        # le/json_de estritos. Cada teste compara o comportamento do requisito.
        return le(caminho) if caminho.is_file() else ""

    def sucesso(self, r, requisito):
        self.assertEqual(r.returncode, 0, requisito + ": " + r.stdout + r.stderr)

    def terminou(self, requisito, amb=None):
        linhas = (amb or self.amb).rodadas()
        self.assertTrue(any(l.get("etapa") == "escrita" and l.get("resultado") == "concluída" for l in linhas),
                        requisito + ": a rodada completa não foi comprovada no registro")


def _registro():
    p = Path(os.environ[PREFIXO + "SIMULADO_REGISTRO"])
    p.mkdir(parents=True, exist_ok=True)
    return p


def _contador(nome):
    p = _registro() / (nome + ".contador")
    with p.open("a+", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.seek(0)
        n = int(f.read() or "0") + 1
        f.seek(0)
        f.truncate()
        f.write(str(n))
    return n


def _log(nome, valor):
    with (_registro() / nome).open("a", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.write(json.dumps(valor, ensure_ascii=False) + "\n")


def _escala():
    return float(os.environ.get(PREFIXO + "ESCALA_DE_TEMPO", "1"))


def _metadados(argv):
    return {"argv": argv, "cwd": os.getcwd(), "pid": os.getpid(), "executavel": os.path.abspath(sys.argv[0]),
            "env": {k: v for k, v in os.environ.items()
                    if k.startswith(PREFIXO) or k in ("CODEX_HOME", "TZ", "HOME", "PATH", "TMPDIR")}}


class ErroRPC(Exception):
    def __init__(self, mensagem, codigo=-32602):
        super().__init__(mensagem)
        self.codigo = codigo


def _cursor(valor):
    return base64.urlsafe_b64encode(json.dumps(valor).encode()).decode()


def _pagina(valores, params, escopo, tamanho, sobrepor=False):
    cursor = params.get("cursor")
    inicio = 0
    if cursor:
        try:
            dado = json.loads(base64.urlsafe_b64decode(cursor.encode()))
            if dado["escopo"] != escopo:
                raise ValueError("escopo")
            inicio = int(dado["posicao"])
        except (ValueError, KeyError, TypeError, AttributeError):
            raise ErroRPC("invalid continuation cursor")
    limite = max(1, min(int(params.get("limit") or tamanho), tamanho))
    fim = min(inicio + limite, len(valores))
    primeiro = inicio - 1 if sobrepor and inicio else inicio
    proximo = _cursor({"escopo": escopo, "posicao": fim}) if fim < len(valores) else None
    return {"data": valores[primeiro:fim], "nextCursor": proximo, "backwardsCursor": None}


def _desligado(argv, caminho, categoria):
    for i, a in enumerate(argv[:-1]):
        if a in ("-c", "--config"):
            opcao = argv[i + 1]
            if categoria in opcao and caminho in opcao and re.search(r"enabled\s*[:=]\s*false", opcao):
                return True
    return False


def _item_nativo(registro, thread):
    """Completa só campos de transporte omitidos na abreviação do Anexo B."""
    r = copy.deepcopy(registro)
    tipo = r["type"]
    padroes = {
        "commandExecution": {"command": "", "commandActions": [], "cwd": thread["cwd"], "status": "completed"},
        "fileChange": {"changes": [], "status": "completed"},
        "mcpToolCall": {"arguments": {}, "status": "completed"},
        "dynamicToolCall": {"arguments": {}, "status": "completed"},
        "collabAgentToolCall": {"agentsStates": {}, "receiverThreadIds": [], "senderThreadId": thread["id"], "status": "completed"},
        "subAgentActivity": {"agentPath": "agente-sintetico", "agentThreadId": CONVERSA_OUTRA},
        "webSearch": {"query": ""}, "imageView": {"path": ""},
        "imageGeneration": {"status": "completed", "result": "imagem-sintetica"},
        "sleep": {"durationMs": 1}, "enteredReviewMode": {"review": "revisão sintética"},
        "exitedReviewMode": {"review": "revisão sintética"},
    }
    for chave, valor in padroes.get(tipo, {}).items():
        r.setdefault(chave, valor)
    if tipo == "hookPrompt":
        for fragmento in r.get("fragments", []):
            fragmento.setdefault("hookRunId", "hook-sintetico")
    if tipo == "fileChange":
        for mudanca in r.get("changes", []):
            mudanca.setdefault("kind", {"type": "add"})
            mudanca.setdefault("diff", "")
    return r


def _responde_rpc(metodo, params, caso, argv):
    op = caso.get("opcoes", {})
    permitidos = {
        "initialize": {"clientInfo", "capabilities"},
        "thread/read": {"threadId", "includeTurns"},
        "thread/turns/list": {"threadId", "sortDirection", "limit", "cursor", "itemsView"},
        "thread/items/list": {"threadId", "turnId", "sortDirection", "limit", "cursor"},
        "skills/list": {"cwds", "forceReload"}, "config/read": {"cwd", "includeLayers"},
        "mcpServerStatus/list": {"cursor", "limit", "detail", "serverName", "threadId"},
    }
    if metodo not in permitidos:
        raise ErroRPC("method not found: " + metodo, -32601)
    if set(params) - permitidos[metodo]:
        raise ErroRPC("unknown parameter: " + ", ".join(sorted(set(params) - permitidos[metodo])))
    if metodo == "initialize":
        if "clientInfo" not in params:
            raise ErroRPC("clientInfo is required")
        return {"userAgent": "codex-simulado/0.166.0", "codexHome": os.environ.get("CODEX_HOME", str(Path.home() / ".codex")),
                "platformFamily": "unix", "platformOs": "macos" if sys.platform == "darwin" else "linux"}
    if metodo == "skills/list":
        skills = copy.deepcopy(op.get("skills", []))
        for s in skills:
            if _desligado(argv, s["path"], "skills") and not op.get("skill_persistente"):
                s["enabled"] = False
        return {"data": [{"cwd": p, "skills": skills, "errors": []}
                         for p in (params.get("cwds") or [os.getcwd()])]}
    if metodo in ("config/read", "mcpServerStatus/list"):
        servidores = copy.deepcopy(op.get("mcp", []))
        configs = {}
        camadas = {}
        for s in servidores:
            desligado = _desligado(argv, s["name"], "mcp_servers") and not op.get("mcp_persistente")
            s["enabled"] = bool(s.get("enabled", True) and not desligado)
            conf = {"command": "servidor-sintetico", "enabled": s["enabled"]}
            configs[s["name"]] = conf
            camadas.setdefault(s.get("camada", "system"), {})[s["name"]] = conf
        if metodo == "config/read":
            layers = [{"name": {"type": camada, "file": str(_registro() / (camada + ".toml"))},
                       "version": "sintetica", "config": {"mcp_servers": conf}}
                      for camada, conf in camadas.items()]
            return {"config": {"mcp_servers": configs, "model": "gpt-6-luna", "model_reasoning_effort": "xhigh"},
                    "origins": {}, "layers": layers if params.get("includeLayers") else None}
        data = [{"name": s["name"], "authStatus": "unsupported", "tools": {}, "resources": [],
                 "resourceTemplates": [], "runtimeStatus": "connected" if s["enabled"] else None}
                for s in servidores if not params.get("serverName") or params["serverName"] == s["name"]]
        return _pagina(data, params, "mcp", int(op.get("pagina_mcp", 25)))
    threads = caso.get("threads", [caso])
    atual = next((c for c in threads if c.get("thread", {}).get("id") == params.get("threadId")), None)
    if atual is None:
        raise ErroRPC("thread not found")
    turnos = atual.get("turns", [])
    thread = copy.deepcopy(atual["thread"])
    modo = thread.get("historyMode", "legacy")
    if metodo == "thread/read":
        primeiro = turnos[0].get("startedAt", 0) if turnos else 0
        ultimo = turnos[-1].get("startedAt", 0) if turnos else 0
        base = {"cliVersion": "0.166.0", "createdAt": primeiro, "updatedAt": ultimo, "ephemeral": False,
                "modelProvider": "openai", "preview": "histórico sintético", "projectId": None,
                "sessionId": thread["id"], "source": "cli", "status": {"type": "notLoaded"}, "turns": []}
        base.update(thread)
        base["turns"] = copy.deepcopy(turnos) if params.get("includeTurns") else []
        for t in base["turns"]:
            t["items"] = [_item_nativo(r, thread) for r in t["items"]]
        return {"thread": base}
    if metodo == "thread/turns/list":
        view = params.get("itemsView", "summary")
        if view not in ("notLoaded", "summary", "full"):
            raise ErroRPC("invalid itemsView")
        data = copy.deepcopy(turnos)
        if params.get("sortDirection", "desc") == "desc":
            data.reverse()
        for t in data:
            t["itemsView"] = view
            if view == "notLoaded":
                t["items"] = []
            else:
                t["items"] = [_item_nativo(r, thread) for r in t["items"]]
        pagina = _pagina(data, params, "turns:" + thread["id"], int(op.get("pagina_turnos", 100)),
                         op.get("sobrepor_turnos", False))
        atraso = op.get("atraso", {})
        if atraso.get("metodo") == metodo and any(t["id"] == atraso.get("turno") for t in pagina["data"]):
            time.sleep(float(atraso.get("segundos", 0)) * _escala())
        return pagina
    if modo == "legacy":
        raise ErroRPC("thread/items/list is not available for legacy history")
    turno_id = params.get("turnId")
    selecionados = [t for t in turnos if not turno_id or t["id"] == turno_id]
    if turno_id and not selecionados:
        raise ErroRPC("turn not found")
    atraso = op.get("atraso", {})
    if atraso.get("metodo", "thread/items/list") == metodo and atraso.get("turno") == turno_id:
        time.sleep(float(atraso.get("segundos", 0)) * _escala())
    data = [{"turnId": t["id"], "item": _item_nativo(r, thread), "startedAtMs": t.get("startedAt", 0) * 1000,
             "completedAtMs": None} for t in selecionados for r in t["items"]]
    if params.get("sortDirection", "asc") == "desc":
        data.reverse()
    cursor = params.get("cursor")
    ancora_inicial = isinstance(cursor, dict)
    if ancora_inicial:
        if set(cursor) != {"type", "itemId"} or cursor["type"] != "item" or not turno_id:
            raise ErroRPC("item anchor requires turnId")
        ancora = next((i for i, e in enumerate(data) if e["item"]["id"] == cursor["itemId"]), None)
        if ancora is None:
            raise ErroRPC("cursor.itemId does not identify an item in the requested history scope")
        # Converter a âncora para o cursor da coleção inteira mantém a paginação.
        params = dict(params, cursor=_cursor({"escopo": "items:" + thread["id"] + ":" + str(turno_id),
                                             "posicao": ancora + 1}))
    return _pagina(data, params, "items:" + thread["id"] + ":" + str(turno_id),
                   int(op.get("pagina_registros", 25)), op.get("sobrepor_registros", False) and not ancora_inicial)


def _app_server(argv):
    if "--listen" not in argv or argv[argv.index("--listen") + 1] != "stdio://":
        raise SystemExit("app-server simulado exige --listen stdio://")
    n = _contador("servidores")
    grava_json(_registro() / ("servidor-%06d.json" % n), _metadados(argv))
    inicializado = False
    notificado = False
    caso = json_de(os.environ[PREFIXO + "SIMULADO_HISTORICO"])
    for linha in sys.stdin:
        pedido = json.loads(linha)
        metodo, params = pedido.get("method"), pedido.get("params") or {}
        if "id" not in pedido:
            if metodo == "initialized":
                notificado = True
            _log("rpc.jsonl", {"method": metodo, "params": params, "notificacao": True})
            continue
        resultado = {"id": pedido["id"]}
        registro = {"method": metodo, "params": params, "pid": os.getpid()}
        _log("rpc-inicios.jsonl", registro)
        try:
            if metodo != "initialize" and not (inicializado and notificado):
                raise ErroRPC("initialize and initialized are required", -32600)
            resultado["result"] = _responde_rpc(metodo, params, caso, argv)
            if metodo == "initialize":
                inicializado = True
            registro["quantidade"] = len(resultado["result"].get("data", []))
        except ErroRPC as erro:
            resultado["error"] = {"code": erro.codigo, "message": str(erro)}
            registro["error"] = resultado["error"]
        _log("rpc.jsonl", registro)
        print(json.dumps(resultado, ensure_ascii=False), flush=True)


def _exec(argv):
    entrada = sys.stdin.read()
    n = _contador("chamadas")
    chamada = dict(_metadados(argv), stdin=entrada, inicio=time.time())
    if "--output-schema" in argv:
        chamada["esquema"] = json_de(argv[argv.index("--output-schema") + 1])
    grava_json(_registro() / ("chamada-%06d.json" % n), chamada)
    lista = os.environ.get(PREFIXO + "SIMULADO", "")
    arquivos = json.loads(lista) if lista.lstrip().startswith("[") else [p for p in lista.split(",") if p]
    if not arquivos:
        raise SystemExit("nenhuma resposta sintética configurada")
    sequencia = _contador("plano-" + hashlib.sha256(lista.encode()).hexdigest()[:16])
    valor = json_de(arquivos[min(sequencia - 1, len(arquivos) - 1)])
    envelope = valor if "resposta" in valor or "texto_bruto" in valor else {"resposta": valor}
    time.sleep(float(envelope.get("espera_segundos", 0)) * _escala())
    resposta = envelope.get("texto_bruto", json.dumps(envelope.get("resposta"), ensure_ascii=False))
    if "-o" in argv:
        Path(argv[argv.index("-o") + 1]).write_text(resposta, encoding="utf-8")
    eventos = envelope.get("eventos", [
        {"type": "thread.started", "thread_id": CONVERSA_B1}, {"type": "turn.started"},
        {"type": "item.completed", "item": {"id": "item_0", "type": "agent_message", "text": resposta}},
        {"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 0, "output_tokens": 20}},
    ])
    for evento in eventos:
        print(json.dumps(evento, ensure_ascii=False), flush=True)
    if envelope.get("stderr"):
        print(envelope["stderr"], file=sys.stderr, flush=True)
    _log("exec-fins.jsonl", {"chamada": n, "fim": time.time(), "codigo": int(envelope.get("codigo_de_saida", 0))})
    raise SystemExit(int(envelope.get("codigo_de_saida", 0)))


def main():
    argv = sys.argv[1:]
    if "app-server" in argv:
        _app_server(argv)
    elif "exec" in argv:
        _exec(argv)
    else:
        raise SystemExit("Codex simulado aceita somente app-server ou exec")


if __name__ == "__main__":
    main()
# prova C18: alteração proposital de critério congelado
