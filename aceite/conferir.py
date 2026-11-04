#!/usr/bin/env python3
"""Conferidor do Codex (Anexo F). Adaptado do Anth, tag v2.0.0, em U2.

Uso: python3 aceite/conferir.py <pasta de documentação> --idioma pt-br|en [--roteiro aceite/roteiro.json]

Imprime o total de verificações rodadas, aprovadas e reprovadas e sai com código 0 só se todas as que rodaram
passarem. Uma verificação que não encontra o objeto que deve conferir reprova. Sem `--roteiro`, F9 aparece como
"não se aplica" e fica fora do total.
"""
import argparse
from datetime import datetime
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

TEXTOS = {
    "pt-br": {
        "conversas": "conversas", "d1": "1-indice.md", "d2": "2-conversa-integral.md", "d3": "3-conversa-simplificada.md",
        "d4": "4-decisoes.md", "d5": "5-funcoes.md", "d6": "6-pendencias.md", "d7": "7-handoff.md",
        "origem": "Origem", "situacao": "Situação", "intervalo": "Intervalo da rodada",
        "ultima_coberta": "Última mensagem coberta", "sem_integral": "sem conversa integral",
        "assunto": "**Assunto: ", "autores": ["Usuário", "Codex", "Plano", "Evento"],
        "situacoes": {"d4": ["vigente", "substituída por ", "revogada em "], "d5": ["concluída", "substituída por ", "desfeita em "],
                      "d6": ["aberta", "encerrada em "]},
        "substituida": "substituída por ", "ferramenta": "Ferramenta: ", "oculto": "[oculto]",
        "secoes_d7": ["Objetivo", "Pautas e estado atual", "Próximo passo", "Decisões e autorizações vigentes",
                      "Restrições vigentes", "Descobertas e tentativas descartadas", "Pendências e compromissos", "Lacunas", "Como retomar"],
        "nao_se_aplica": "não se aplica", "migracao": "migração",
    },
    "en": {
        "conversas": "conversations", "d1": "1-index.md", "d2": "2-full-conversation.md", "d3": "3-simplified-conversation.md",
        "d4": "4-decisions.md", "d5": "5-functions.md", "d6": "6-pending.md", "d7": "7-handoff.md",
        "origem": "Source", "situacao": "Status", "intervalo": "Run range",
        "ultima_coberta": "Last covered message", "sem_integral": "no full conversation",
        "assunto": "**Subject: ", "autores": ["User", "Codex", "Plan", "Event"],
        "situacoes": {"d4": ["in force", "replaced by ", "revoked in "], "d5": ["done", "replaced by ", "undone in "],
                      "d6": ["open", "closed in "]},
        "substituida": "replaced by ", "ferramenta": "Tool: ", "oculto": "[hidden]",
        "secoes_d7": ["Goal", "Topics and current state", "Next step", "Decisions and authorizations in force",
                      "Constraints in force", "Findings and discarded approaches", "Pending items and commitments", "Gaps", "How to resume"],
        "nao_se_aplica": "not applicable", "migracao": "migration",
    },
}
RE_MENSAGEM = re.compile(r"^## (M(\d+)-([A-Za-z0-9-]+)) · (\d{4}-\d{2}-\d{2} \d{2}:\d{2} [+-]\d{2}:\d{2}) · (.+)$")
RE_BLOCO = re.compile(r"^## M(\d+)-([A-Za-z0-9-]+) a M(\d+)-([A-Za-z0-9-]+)$")
RE_ORIGEM_FINAL = re.compile(r"\((M\d+-[A-Za-z0-9-]+(?: a M\d+-[A-Za-z0-9-]+)?(?:, M\d+-[A-Za-z0-9-]+(?: a M\d+-[A-Za-z0-9-]+)?)*)\)$")
RE_ID_MENSAGEM = re.compile(r"\bM(\d+)-([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\b")
RE_ID_ITEM = re.compile(r"\b((?:D|F|PD)\d+-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\b")
RE_ITEM = re.compile(r"^### ((?:D|F|PD)(\d+)-([A-Za-z0-9-]+))$")
RE_CODIGO = re.compile(r"(?:[0-9a-f]{8}|[0-9a-f]{12}|antigo[0-9a-f]{4})")
RE_REGISTROS = re.compile(r"^<!-- registros: ([^\s/]+/[^\s/]+) ([^\s/]+/[^\s/]+) -->$")


