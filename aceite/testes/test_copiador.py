"""T04 a T10. Histórico sintético e expectativas literais do Anexo B."""
import hashlib
import json
import re

from apoio import (CASOS, CODIGO_B1, CONVERSA_B1, IDIOMA, TEXTO, CasoDeAceite,
                   corpo_do_documento_2, json_de, le, mensagens, turno, usuario)


class Copiador(CasoDeAceite):
    def test_R04_acrescenta_so_o_novo_e_retoma_pela_ancora(self):
        """T04. 2 modos, status, turno em andamento, turno ou âncora removidos e conversa ausente."""
        for modo in ("paginated", "legacy"):
            amb = self.amb if modo == "paginated" else self.novo_ambiente()
            amb.historico_b1(modo)
            self.sucesso(amb.copia(), "R04")
            antes = self.documento(2, "R04", amb).encode()
            self.assertEqual(corpo_do_documento_2(antes.decode()), le(CASOS / "b1" / ("esperado-" + IDIOMA + ".md")),
                             "R04: a cópia inicial deve registrar as mensagens que a segunda rodada preservará")
            total_rpc = len(amb.rpc())
            amb.segunda_rodada()
            self.sucesso(amb.copia(), "R04")
            depois = amb.d(2).read_bytes()
            self.assertEqual(hashlib.sha256(depois[:len(antes)]).digest(), hashlib.sha256(antes).digest(), "R04: bytes anteriores mudaram")
            self.assertEqual(depois[len(antes):].decode().strip() + "\n", le(CASOS / "b1" / ("esperado-m15-" + IDIOMA + ".md")))
            self.assertFalse(any(l.get("params", {}).get("turnId") == "t5" for l in amb.rpc()[total_rpc:]),
                             "R04: o turno encerrado por status deve ser ultrapassado sem âncora")
            self.sucesso(amb.copia(), "R04")
            self.assertEqual(amb.d(2).read_bytes(), depois)
            self.assertFalse(any(l.get("params", {}).get("cursor") == {"type": "item", "itemId": "status"} for l in amb.rpc()), "R04: status não é âncora nativa")
            chamadas = [l for l in amb.rpc() if l["method"] == "thread/turns/list"]
            self.assertTrue(chamadas)
            self.assertTrue(all(l["params"].get("itemsView") == ("notLoaded" if modo == "paginated" else "full") for l in chamadas))
            self.assertTrue(all(l["params"].get("limit") == 100 and l["params"].get("sortDirection") == "desc" for l in chamadas))
            leituras = [l for l in amb.rpc() if l["method"] == "thread/read"]
            self.assertTrue(leituras)
            self.assertTrue(all(l["params"].get("threadId") == CONVERSA_B1 and l["params"].get("includeTurns") is False for l in leituras))
            registros = [l for l in amb.rpc() if l["method"] == "thread/items/list"]
            self.assertTrue(all(l["params"].get("turnId") and l["params"].get("sortDirection") == "asc" for l in registros))
            for servidor in amb.servidores():
                argv = servidor["argv"]
                self.assertEqual(argv[argv.index("--listen") + 1], "stdio://")
                for recurso in ("hooks", "plugins"):
                    self.assertTrue(any(argv[i:i + 2] == ["--disable", recurso] for i in range(len(argv) - 1)))
            if modo == "legacy":
                self.assertFalse(any(l["method"] == "thread/items/list" for l in amb.rpc()), "R04: legacy deve usar os itens de turns/list")
            # Turno em andamento. O término da cópia anterior separa as mensagens.
            amb = self.novo_ambiente()
            caso = amb.historico_b1(modo)
            caso["turns"].append(json_de(CASOS / "b1/em-andamento.json"))
            amb.grava_historico(caso)
            self.sucesso(amb.copia(), "R04")
            primeiro = self.documento(2, "R04", amb).encode()
            caso["turns"][-1]["items"].append({"id": "r24", "type": "agentMessage", "text": "Anotado o azul."})
            caso["turns"][-1]["status"] = "completed"
            amb.grava_historico(caso)
            self.sucesso(amb.copia(), "R04")
            texto = le(amb.d(2))
            self.assertTrue(texto.encode().startswith(primeiro))
            self.assertIn("## M16-" + CODIGO_B1, texto)
            self.assertIn("<!-- registros: t6/r24 t6/r24 -->", texto)
            self.assertEqual(texto.count("Anotado o azul."), 1)
            if modo == "paginated":
                self.assertTrue(any(l.get("params", {}).get("cursor") == {"type": "item", "itemId": "r23"} for l in amb.rpc()))
        t1 = "019ca100-0000-7000-8000-000000000001"
        t2 = "019ca101-0000-7000-8000-000000000002"
        for perdeu in ("turno", "registro"):
            amb = self.novo_ambiente()
            caso = {"thread": {"id": CONVERSA_B1, "historyMode": "paginated"}, "turns": [turno(t1, [usuario("a1", "Texto anterior.")])]}
            amb.grava_historico(caso)
            self.sucesso(amb.copia(), "R04")
            antes = self.documento(2, "R04", amb).encode()
            caso["turns"] = [] if perdeu == "turno" else [turno(t1, [])]
            caso["turns"].append(turno(t2, [usuario("a2", "Texto posterior.")], 1773501000))
            amb.grava_historico(caso)
            self.sucesso(amb.copia(), "R04")
            texto = le(amb.d(2))
            self.assertTrue(texto.encode().startswith(antes))
            self.assertIn("M2-" + CODIGO_B1, texto)
            self.assertIn("Texto posterior.", texto)
            self.assertTrue(any(l.get("motivo") for l in amb.rodadas()), "R04: perda da âncora sem registro")
            if perdeu == "registro":
                self.assertTrue(any(l.get("error", {}).get("code") == -32602 for l in amb.rpc()))
        amb = self.novo_ambiente()
        amb.historico_b1()
        self.sucesso(amb.rodada(), "R04")
        antes = {n: amb.d(n).read_bytes() for n in range(2, 8)}
        caso = json_de(amb.arquivo_historico)
        caso["thread"]["id"] = "019ca111-0000-7000-8000-000000000001"
        amb.grava_historico(caso)
        r = amb.rodada()
        self.assertEqual(r.returncode, 1)
        self.assertIn("conversa não encontrada no histórico", json.dumps(amb.rodadas(), ensure_ascii=False))
        self.assertEqual({n: amb.d(n).read_bytes() for n in range(2, 8)}, antes)

    def test_R05_cabecalhos_e_corpo_literal_sem_usuario_vazio(self):
        """T05. M1 a M14, comentários, hora do turno e usuário vazio após contexto."""
        self.amb.historico_b1()
        self.sucesso(self.amb.copia(), "R05")
        texto = self.documento(2, "R05")
        esperado = ("# " + TEXTO["integral"] + " · " + CODIGO_B1 + "\n\n- " + TEXTO["conversa"] + ": " + CONVERSA_B1 +
                    "\n- " + TEXTO["projeto"] + ": " + str(self.amb.projeto) + "\n- " + TEXTO["fuso"] + ": +00:00\n\n")
        self.assertTrue(texto.startswith(esperado), "R05: cabeçalho diferente do Anexo E")
        self.assertEqual(corpo_do_documento_2(texto), le(CASOS / "b1" / ("esperado-" + IDIOMA + ".md")))
        self.assertEqual([m[0] for m in mensagens(texto)], ["M%d-%s" % (n, CODIGO_B1) for n in range(1, 15)])
        amb = self.novo_ambiente()
        amb.grava_historico({"thread": {"id": CONVERSA_B1, "historyMode": "paginated"}, "turns": [
            turno("t1", [usuario("vazio", "  <user_instructions>contexto interno</user_instructions>"), usuario("real", "Pedido real.")])]})
        self.sucesso(amb.copia(), "R05")
        texto = self.documento(2, "R05", amb)
        self.assertEqual(len(mensagens(texto)), 1)
        self.assertIn("<!-- registros: t1/real t1/real -->", texto)
        self.assertIn("M1-" + CODIGO_B1, texto)
        self.assertNotIn("contexto interno", texto)

    def test_R06_ferramentas_em_uma_linha_sem_resultado(self):
        """T06. B1 e todos os tipos do Anexo E, alvo de 120 caracteres, vazio e senha."""
        self.amb.historico_b1()
        self.sucesso(self.amb.copia(), "R06")
        texto = self.documento(2, "R06")
        f = TEXTO["ferramenta"]
        self.assertIn(f + ("comando" if IDIOMA == "pt-br" else "command") + " · ls -la\n", texto)
        nomes = (["comando", "alteração de arquivo", "busca na web", "ver imagem", "agente", "geração de imagem"]
                 if IDIOMA == "pt-br" else ["command", "file change", "web search", "view image", "agent", "image generation"])
        registros = [usuario("u1", "Use as ferramentas.")]
        dados = [
            {"type": "commandExecution", "command": "x" * 200, "aggregatedOutput": "RESULTADO-PROIBIDO"},
            {"type": "fileChange", "changes": [{"path": "/tmp/a.txt", "diff": "DIFF-PROIBIDO"}, {"path": "/tmp/b.txt", "diff": ""}]},
            {"type": "mcpToolCall", "server": "docs", "tool": "buscar", "result": {"content": ["RESULTADO-PROIBIDO"]}},
            {"type": "dynamicToolCall", "namespace": "catalogo", "tool": "listar"},
            {"type": "dynamicToolCall", "tool": "listar"},
            {"type": "collabAgentToolCall", "tool": "spawnAgent"},
            {"type": "webSearch", "query": "manual"}, {"type": "imageView", "path": "/tmp/img.png"},
            {"type": "imageGeneration"}, {"type": "commandExecution"},
            {"type": "commandExecution", "command": "echo senha=Pl4nt@d4#2026"},
        ]
        registros.extend(dict(r, id="f%d" % n) for n, r in enumerate(dados))
        amb = self.novo_ambiente()
        amb.grava_historico({"thread": {"id": CONVERSA_B1, "historyMode": "paginated"}, "turns": [turno("t1", registros)]})
        self.sucesso(amb.copia(), "R06")
        texto = self.documento(2, "R06", amb)
        linhas = [l for l in texto.splitlines() if l.startswith(f)]
        self.assertEqual(linhas, [f + nomes[0] + " · " + "x" * 120, f + nomes[1] + " · /tmp/a.txt, /tmp/b.txt",
            f + "docs.buscar", f + "catalogo.listar", f + "listar", f + nomes[4] + " · spawnAgent", f + nomes[2] + " · manual",
            f + nomes[3] + " · /tmp/img.png", f + nomes[5], f + nomes[0], f + nomes[0] + " · echo senha=" + TEXTO["oculto"]])
        for proibido in ("x" * 121, "RESULTADO-PROIBIDO", "DIFF-PROIBIDO", "Pl4nt@d4#2026"):
            self.assertNotIn(proibido, texto)

    def test_R07_oculta_todos_os_formatos_b2_e_preserva_texto_comum(self):
        """T07. B2 do anth sem mudanças, JSON aninhado, tokens inteiros e 3 casos da spec."""
        casos = json_de(CASOS / "b2/ocultacao.json")
        exemplos = [("caso", c) for c in casos["casos"]] + [("aninhado", c) for c in casos["json_aninhado"]]
        exemplos += [("inteiro", c) for c in casos["tokens_inteiros"]] + [("spec", c) for c in casos["casos_da_spec"]]
        registros = [usuario("s%d" % n, c if tipo == "inteiro" else c["texto"]) for n, (tipo, c) in enumerate(exemplos)]
        self.amb.grava_historico({"thread": {"id": CONVERSA_B1, "historyMode": "paginated"}, "turns": [turno("t1", registros)]})
        self.sucesso(self.amb.copia(), "R07")
        saidas = mensagens(self.documento(2, "R07"))
        self.assertEqual(len(saidas), len(exemplos), "R07: todos os casos precisam passar pela cópia")
        for mensagem, (tipo, c) in zip(saidas, exemplos):
            corpo = mensagem[3].strip()
            if tipo == "inteiro":
                self.assertEqual(corpo, TEXTO["oculto"])
            elif tipo == "spec":
                self.assertEqual(corpo, c["esperado_" + IDIOMA])
            else:
                for segredo in c["ocultos"]:
                    self.assertNotIn(segredo, corpo, "R07: caso " + c["texto"][:40])
                for mantido in c.get("mantidos", []):
                    self.assertIn(mantido, corpo)
                if c["ocultos"]:
                    self.assertIn(TEXTO["oculto"], corpo)
                if tipo == "aninhado":
                    for _ in range(c["profundidade"]):
                        corpo = json.loads(corpo)
                    self.assertEqual(corpo["note"], "visible")

    def test_R08_inclui_usuario_codex_planos_eventos_e_anexos(self):
        """T08. Usuário durante o trabalho, planos, interrupção, falha longa e todos os anexos."""
        caso = self.amb.historico_b1()
        self.sucesso(self.amb.copia(), "R08")
        texto = self.documento(2, "R08")
        for autor in TEXTO["autores"]:
            self.assertIn(" · " + autor + "\n", texto)
        self.assertLess(texto.index("M10-"), texto.index("Prefira o PDF."))
        self.assertLess(texto.index("Prefira o PDF."), texto.index("M12-"))
        self.assertIn("1. Listar formatos.\n2. Comparar.", texto)
        self.assertIn("t3/status t3/status", texto)
        self.assertIn("t5/status t5/status", texto)
        anexo = usuario("anexos", "Confira os anexos.")
        anexo["content"] += [{"type": "image", "url": "data:image/png;base64,U0lOVEVUSUNP"},
            {"type": "localImage", "path": "/tmp/foto.png"}, {"type": "audio", "url": "audio-sintetico"},
            {"type": "localAudio", "path": "/tmp/voz.wav"}, {"type": "mention", "name": "relatorio.pdf", "path": "/tmp/relatorio.pdf"},
            {"type": "skill", "name": "skill-sintetica", "path": "/tmp/skill-sintetica/SKILL.md"}]
        erro = "erro sintético " + "x" * 210 + "FIM-PROIBIDO"
        caso["turns"].append(turno("t6", [anexo], 1773501000, "failed", error={"message": erro}))
        self.amb.grava_historico(caso)
        self.sucesso(self.amb.copia(), "R08")
        texto = self.documento(2, "R08")
        self.assertEqual(texto.count(TEXTO["imagem"]), 3)
        self.assertEqual(texto.count(TEXTO["audio"]), 2)
        self.assertIn(TEXTO["arquivo"] + "relatorio.pdf]", texto)
        self.assertIn(TEXTO["skill"] + "skill-sintetica]", texto)
        self.assertNotIn("U0lOVEVUSUNP", texto)
        self.assertNotIn("FIM-PROIBIDO", texto)
        self.assertIn(("A resposta falhou: " if IDIOMA == "pt-br" else "The response failed: ") + erro[:200] + ".", texto)

    def test_R09_exclui_contexto_resultados_raciocinio_e_tipos_desconhecidos(self):
        """T09. Todos os marcadores, tipos excluídos e aviso para tipo desconhecido."""
        caso = self.amb.historico_b1()
        marcadores = ["# AGENTS.md instructions", "<environment_context>", "<user_instructions>",
                      "<external_codex_apps_open_page>", "<turn_aborted>", "<subagent_notification>"]
        excluidos = ["reasoning", "functionCallOutput", "hookPrompt", "contextCompaction", "subAgentActivity", "sleep",
                     "enteredReviewMode", "exitedReviewMode", "tipoFuturo"]
        for n, marcador in enumerate(marcadores):
            caso["turns"][-1]["items"].append(usuario("ctx%d" % n, "  " + marcador + " EXCLUIR-MARCADOR-%d" % n))
        caso["turns"][-1]["items"].extend({"id": "ex%d" % n, "type": tipo, "text": "EXCLUIR-TIPO-%d" % n,
                                          "output": "EXCLUIR-TIPO-%d" % n} for n, tipo in enumerate(excluidos))
        caso["turns"][-1]["items"].append(usuario("preservar", "Mensagem real preservada."))
        self.amb.grava_historico(caso)
        self.sucesso(self.amb.copia(), "R09")
        texto = self.documento(2, "R09")
        self.assertIn("Mensagem real preservada.", texto, "R09: a prova deve conservar uma mensagem real")
        for s in ("EXCLUIR-MARCADOR-", "EXCLUIR-TIPO-", "raciocínio interno", "contexto de hook", "+teste", "regras do projeto"):
            self.assertNotIn(s, texto)
        self.assertNotRegex(texto, re.compile(r"^nota\.txt$", re.M), "R09: saída do comando entrou no documento")
        self.assertIn("tipo de registro ignorado: tipoFuturo", json.dumps(self.amb.rodadas(), ensure_ascii=False))

    def test_R10_copia_uma_vez_por_turno_e_registro(self):
        """T10. Sobreposição entre páginas e rodadas, incluindo mesmo id em outro turno."""
        for modo in ("paginated", "legacy"):
            amb = self.amb if modo == "paginated" else self.novo_ambiente()
            caso = amb.historico_b1(modo)
            caso["opcoes"] = {"pagina_turnos": 2, "pagina_registros": 3, "sobrepor_turnos": True, "sobrepor_registros": True}
            amb.grava_historico(caso)
            self.sucesso(amb.copia(), "R10")
            texto = self.documento(2, "R10", amb)
            self.assertEqual(corpo_do_documento_2(texto), le(CASOS / "b1" / ("esperado-" + IDIOMA + ".md")),
                             "R10: sobreposição de páginas deve produzir exatamente as 14 mensagens de B1")
            antes = amb.d(2).read_bytes()
            self.sucesso(amb.copia(), "R10")
            self.assertEqual(amb.d(2).read_bytes(), antes)
            amb.acrescenta(turno("t6", [usuario("r1", "Mesmo id em outro turno.")], 1773501000))
            self.sucesso(amb.copia(), "R10")
            texto = le(amb.d(2))
            self.assertEqual(len(mensagens(texto)), 15)
            self.assertEqual(texto.count("Mesmo id em outro turno."), 1)
            self.assertEqual(texto.count("Quero seguir o sitema"), 1)
            self.assertIn("<!-- registros: t6/r1 t6/r1 -->", texto)
            self.assertGreater(sum(l["method"] == "thread/turns/list" for l in amb.rpc()), 2)


if __name__ == "__main__":
    import unittest
    unittest.main()
