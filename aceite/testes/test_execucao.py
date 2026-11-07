"""T22 a T24 e T27 a T30. Apenas comandos públicos e variáveis C36."""
import datetime
import json
import os
import re
import signal
import subprocess
import sys
import time

from apoio import (CASOS, CHAVES_HANDOFF, CODIGO_B1, CONVERSA_B1, CONVERSA_OUTRA, IDIOMA, PREFIXO, TEXTO,
                   CasoDeAceite, blocos, corpo_do_documento_2, espera, grava_json,
                   inventario, itens, json_de, le, linhas_json, mensagens, turno, ultima_linha, usuario)


class Execucao(CasoDeAceite):
    def perfil(self, amb, nome, resposta="rodada-b1", espera_segundos=0, falha=False):
        p = amb.respostas / (nome + ".json")
        grava_json(p, {"resposta": json_de(amb.resposta(resposta)), "espera_segundos": espera_segundos,
                       "codigo_de_saida": 7 if falha else 0, "stderr": "falha sintética tardia" if falha else ""})
        return p

    def partes_lentas(self, amb, falha_final=False):
        """3 chamadas abaixo de 1.800 s cada, cuja soma passa de 3.500 s."""
        amb.grava_historico({"thread": {"id": CONVERSA_B1, "historyMode": "paginated"}, "turns": [
            turno("t1", [usuario("p%d" % n, "Parte %d. " % n + "palavra " * 100) for n in range(1, 4)])]})
        respostas = [self.perfil(amb, "espera-%d" % n, "rodada-nada-relevante", 1300,
                                falha=falha_final and n == 3) for n in range(1, 4)]
        return {PREFIXO + "SIMULADO": json.dumps([str(p) for p in respostas]), PREFIXO + "LIMITE_DA_PARTE": "1400"}

    def terminou_escrita(self, amb, resultado):
        return any(l.get("etapa") == "escrita" and l.get("resultado") == resultado for l in amb.rodadas())

    def encerra_gatilho(self, amb, arquivo):
        """Encerra só o grupo criado por este teste. O trabalhador deve sobreviver."""
        env = amb.ambiente((), "0.02", {PREFIXO + "SIMULADO": str(arquivo)})
        p = subprocess.Popen([sys.executable, "-B", str(amb.programa), "escrita"], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(amb.raiz),
                             env=env, start_new_session=True)
        amb.processos.append(p)
        p.stdin.write(amb.evento())
        p.stdin.close()
        p.stdin = None
        self.assertTrue(espera(lambda: bool(amb.chamadas()), 5), "R23/R24: processo separado não iniciou a escrita")
        # O intervalo corresponde a 5 a 30 s na escala do teste.
        time.sleep(0.15)
        if p.poll() is None:
            os.killpg(p.pid, signal.SIGTERM)
        p.communicate(timeout=5)
        return time.time()

    def test_R22_copia_no_prazo_libera_hook_e_recupera_o_restante(self):
        """T22. 2.000 turnos, 20.000 registros, atraso no turno, trava e falha."""
        for modo in ("paginated", "legacy"):
            amb = self.amb if modo == "paginated" else self.novo_ambiente()
            turnos = [turno("019c%04x-0000-7000-8000-%012x" % (n, n),
                             [usuario("r%d" % i, "Mensagem %d do turno %d." % (i, n)) for i in range(10)],
                             1773500400 + n) for n in range(2000)]
            amb.grava_historico({"thread": {"id": CONVERSA_B1, "historyMode": modo}, "turns": turnos})
            inicio = time.monotonic()
            r = amb.copia(escala="1", tempo=125)
            duracao = time.monotonic() - inicio
            self.sucesso(r, "R22")
            texto = self.documento(2, "R22", amb)
            self.assertEqual(len(mensagens(texto)), 20000, "R22: a cópia completa precisa incluir os 20.000 registros")
            self.assertLessEqual(duracao, 120, "R22: cópia ultrapassou 120 segundos")
            self.assertIsNot(json.loads(r.stdout).get("continue"), False)
            self.assertFalse(amb.chamadas(), "R22: cópia síncrona não chama redator")
            self.assertIn("M20000-" + CODIGO_B1, texto)
        for modo in ("paginated", "legacy"):
            amb = self.novo_ambiente()
            caso = {"thread": {"id": CONVERSA_B1, "historyMode": modo}, "turns": [
                turno("t1", [usuario("r1", "Mensagem antes do atraso.")]),
                turno("t2", [usuario("l%d" % n, "Mensagem atrasada %d." % n) for n in range(100)], 1773500460)],
                "opcoes": {"atraso": {"metodo": "thread/items/list" if modo == "paginated" else "thread/turns/list", "turno": "t2", "segundos": 150}}}
            if modo == "legacy":
                amb.grava_historico({"thread": caso["thread"], "turns": caso["turns"][:1]})
                self.sucesso(amb.copia(), "R22")
            amb.grava_historico(caso)
            inicio = time.monotonic()
            r = amb.copia(escala="0.03", tempo=6)
            duracao = time.monotonic() - inicio
            self.sucesso(r, "R22")
            self.assertLessEqual(duracao, 3 + 0.2, "R22: resposta bloqueada ultrapassou o limite de 100 segundos escalado")
            self.assertIsNot(json.loads(r.stdout).get("continue"), False)
            antes = self.documento(2, "R22", amb).encode()
            self.assertIn(b"Mensagem antes do atraso.", antes)
            self.assertLess(len(mensagens(antes.decode())), 101)
            self.assertTrue(any(l.get("motivo") for l in amb.rodadas()), "R22: interrupção por prazo precisa de motivo")
            for servidor in amb.servidores():
                try:
                    os.kill(servidor["pid"], 0)
                except ProcessLookupError:
                    pass
                else:
                    self.fail("R22: o leitor atrasado continuou vivo depois do prazo")
            caso.pop("opcoes")
            amb.grava_historico(caso)
            self.sucesso(amb.rodada(respostas=("rodada-nada-relevante",)), "R22")
            self.assertTrue(amb.d(2).read_bytes().startswith(antes))
            self.assertEqual(len(mensagens(le(amb.d(2)))), 101)
        # A primeira cópia segura a trava, sem depender do nome interno dela.
        amb = self.novo_ambiente()
        caso["thread"]["historyMode"] = "paginated"
        caso["opcoes"] = {"atraso": {"turno": "t2", "segundos": 40}}
        amb.grava_historico(caso)
        p = amb.inicia("copia", entrada=amb.evento(), respostas=(), escala="0.1")
        self.assertTrue(espera(lambda: any(l.get("params", {}).get("turnId") == "t2"
                                         for l in linhas_json(amb.registro_simulado / "rpc-inicios.jsonl")), 5))
        inicio = time.monotonic()
        r = amb.copia(escala="0.02", tempo=4)
        espera_real = time.monotonic() - inicio
        self.sucesso(r, "R22")
        self.assertGreaterEqual(espera_real, 0.25, "R22: a segunda cópia não esperou a trava")
        self.assertLess(espera_real, 2.4, "R22: a espera da trava consumiu o prazo inteiro")
        self.assertTrue(any(l.get("motivo") for l in amb.rodadas()))
        p.communicate(timeout=8)
        self.assertEqual(p.returncode, 0)
        # O mesmo limite de 100 s inclui uma espera de trava bem-sucedida.
        amb = self.novo_ambiente()
        rapido = {"thread": {"id": CONVERSA_B1, "historyMode": "paginated"},
                  "turns": [turno("t1", [usuario("r1", "Antes da espera.")])],
                  "opcoes": {"atraso": {"turno": "t1", "segundos": 20}}}
        amb.grava_historico(rapido)
        p = amb.inicia("copia", entrada=amb.evento(), respostas=(), escala="0.02")
        self.assertTrue(espera(lambda: any(l.get("params", {}).get("turnId") == "t1"
                                         for l in linhas_json(amb.registro_simulado / "rpc-inicios.jsonl")), 5))
        rapido["turns"].append(turno("t2", [usuario("r2", "Depois da espera.")], 1773500460))
        rapido["opcoes"]["atraso"] = {"turno": "t2", "segundos": 150}
        amb.grava_historico(rapido)
        inicio = time.monotonic()
        r = amb.copia(escala="0.03", tempo=6)
        self.sucesso(r, "R22")
        self.assertLessEqual(time.monotonic() - inicio, 3.2, "R22: a espera da trava ficou fora da contagem dos 100 segundos")
        p.communicate(timeout=5)
        self.assertEqual(p.returncode, 0)
        # C07. A escrita está dentro do redator; a cópia deve avançar sem esperá-lo.
        amb = self.novo_ambiente()
        amb.historico_b1()
        lenta = self.perfil(amb, "escrita-durante-copia", espera_segundos=1000)
        p = amb.inicia("escrita", entrada=amb.evento(), respostas=(), escala="0.01",
                       extra={PREFIXO + "SIMULADO": str(lenta)})
        self.assertTrue(espera(lambda: bool(amb.chamadas()), 5), "R22: a escrita lenta não iniciou o redator")
        self.assertFalse(linhas_json(amb.registro_simulado / "exec-fins.jsonl"))
        amb.segunda_rodada()
        r = amb.copia(escala="0.01", tempo=4)
        self.sucesso(r, "R22")
        self.assertIn("M15-" + CODIGO_B1, self.documento(2, "R22", amb),
                      "R22/C07: a cópia não incluiu a mensagem nova durante a escrita")
        self.assertFalse(linhas_json(amb.registro_simulado / "exec-fins.jsonl"),
                         "R22/C07: a cópia esperou o término do redator")
        out, err = p.communicate(timeout=15)
        self.assertEqual(p.returncode, 0, out + err)
        self.assertEqual(len(linhas_json(amb.registro_simulado / "exec-fins.jsonl")), 1)
        amb = self.novo_ambiente()
        amb.historico_b1()
        r = amb.copia("019ca999-0000-7000-8000-000000000001")
        self.sucesso(r, "R22")
        self.assertIsNot(json.loads(r.stdout).get("continue"), False)
        self.assertTrue(any(l.get("resultado") == "falhou" for l in amb.rodadas()))

    def test_R23_recupera_escrita_nao_iniciada_e_mantem_processo_separado(self):
        """T23. Cópia sem escrita, retomada, sessão encerrada e aviso após 3.500 s."""
        self.amb.historico_b1()
        self.sucesso(self.amb.copia(), "R23")
        antes = self.documento(2, "R23").encode()
        self.assertFalse(self.amb.chamadas())
        self.assertFalse(self.amb.d(3).exists())
        self.sucesso(self.amb.rodada(), "R23")
        self.assertEqual(blocos(self.documento(3, "R23")), ["M1-" + CODIGO_B1 + " a M14-" + CODIGO_B1],
                         "R23: a rodada seguinte deve escrever o intervalo cuja escrita não iniciou")
        self.assertEqual(self.amb.d(2).read_bytes(), antes)
        linhas = [l for l in self.amb.rodadas() if l.get("resultado") == "escrita não iniciada"]
        self.assertEqual(len(linhas), 1, "R23: falta o registro da compactação sem escrita")
        self.assertEqual(linhas[0]["conversa"], CONVERSA_B1)
        self.assertEqual(len(self.amb.chamadas()), 1)
        self.sucesso(self.amb.rodada(), "R23")
        self.assertEqual(sum(l.get("resultado") == "escrita não iniciada" for l in self.amb.rodadas()), 1)
        amb = self.novo_ambiente()
        amb.historico_b1()
        arquivo = self.perfil(amb, "sobrevive", espera_segundos=100)
        fim_do_gatilho = self.encerra_gatilho(amb, arquivo)
        self.assertTrue(espera(lambda: self.terminou_escrita(amb, "concluída"), 8), "R23: a rodada morreu com a sessão")
        self.documento(7, "R23", amb)
        final = [l for l in amb.rodadas() if l.get("etapa") == "escrita" and l.get("resultado") == "concluída"][-1]
        data = datetime.datetime.fromisoformat(final["data"].replace("Z", "+00:00")).timestamp()
        self.assertGreater(data + 1, fim_do_gatilho)
        amb = self.novo_ambiente()
        extra = self.partes_lentas(amb)
        r = amb.escrita(respostas=(), escala="0.002", extra=extra, tempo=12)
        self.sucesso(r, "R23")
        self.assertEqual(json.loads(r.stdout).get("systemMessage"), TEXTO["andamento"])
        self.assertTrue(espera(lambda: self.terminou_escrita(amb, "concluída"), 8), "R23: o processo não continuou depois do aviso")
        self.assertEqual(len(amb.chamadas()), 3)

    def test_R24_registra_falha_no_indice_e_devolve_um_aviso(self):
        """T24. Falha no exec, aviso único, falha tardia e falha depois do fim da sessão."""
        self.amb.historico_b1()
        r = self.amb.escrita(respostas=("falha-exec",))
        self.sucesso(r, "R24")
        falhas = [l for l in self.amb.rodadas() if l.get("etapa") == "escrita" and l.get("resultado") == "falhou"]
        self.assertEqual(len(falhas), 1, "R24: a falha da rodada não foi registrada")
        motivo = falhas[0]["motivo"]
        self.assertTrue(motivo)
        self.assertEqual(falhas[0]["acionamento"], "gatilho-escrita")
        aviso = json.loads(r.stdout)
        self.assertEqual(set(aviso), {"systemMessage"})
        self.assertTrue(aviso["systemMessage"].startswith(TEXTO["falha"]))
        self.assertIn(motivo, aviso["systemMessage"])
        self.assertIn(TEXTO["falhou"] + ":", self.documento(1, "R24"))
        self.assertEqual(len(self.amb.chamadas()), 1, "R24: falha do modelo não admite modelo de reserva")
        amb = self.novo_ambiente()
        extra = self.partes_lentas(amb, falha_final=True)
        r = amb.escrita(respostas=(), escala="0.002", extra=extra, tempo=12)
        self.sucesso(r, "R24")
        self.assertEqual(json.loads(r.stdout).get("systemMessage"), TEXTO["andamento"])
        self.assertTrue(espera(lambda: any(l.get("resultado") in ("falhou", "parcial") and l.get("etapa") == "escrita" for l in amb.rodadas()), 8))
        self.assertIn(TEXTO["falhou"] + ":", self.documento(1, "R24", amb))
        amb = self.novo_ambiente()
        amb.historico_b1()
        arquivo = self.perfil(amb, "falha-depois-da-sessao", espera_segundos=100, falha=True)
        self.encerra_gatilho(amb, arquivo)
        self.assertTrue(espera(lambda: self.terminou_escrita(amb, "falhou"), 8))
        self.assertIn(TEXTO["falhou"] + ":", self.documento(1, "R24", amb))

    def test_R27_serializa_rodadas_e_desiste_apos_15_minutos(self):
        """T27. Espera pela mesma conversa, nada novo e prazo de 900 s escalado."""
        for esgota in (False, True):
            amb = self.amb if not esgota else self.novo_ambiente()
            amb.historico_b1()
            lenta = self.perfil(amb, "segura-trava", espera_segundos=125)
            p = amb.inicia("rodada", "--conversa", CONVERSA_B1, respostas=(), escala="0.02", extra={PREFIXO + "SIMULADO": str(lenta)})
            self.assertTrue(espera(lambda: bool(amb.chamadas()), 5), "R27: a primeira rodada não iniciou o redator")
            inicio = time.monotonic()
            r = amb.rodada(escala="0.001" if esgota else "0.02", tempo=8)
            duracao = time.monotonic() - inicio
            if esgota:
                self.assertEqual(r.returncode, 1)
                self.assertGreaterEqual(duracao, 0.75)
                self.assertLess(duracao, 2)
                self.assertTrue(ultima_linha(r.stdout).startswith(TEXTO["falha"]))
                self.assertTrue(any(l.get("resultado") == "falhou" and l.get("motivo") for l in amb.rodadas()))
            else:
                self.sucesso(r, "R27")
                self.assertGreater(duracao, 1, "R27: a segunda rodada não esperou a primeira")
                self.assertEqual(ultima_linha(r.stdout), TEXTO["nada_novo"])
            out, err = p.communicate(timeout=8)
            self.assertEqual(p.returncode, 0, out + err)
            self.assertEqual(len(amb.chamadas()), 1, "R27: 2 redatores trabalharam na mesma conversa")
            self.assertEqual(blocos(self.documento(3, "R27", amb)), ["M1-" + CODIGO_B1 + " a M14-" + CODIGO_B1])
        # C07. Conversas diferentes compartilham os documentos 1, 4, 5 e 6.
        amb = self.novo_ambiente()
        primeira = amb.historico_b1()
        outra = json.loads(json.dumps(primeira).replace(CONVERSA_B1, CONVERSA_OUTRA))
        amb.grava_historico({"threads": [primeira, outra]})
        codigo_outro = CONVERSA_OUTRA[-8:]
        lenta = self.perfil(amb, "conversa-a-lenta", espera_segundos=125)
        resposta_b = amb.respostas / "conversa-b.json"
        # Versão 2.1: decisão vigente com o mesmo texto reaproveita o identificador; a outra conversa usa texto próprio.
        resposta_outra = json.loads(le(amb.resposta("rodada-b1")).replace(CODIGO_B1, codigo_outro))
        for item in resposta_outra["itens_novos"]:
            item["texto"] = item["texto"].rstrip(".") + " Na outra conversa."
        grava_json(resposta_b, resposta_outra)
        p = amb.inicia("rodada", "--conversa", CONVERSA_B1, respostas=(), escala="0.02",
                       extra={PREFIXO + "SIMULADO": str(lenta)})
        self.assertTrue(espera(lambda: bool(amb.chamadas()), 5), "R27: a conversa A não iniciou")
        q = amb.inicia("rodada", "--conversa", CONVERSA_OUTRA, respostas=(), escala="0.02",
                       extra={PREFIXO + "SIMULADO": str(resposta_b)})
        for processo in (p, q):
            out, err = processo.communicate(timeout=10)
            self.assertEqual(processo.returncode, 0, out + err)
        self.assertEqual(len(amb.chamadas()), 2)
        for n, tipo in ((4, "D"), (5, "F"), (6, "PD")):
            self.assertCountEqual([i["id"] for i in itens(self.documento(n, "R27", amb))],
                                  [tipo + "1-" + codigo for codigo in (CODIGO_B1, codigo_outro)],
                                  "R27/C07: a gravação perdeu o resultado de outra conversa")
        indice = self.documento(1, "R27", amb)
        for codigo in (CODIGO_B1, codigo_outro):
            self.assertEqual(indice.count("| [" + codigo + "]"), 1)
            self.assertEqual(blocos(self.documento(3, "R27", amb, codigo=codigo)),
                             ["M1-" + codigo + " a M14-" + codigo])
            self.assertIn("- " + TEXTO["ultima"] + ": M14-" + codigo,
                          self.documento(7, "R27", amb, codigo=codigo))

    def test_R28_nada_novo_preserva_documentos_e_poupa_redator(self):
        """T28. Conteúdo e mtime dos 7 documentos, chamada única e linha final literal."""
        self.amb.historico_b1()
        self.sucesso(self.amb.rodada(), "R28")
        self.terminou("R28")
        for n in range(1, 8):
            self.documento(n, "R28")
        antes = inventario(self.amb.doc)
        self.assertEqual(len(self.amb.chamadas()), 1)
        r = self.amb.rodada()
        self.sucesso(r, "R28")
        self.assertEqual(ultima_linha(r.stdout), TEXTO["nada_novo"])
        self.assertEqual(len(self.amb.chamadas()), 1)
        self.assertEqual(inventario(self.amb.doc), antes, "R28: uma rodada sem trecho novo alterou documentos")
        self.assertEqual(self.amb.rodadas()[-1]["resultado"], "nada novo")

    def test_R29_retoma_as_4_interrupcoes_sem_perda_ou_duplicacao(self):
        """T29. Meio da cópia, depois da cópia, diário e meio da gravação."""
        for etapa in ("meio-da-copia", "depois-da-copia", "depois-do-diario", "meio-da-gravacao"):
            amb = self.amb if etapa == "meio-da-copia" else self.novo_ambiente()
            amb.historico_b1()
            r = amb.rodada(extra={PREFIXO + "INTERROMPER_EM": etapa})
            self.assertEqual(r.returncode, 1, "R29: o ponto de interrupção " + etapa + " não interrompeu a rodada")
            antes = amb.d(2).read_bytes() if amb.d(2).exists() else b""
            self.sucesso(amb.rodada(), "R29")
            texto = self.documento(2, "R29", amb)
            self.assertTrue(texto.encode().startswith(antes), "R29: retomada alterou bytes completos já copiados")
            self.assertEqual(corpo_do_documento_2(texto), le(CASOS / "b1" / ("esperado-" + IDIOMA + ".md")))
            self.assertEqual(blocos(self.documento(3, "R29", amb)), ["M1-" + CODIGO_B1 + " a M14-" + CODIGO_B1])
            for n, tipo in ((4, "D"), (5, "F"), (6, "PD")):
                self.assertEqual([i["id"] for i in itens(self.documento(n, "R29", amb))], [tipo + "1-" + CODIGO_B1])
            self.assertTrue(amb.d(7).is_file(), "R29: a retomada não restaurou o documento 7 em " + etapa)
            handoff = self.documento(7, "R29", amb)
            self.assertEqual(re.findall(r"^## (.+)$", handoff, re.M), TEXTO["secoes_d7"])
            self.assertIn("- " + TEXTO["ultima"] + ": M14-" + CODIGO_B1, handoff)
            secoes = re.split(r"^## (.+)\n", handoff, flags=re.M)
            conteudos = dict(zip(secoes[1::2], (s.strip() for s in secoes[2::2])))
            esperado = json_de(amb.resposta("rodada-b1"))["handoff"]
            for chave, titulo in zip(CHAVES_HANDOFF, TEXTO["secoes_d7"]):
                conteudo = esperado[chave]
                for ref, tipo in (("N1", "D"), ("N2", "F"), ("N3", "PD")):
                    conteudo = re.sub(r"\b" + ref + r"\b", tipo + "1-" + CODIGO_B1, conteudo)
                self.assertEqual(conteudos[titulo], conteudo, "R29: seção não restaurada em " + etapa)
            self.assertEqual(self.documento(1, "R29", amb).count("| [" + CODIGO_B1 + "]"), 1)
            self.assertEqual(len(amb.chamadas()), 1, "R29: resposta já gravada no diário foi solicitada outra vez")

    def test_R30_ignora_subconversa_sem_ler_historico(self):
        """T30. Cada hook ignora agent_id, devolve sucesso e grava 1 linha do Anexo E."""
        campos = {"data", "conversa", "pasta_do_projeto", "acionamento", "etapa", "resultado", "motivo", "intervalo", "executavel", "trigger"}
        for comando in ("copia", "escrita"):
            amb = self.amb if comando == "copia" else self.novo_ambiente()
            evento = amb.evento(agent_id="subagente-sintetico", agent_type="worker")
            r = getattr(amb, comando)(evento=evento)
            self.sucesso(r, "R30")
            self.assertEqual(len(amb.rodadas()), 1, "R30: cada comando deve registrar a subconversa ignorada")
            linha = amb.rodadas()[0]
            self.assertEqual(set(linha), campos)
            self.assertEqual(linha["etapa"], "inicio-compactacao")
            self.assertEqual(linha["resultado"], "subconversa ignorada")
            self.assertEqual(linha["acionamento"], "gatilho-" + comando)
            self.assertEqual(linha["trigger"], "auto")
            self.assertTrue(datetime.datetime.fromisoformat(linha["data"].replace("Z", "+00:00")).tzinfo)
            self.assertEqual(json.loads(r.stdout), {})
            self.assertFalse(amb.servidores())
            self.assertFalse(amb.rpc())
            self.assertFalse(amb.chamadas())
            self.assertFalse(amb.doc.exists())


if __name__ == "__main__":
    import unittest
    unittest.main()