def le(caminho):
    return Path(caminho).read_text(encoding="utf-8")


def ancoras_markdown(texto):
    """Âncoras explícitas e títulos Markdown, com sufixos para títulos repetidos."""
    ancoras, usados = set(), set()
    cerca, tamanho, anterior = None, 0, ""
    for linha in texto.splitlines():
        if cerca:
            if re.fullmatch(r" {0,3}" + re.escape(cerca) + "{" + str(tamanho) + r",}[ \t]*", linha):
                cerca = None
            continue
        m = re.fullmatch(r" {0,3}(`{3,}|~{3,})(.*)", linha)
        if m and (m[1][0] == "~" or "`" not in m[2]):
            cerca, tamanho, anterior = m[1][0], len(m[1]), ""
            continue
        if linha.startswith(("    ", "\t")):
            anterior = ""
            continue
        ancoras.update(re.findall(r'<[^>]*\b(?:id|name)=["\']([^"\']+)["\'][^>]*>', linha))
        m = re.match(r"^ {0,3}#{1,6}(?:[ \t]+|$)(.*)$", linha)
        titulo = re.sub(r"[ \t]+#+[ \t]*$", "", m[1]).strip() if m else None
        if not m and anterior and re.fullmatch(r" {0,3}(?:=+|-+)[ \t]*", linha):
            titulo = anterior.strip()
        if titulo is not None:
            titulo = re.sub(r"!?\[([^]]*)\]\([^)]+\)", r"\1", titulo)
            titulo = re.sub(r"<[^>]*>", "", titulo)
            base = re.sub(r"[^\w -]", "", titulo.lower()).replace(" ", "-")
            ancora, n = base, 0
            while ancora in usados:
                n += 1
                ancora = base + "-" + str(n)
            usados.add(ancora)
        anterior = linha if linha.strip() and not m else ""
    return ancoras | usados


class Conferencia:
    def __init__(self, pasta, idioma, roteiro):
        self.pasta = Path(pasta)
        self.t = TEXTOS[idioma]
        self.idioma = idioma
        self.roteiro = json.loads(le(roteiro)) if roteiro else None
        if roteiro and (not isinstance(self.roteiro, dict) or len(self.roteiro.get("mensagens", [])) != 6):
            raise ValueError("o roteiro deve conter as 6 mensagens de F-C")
        self.resultados = {}
        self.falhas = {}

    def falha(self, f, mensagem):
        self.falhas.setdefault(f, []).append(mensagem)

    # --- apoio -----------------------------------------------------------------------------------------------
    def pastas_de_conversa(self):
        base = self.pasta / self.t["conversas"]
        return sorted(p for p in base.iterdir() if p.is_dir()) if base.is_dir() else []

    def migrada(self, pasta):
        d7 = pasta / self.t["d7"]
        return d7.exists() and f"- {self.t['ultima_coberta']}: {self.t['sem_integral']}" in le(d7)

    def mensagens(self, pasta):
        """Lista de (n, codigo, autor, corpo, registros) do documento 2 de uma pasta de conversa."""
        d2 = pasta / self.t["d2"]
        if not d2.exists():
            return []
        # O comentário distingue mensagens de títulos; F2 valida o cabeçalho depois.
        linhas = le(d2).split("\n")
        inicios = [i for i, linha in enumerate(linhas)
                   if re.match(r"^## M\d+-", linha) and i + 1 < len(linhas)
                   and linhas[i + 1].startswith("<!-- registros:")]
        saida = []
        for k, i in enumerate(inicios):
            fim = inicios[k + 1] if k + 1 < len(inicios) else len(linhas)
            m = RE_MENSAGEM.match(linhas[i])
            registros = linhas[i + 1] if i + 1 < len(linhas) else ""
            corpo = "\n".join(linhas[i + 2:fim]).strip("\n")
            saida.append((int(m.group(2)) if m else None, m.group(3) if m else None, m.group(5) if m else linhas[i], corpo, registros, linhas[i]))
        return saida

    def ids_de_mensagens(self):
        ids = set()
        for pasta in self.pastas_de_conversa():
            for n, codigo, *_ in self.mensagens(pasta):
                if n is not None:
                    ids.add(f"M{n}-{codigo}")
        return ids

    def itens(self, nome):
        caminho = self.pasta / self.t[nome]
        if not caminho.exists():
            return []
        saida, atual = [], None
        for linha in le(caminho).split("\n"):
            m = RE_ITEM.match(linha)
            if m:
                atual = {"id": m.group(1), "texto": "", "campos": {}}
                saida.append(atual)
            elif atual is not None and linha.startswith("- ") and ":" in linha:
                chave, _, valor = linha[2:].partition(":")
                atual["campos"][chave.strip()] = valor.strip()
            elif atual is not None and linha.strip():
                atual["texto"] = (atual["texto"] + "\n" + linha.strip()).strip()
        return saida

    def ids_de_itens(self):
        return {i["id"] for nome in ("d4", "d5", "d6") for i in self.itens(nome)}

    def mensagens_do_roteiro(self, pasta):
        """Encontra os 6 pedidos em ordem, na mesma conversa, após a ocultação."""
        fixos = self.roteiro["textos_fixos"][self.idioma]
        textos = self.roteiro.get("mensagens_no_documento_2", self.roteiro["mensagens"])
        localizadas, posicao = {}, 0
        msgs = self.mensagens(pasta)
        for i, texto in enumerate(textos, 1):
            texto = texto.replace("{oculto}", fixos["oculto"])
            for pos in range(posicao, len(msgs)):
                n, codigo, autor, corpo, *_ = msgs[pos]
                if n is not None and autor == self.t["autores"][0] and texto in corpo:
                    localizadas[i] = (f"M{n}-{codigo}", pos)
                    posicao = pos + 1
                    break
        return localizadas

    def ultima_no_indice(self, pasta):
        d1 = self.pasta / self.t["d1"]
        if not d1.is_file():
            return None
        alvo = f"({self.t['conversas']}/{pasta.name}/)"
        linhas = [l for l in le(d1).splitlines() if l.startswith("|") and alvo in l]
        if len(linhas) != 1:
            return None
        colunas = [c.strip() for c in linhas[0].strip().strip("|").split("|")]
        return colunas[2] if len(colunas) == 6 else None

    # --- verificações ----------------------------------------------------------------------------------------
    def f1(self):
        for nome in ("d1", "d4", "d5", "d6"):
            if not (self.pasta / self.t[nome]).is_file():
                self.falha("F1", f"falta {self.t[nome]}")
        if not (self.pasta / self.t["conversas"]).is_dir():
            self.falha("F1", f"falta a pasta {self.t['conversas']}/")
        if not self.pastas_de_conversa():
            self.falha("F1", "nenhuma pasta de conversa")
        for pasta in self.pastas_de_conversa():
            if not (pasta / self.t["d7"]).exists():
                self.falha("F1", f"falta {pasta.name}/{self.t['d7']}")
            elif not self.migrada(pasta):
                for nome in ("d2", "d3"):
                    if not (pasta / self.t[nome]).exists():
                        self.falha("F1", f"falta {pasta.name}/{self.t[nome]}")

    def f2(self):
        objeto = False
        for pasta in self.pastas_de_conversa():
            if self.migrada(pasta) or not (pasta / self.t["d2"]).is_file():
                continue
            objeto = True
            vistos = set()
            esperado = 1
            msgs = self.mensagens(pasta)
            if not msgs:
                self.falha("F2", f"{pasta.name}: documento 2 sem mensagens")
            for n, codigo, autor, corpo, registros, cabecalho in msgs:
                if n is None:
                    self.falha("F2", f"{pasta.name}: cabeçalho fora do formato: {cabecalho}")
                    continue
                if n != esperado:
                    self.falha("F2", f"{pasta.name}: esperado M{esperado}, veio M{n}")
                esperado = n + 1
                if not RE_CODIGO.fullmatch(codigo) or not pasta.name.endswith("-" + codigo):
                    self.falha("F2", f"{pasta.name}: código incompatível em M{n}: {codigo}")
                try:
                    datetime.strptime(RE_MENSAGEM.fullmatch(cabecalho).group(4), "%Y-%m-%d %H:%M %z")
                except ValueError:
                    self.falha("F2", f"{pasta.name}: data inválida em M{n}")
                if autor not in self.t["autores"]:
                    self.falha("F2", f"{pasta.name}: autor desconhecido em M{n}: {autor}")
                m = RE_REGISTROS.fullmatch(registros)
                if not m:
                    self.falha("F2", f"{pasta.name}: M{n} sem o comentário de registros")
                    continue
                inicio, fim = m.groups()
                evento = autor == self.t["autores"][3]
                marcadores = [r.split("/", 1)[1] == "status" for r in (inicio, fim)]
                if evento and (inicio != fim or not all(marcadores)):
                    self.falha("F2", f"{pasta.name}: Evento M{n} deve usar o mesmo <turno>/status nos 2 limites")
                elif not evento and any(marcadores):
                    self.falha("F2", f"{pasta.name}: M{n} usa status sem autor Evento")
                for r in set(m.groups()):
                    if r in vistos:
                        self.falha("F2", f"{pasta.name}: registro {r} aparece em 2 mensagens")
                    vistos.add(r)
        if not objeto:
            self.falha("F2", "nenhuma conversa com documento 2")

    def f3(self):
        objeto = False
        for pasta in self.pastas_de_conversa():
            d3 = pasta / self.t["d3"]
            if not d3.exists():
                continue
            objeto = True
            esperado = 1
            partes = le(d3).split("\n## ")[1:]
            if not partes:
                self.falha("F3", f"{pasta.name}: documento 3 sem blocos")
            for parte in partes:
                linhas = ("## " + parte).split("\n")
                m = RE_BLOCO.match(linhas[0])
                if not m:
                    self.falha("F3", f"{pasta.name}: bloco fora do formato: {linhas[0]}")
                    continue
                a, b = int(m.group(1)), int(m.group(3))
                if m.group(2) != m.group(4) or not pasta.name.endswith("-" + m.group(2)):
                    self.falha("F3", f"{pasta.name}: códigos incompatíveis no bloco {linhas[0]}")
                if a != esperado or b < a:
                    self.falha("F3", f"{pasta.name}: bloco {linhas[0]} não segue M{esperado}")
                esperado = b + 1
                paragrafos = [p.strip() for p in "\n".join(linhas[1:]).split("\n\n") if p.strip()]
                if not paragrafos or not paragrafos[0].startswith(self.t["assunto"]) or not paragrafos[0].endswith("**"):
                    self.falha("F3", f"{pasta.name}: bloco {linhas[0]} sem a linha de assunto")
                if len(paragrafos) < 2:
                    self.falha("F3", f"{pasta.name}: bloco {linhas[0]} sem parágrafo com origem")
                for p in paragrafos[1:]:
                    if not RE_ORIGEM_FINAL.search(p.replace("\n", " ")):
                        self.falha("F3", f"{pasta.name}: parágrafo sem origem no bloco {linhas[0]}: {p[:60]}")
            d7 = pasta / self.t["d7"]
            cobertas = (re.findall(r"^- " + re.escape(self.t["ultima_coberta"]) + r": (.+)$", le(d7), re.M)
                        if d7.is_file() else [])
            ultima = cobertas[0] if len(cobertas) == 1 else None
            final = f"M{esperado - 1}-{pasta.name[11:]}"
            if ultima != final:
                self.falha("F3", f"{pasta.name}: fim do documento 3 {final} difere do documento 7 {ultima!r}")
            indice = self.ultima_no_indice(pasta)
            if indice != ultima or indice is None:
                self.falha("F3", f"{pasta.name}: última mensagem do índice {indice!r} difere do documento 7 {ultima!r}")
            if self.roteiro:
                pedidos = self.mensagens_do_roteiro(pasta)
                if 6 in pedidos and esperado - 1 < int(RE_ID_MENSAGEM.fullmatch(pedidos[6][0]).group(1)):
                    self.falha("F3", f"{pasta.name}: cobertura não alcança o pedido da mensagem 6 de F-C")
        if not objeto:
            self.falha("F3", "nenhum documento 3")

    def f4(self):
        ids = set()
        mensagens = self.ids_de_mensagens()
        todos_itens = self.ids_de_itens()

        def mensagem_valida(valor):
            return RE_ID_MENSAGEM.fullmatch(valor) is not None and valor in mensagens

        def intervalo_valido(valor):
            partes = valor.split(" a ")
            if len(partes) != 2 or not all(mensagem_valida(p) for p in partes):
                return False
            a, b = (RE_ID_MENSAGEM.fullmatch(p) for p in partes)
            return a[2] == b[2] and int(a[1]) <= int(b[1])

        def origem_valida(valor):
            for parte in valor.split(","):
                parte = parte.strip()
                if mensagem_valida(parte) or intervalo_valido(parte) or parte in todos_itens:
                    continue
                if parte in ("index.md", ".state") or re.fullmatch(r"handoff-\d{8}-\d{6}(?:-[A-Za-z0-9]+)*\.md", parte):
                    continue
                return False
            return bool(valor)

        for nome in ("d4", "d5", "d6"):
            if not (self.pasta / self.t[nome]).exists():
                self.falha("F4", f"falta {self.t[nome]}")
                continue
            for linha in le(self.pasta / self.t[nome]).splitlines():
                if linha.startswith("### ") and not RE_ITEM.fullmatch(linha):
                    self.falha("F4", f"{self.t[nome]}: identificador fora do formato: {linha}")
            for item in self.itens(nome):
                tipo = {"d4": "D", "d5": "F", "d6": "PD"}[nome]
                if not re.fullmatch(tipo + r"[1-9]\d*-" + RE_CODIGO.pattern, item["id"]):
                    self.falha("F4", f"{self.t[nome]}: identificador incompatível: {item['id']}")
                if item["id"] in ids:
                    self.falha("F4", f"identificador repetido: {item['id']}")
                ids.add(item["id"])
                if not item["texto"]:
                    self.falha("F4", f"{item['id']} sem texto")
                for campo in (self.t["origem"], self.t["situacao"], self.t["intervalo"]):
                    if not item["campos"].get(campo):
                        self.falha("F4", f"{item['id']} sem o campo {campo}")
                situacao = item["campos"].get(self.t["situacao"], "")
                permitidas = self.t["situacoes"][nome]
                valida = situacao == permitidas[0]
                if situacao.startswith(self.t["substituida"]) and nome != "d6":
                    alvo = situacao[len(self.t["substituida"]):]
                    valida = RE_ID_ITEM.fullmatch(alvo) is not None and alvo in todos_itens
                elif situacao.startswith(permitidas[-1]):
                    resto = situacao[len(permitidas[-1]):]
                    if nome == "d6":
                        encerramento = re.fullmatch(r"(M\d+-[A-Za-z0-9-]+) \(([^()\n]+)\)", resto)
                        valida = bool(encerramento and encerramento[2].strip() and mensagem_valida(encerramento[1]))
                    else:
                        valida = mensagem_valida(resto)
                if not valida:
                    self.falha("F4", f"{item['id']} com situação não permitida: {situacao}")
                origem = item["campos"].get(self.t["origem"], "")
                if not origem_valida(origem):
                    self.falha("F4", f"{item['id']} com origem inválida: {origem}")
                intervalo = item["campos"].get(self.t["intervalo"], "")
                if intervalo != self.t["migracao"] and not intervalo_valido(intervalo):
                    self.falha("F4", f"{item['id']} com intervalo inválido: {intervalo}")
        for nome in ("d4", "d5", "d6"):
            for item in self.itens(nome):
                situacao = item["campos"].get(self.t["situacao"], "")
                if situacao.startswith(self.t["substituida"]):
                    alvo = situacao[len(self.t["substituida"]):].strip()
                    if alvo not in ids:
                        self.falha("F4", f"{item['id']} substituído por item inexistente: {alvo}")

    def f5(self):
        objeto = False
        for pasta in self.pastas_de_conversa():
            d7 = pasta / self.t["d7"]
            if not d7.exists():
                continue
            objeto = True
            secoes = [l[3:].strip() for l in le(d7).split("\n") if l.startswith("## ")]
            obrigatorias = [titulo for titulo in secoes if titulo in self.t["secoes_d7"]]
            if obrigatorias != self.t["secoes_d7"]:
                self.falha("F5", f"{pasta.name}: seções do documento 7: {secoes}")
        if not objeto:
            self.falha("F5", "nenhum documento 7")

    def f6(self):
        d1 = self.pasta / self.t["d1"]
        if not d1.exists():
            self.falha("F6", "falta o documento 1")
            return
        texto = le(d1)
        alvos = re.findall(r"\]\(([^)]+)\)", texto)
        if not alvos or not self.pastas_de_conversa():
            self.falha("F6", "índice sem links ou sem pastas de conversa")
        for alvo in alvos:
            url = urlsplit(alvo)
            if url.scheme in ("http", "https"):
                continue
            if url.scheme:
                self.falha("F6", f"esquema incompatível com link relativo: {alvo}")
                continue
            caminho = self.pasta / unquote(url.path) if url.path else d1
            if not caminho.exists():
                self.falha("F6", f"link quebrado: {alvo}")
            elif url.fragment and (not caminho.is_file() or unquote(url.fragment) not in ancoras_markdown(le(caminho))):
                self.falha("F6", f"âncora inexistente: {alvo}")
        for pasta in self.pastas_de_conversa():
            if f"({self.t['conversas']}/{pasta.name}/)" not in texto:
                self.falha("F6", f"conversa fora do índice: {pasta.name}")

    def f7(self):
        objeto = False
        frases_total, longas = 0, 0
        for caminho in self.documentos_3_a_7():
            objeto = True
            for paragrafo in self.paragrafos_contaveis(le(caminho)):
                frases = [f for f in re.split(r"(?<=[.!?])\s+", paragrafo) if f.strip()]
                if len(frases) > 6:
                    self.falha("F7", f"{caminho.name}: parágrafo com {len(frases)} frases")
                for f in frases:
                    palavras = len(f.split())
                    frases_total += 1
                    if palavras > 25:
                        longas += 1
                    if palavras > 40:
                        self.falha("F7", f"{caminho.name}: frase com {palavras} palavras")
        if frases_total and longas / frases_total > 0.10:
            self.falha("F7", f"{longas} de {frases_total} frases passam de 25 palavras nos documentos 3 a 7")
        if not objeto or not frases_total:
            self.falha("F7", "nenhum texto contável nos documentos 3 a 7")

    def documentos_3_a_7(self):
        saida = [self.pasta / self.t[n] for n in ("d4", "d5", "d6") if (self.pasta / self.t[n]).exists()]
        for pasta in self.pastas_de_conversa():
            saida += [pasta / self.t[n] for n in ("d3", "d7") if (pasta / self.t[n]).exists()]
        return saida

    def paragrafos_contaveis(self, texto):
        rotulos = ({"Conversa", "Pasta do projeto", "Fuso dos horários", "Origem", "Situação", "Intervalo da rodada",
                    "Recomendação", "Depende de", "Última mensagem coberta", "Data da rodada", "Redator"}
                   if self.idioma == "pt-br" else
                   {"Conversation", "Project folder", "Time zone", "Source", "Status", "Run range", "Recommendation",
                    "Depends on", "Last covered message", "Run date", "Writer"})
        metadado = re.compile(r"^- (?:" + "|".join(re.escape(r) for r in rotulos) + r"): ")
        cerca, tamanho, indentado, nivel_citacao, recuo_lista = None, 0, False, 0, 0
        paragrafos, atual = [], []

        def termina_paragrafo():
            if atual:
                paragrafos.append(" ".join(atual))
                atual.clear()

        for linha in texto.split("\n"):
            # O conteúdo da cerca é literal após os recuos da citação e da lista.
            if cerca:
                conteudo = linha
                if nivel_citacao:
                    prefixo = re.match(r"^ {0,3}(?:>[ \t]?){" + str(nivel_citacao) + r"}", linha)
                    if prefixo:
                        conteudo = linha[prefixo.end():]
                    else:
                        cerca = None
                if cerca:
                    expandida = conteudo.expandtabs(4)
                    if recuo_lista and expandida.startswith(" " * recuo_lista):
                        conteudo = expandida[recuo_lista:]
                    if re.fullmatch(r" {0,3}" + re.escape(cerca) + "{" + str(tamanho) + r",}[ \t]*", conteudo):
                        cerca = None
                    continue
            citacao = re.match(r"^ {0,3}(?:>[ \t]?)+", linha)
            nivel = citacao[0].count(">") if citacao else 0
            if nivel != nivel_citacao:
                termina_paragrafo()
                cerca, indentado, nivel_citacao, recuo_lista = None, False, nivel, 0
            if citacao:
                linha = linha[citacao.end():]
            marcador_lista = re.match(r"^ {0,3}(?:[-+*]|\d+[.)])[ \t]+", linha)
            if marcador_lista:
                recuo_lista = len(marcador_lista[0].expandtabs(4))
            elif recuo_lista and linha.strip():
                expandida = linha.expandtabs(4)
                if expandida.startswith(" " * recuo_lista):
                    linha = expandida[recuo_lista:]
                else:
                    recuo_lista = 0
            m = re.fullmatch(r" {0,3}(`{3,}|~{3,})(.*)", linha)
            if m and (m[1][0] == "~" or "`" not in m[2]):
                termina_paragrafo()
                cerca, tamanho, indentado = m[1][0], len(m[1]), False
                continue
            recuada = linha.startswith(("    ", "\t"))
            if indentado:
                if recuada or not linha.strip():
                    continue
                indentado = False
            if recuada and not atual:
                indentado = True
                continue
            # Uma linha setext transforma as linhas anteriores em título.
            if re.fullmatch(r" {0,3}(?:=+|-+)[ \t]*", linha):
                atual.clear()
                continue
            if re.match(r"^ {0,3}#{1,6}(?:[ \t]+|$)", linha) or linha.startswith(self.t["assunto"]) or metadado.match(linha) \
                    or re.match(r"^ {0,3}(?:\||<!--)", linha) \
                    or re.fullmatch(r" {0,3}(?:(?:\*[ \t]*){3,}|(?:_[ \t]*){3,}|(?:-[ \t]*){3,})", linha):
                termina_paragrafo()
                continue
            lista = re.match(r"^ {0,3}(?:[-+*]|\d+[.)])[ \t]+(.*)$", linha)
            if lista:
                termina_paragrafo()
                linha = lista[1]
            if not linha.strip():
                termina_paragrafo()
                continue
            limpa = RE_ID_MENSAGEM.sub("", RE_ID_ITEM.sub("", linha))
            limpa = re.sub(r"\((?:\s*a\s*|,\s*)*\)", "", limpa)
            atual.append(limpa.strip())
        termina_paragrafo()
        return paragrafos

    def f8(self):
        mensagens = self.ids_de_mensagens()
        itens = self.ids_de_itens()
        objeto = False
        for caminho in self.documentos_3_a_7():
            objeto = True
            texto = le(caminho)
            for n, codigo in set(RE_ID_MENSAGEM.findall(texto)):
                if f"M{n}-{codigo}" not in mensagens:
                    self.falha("F8", f"{caminho.name}: mensagem inexistente M{n}-{codigo}")
            for item in set(RE_ID_ITEM.findall(texto)):
                if item not in itens:
                    self.falha("F8", f"{caminho.name}: item inexistente {item}")
        if not objeto:
            self.falha("F8", "nenhum documento 3 a 7")

    def f9(self):
        r = self.roteiro
        fixos = r["textos_fixos"][self.idioma]
        candidatas = []
        for pasta in self.pastas_de_conversa():
            localizadas = self.mensagens_do_roteiro(pasta)
            if len(localizadas) == 6:
                candidatas.append((pasta, localizadas))
        if len(candidatas) != 1:
            self.falha("F9", f"esperada 1 conversa com os 6 pedidos do roteiro em ordem; encontradas {len(candidatas)}")
            return
        pasta, localizadas = candidatas[0]
        msgs = self.mensagens(pasta)
        d2 = le(pasta / self.t["d2"])
        a = r["assercoes"]["documento_2"]
        for s in a["contem"]:
            if s not in d2:
                self.falha("F9", f"documento 2 sem {s!r}")
        if a.get("contem_oculto") and fixos["oculto"] not in d2:
            self.falha("F9", f"documento 2 sem {fixos['oculto']}")
        for s in a["nao_contem"]:
            if s in d2:
                self.falha("F9", f"documento 2 contém {s!r}")
        lf = a["linha_de_ferramenta"]
        linhas = [l for l in d2.splitlines() if l.startswith(fixos["ferramenta"]) and lf["contem"] in l]
        if not linhas:
            self.falha("F9", f"documento 2 sem linha de ferramenta que contém {lf['contem']!r}")
        for nome, chave in (("d4", "documento_4"), ("d6", "documento_6"), ("d5", "documento_5")):
            regra = r["assercoes"][chave]
            origens = {localizadas[regra["origem_na_mensagem"]][0]}
            ferramenta = regra.get("ou_na_mensagem_do_codex_com_a_ferramenta")
            if ferramenta:
                pos = localizadas[regra["origem_na_mensagem"]][1]
                for n, codigo, autor, corpo, *_r in msgs[pos + 1:]:
                    if autor == self.t["autores"][0]:
                        break
                    if n is not None and autor == "Codex" and any(
                            l.startswith(fixos["ferramenta"]) and ferramenta in l for l in corpo.splitlines()):
                        origens.add(f"M{n}-{codigo}")
            encontrado = any(
                re.match(r"^" + re.escape(regra["tipo"]) + r"\d+-", i["id"])
                and origens & {f"M{n}-{codigo}" for n, codigo in RE_ID_MENSAGEM.findall(i["campos"].get(self.t["origem"], ""))}
                and regra["texto_contem"].casefold() in i["texto"].casefold()
                for i in self.itens(nome))
            if not encontrado:
                self.falha("F9", f"{self.t[nome]} sem item {regra['tipo']} com origem em {sorted(origens)} e texto {regra['texto_contem']!r}")
        resposta = r["assercoes"]["resposta_ao_pedido"]
        pos = localizadas[resposta["depois_da_mensagem"]][1]
        prefixo = resposta["linha_comeca_com"][self.idioma]
        posteriores = []
        for msg in msgs[pos + 1:]:
            if msg[2] == self.t["autores"][0]:
                break
            posteriores.append(msg)
        if not any(autor == "Codex" and any(l.startswith(prefixo) for l in corpo.splitlines())
                   for _n, _codigo, autor, corpo, *_ in posteriores):
            self.falha("F9", f"resposta ao pedido sem linha iniciada por {prefixo!r}")

    def f10(self):
        for p in self.pasta.iterdir():
            if p.name in ("index.md", ".state") or (p.name.startswith("handoff-") and p.suffix == ".md"):
                self.falha("F10", f"arquivo do formato antigo na raiz: {p.name}")

    # --- execução ---------------------------------------------------------------------------------------------
    def roda(self):
        verificacoes = [("F1", self.f1), ("F2", self.f2), ("F3", self.f3), ("F4", self.f4), ("F5", self.f5), ("F6", self.f6),
                        ("F7", self.f7), ("F8", self.f8), ("F9", self.f9), ("F10", self.f10)]
        for nome, funcao in verificacoes:
            if nome == "F9" and not self.roteiro:
                self.resultados[nome] = self.t["nao_se_aplica"]
                continue
            try:
                funcao()
            except Exception as erro:  # noqa: BLE001
                self.falha(nome, f"erro na verificação: {erro!r}")
            self.resultados[nome] = "reprovada" if nome in self.falhas else "aprovada"
        rodadas = [n for n, r in self.resultados.items() if r != self.t["nao_se_aplica"]]
        aprovadas = [n for n in rodadas if self.resultados[n] == "aprovada"]
        reprovadas = [n for n in rodadas if self.resultados[n] == "reprovada"]
        for nome in verificacoes:
            n = nome[0]
            detalhes = "; ".join(self.falhas.get(n, []))
            print(f"{n}: {self.resultados[n]}" + (f" · {detalhes}" if detalhes else ""))
        print(f"verificações rodadas: {len(rodadas)}, aprovadas: {len(aprovadas)}, reprovadas: {len(reprovadas)}")
        return 0 if not reprovadas else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pasta")
    ap.add_argument("--idioma", choices=["pt-br", "en"], required=True)
    ap.add_argument("--roteiro")
    args = ap.parse_args()
    if not Path(args.pasta).is_dir():
        print(f"pasta inexistente: {args.pasta}")
        return 2
    try:
        return Conferencia(args.pasta, args.idioma, args.roteiro).roda()
    except (OSError, ValueError) as erro:
        print(f"falha ao ler a entrada: {erro}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
