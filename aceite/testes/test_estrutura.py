"""T01 a T03. Expectativas da seção 5.1 e dos Anexos B, D e E."""
import copy
import datetime
import json

from apoio import (CASOS, CODIGO_B1, CONVERSA_B1, PREFIXO, TEXTO, CasoDeAceite,
                   grava_json, inventario, json_de, le, tag, turno, usuario)


class Estrutura(CasoDeAceite):
    def test_R01_cria_a_documentacao_e_trata_pastas_sem_gravacao(self):
        """T01. Árvore inicial, projeto sem gravação e dados sem gravação."""
        self.amb.historico_b1()
        self.sucesso(self.amb.rodada(), "R01")
        esperado = {TEXTO["d" + str(n)] for n in (1, 4, 5, 6)}
        esperado.update(TEXTO["conversas"] + "/2026-03-14-" + CODIGO_B1 + "/" + TEXTO["d" + str(n)]
                        for n in (2, 3, 7))
        encontrado = {p.relative_to(self.amb.doc).as_posix() for p in self.amb.doc.rglob("*") if p.is_file()}
        self.assertEqual(encontrado, esperado, "R01: a primeira rodada deve produzir a árvore de 7 documentos do Anexo E")
        for n in (1, 4, 5, 6):
            self.assertTrue(le(self.amb.d(n)).startswith("# "), "R01: documento sem título")
        amb = self.novo_ambiente()
        amb.historico_b1()
        amb.projeto.chmod(0o555)
        try:
            r = amb.rodada()
            aviso = amb.escrita()
        finally:
            amb.projeto.chmod(0o755)
        self.assertEqual(r.returncode, 1, "R01: projeto sem gravação deve falhar")
        self.assertFalse(amb.doc.exists(), "R01: projeto sem gravação recebeu arquivos")
        self.assertTrue(any(l.get("resultado") == "falhou" and l.get("motivo") for l in amb.rodadas()), "R01: falta o motivo")
        self.assertEqual(aviso.returncode, 0, "R01: o gatilho precisa liberar a compactação")
        self.assertTrue(json.loads(aviso.stdout).get("systemMessage"), "R01: falta o aviso de R24")
        for comando in ("rodada", "copia", "escrita"):
            amb = self.novo_ambiente()
            amb.historico_b1()
            resposta = amb.resposta("rodada-b1")
            amb.dados.chmod(0o555)
            try:
                kw = {"respostas": (), "extra": {PREFIXO + "SIMULADO": str(resposta), "TMPDIR": str(amb.raiz)}}
                if comando == "rodada":
                    r = amb.rodada(**kw)
                    self.assertEqual(r.returncode, 1, "R01: dados sem gravação devem encerrar o pedido com 1")
                    self.assertTrue(r.stdout.strip().splitlines()[-1].startswith(TEXTO["falha"]))
                else:
                    r = getattr(amb, comando)(**kw)
                    self.assertEqual(r.returncode, 0, "R01: dados sem gravação não podem reprovar o hook")
            finally:
                amb.dados.chmod(0o700)

    def test_R02_identifica_conversa_data_fork_migracao_e_colisao(self):
        """T02. Data inicial, meia-noite, migração, fork, entrada inválida e colisão."""
        caso = self.amb.historico_b1()
        self.sucesso(self.amb.copia(), "R02")
        texto = self.documento(2, "R02")
        self.assertIn("- " + TEXTO["conversa"] + ": " + CONVERSA_B1, texto,
                      "R02: a cópia deve identificar a conversa dentro da pasta com a data inicial")
        self.assertFalse(self.amb.d(3).exists())
        self.assertFalse(self.amb.d(7).exists())
        self.sucesso(self.amb.rodada(), "R02")
        self.documento(3, "R02")
        self.documento(7, "R02")
        amb = self.novo_ambiente()
        meia_noite = int(datetime.datetime(2026, 3, 14, 23, 59, 30, tzinfo=datetime.timezone.utc).timestamp())
        amb.grava_historico({"thread": caso["thread"], "turns": [turno("noite", [usuario("n1", "Antes da meia-noite.")], meia_noite),
                              turno("dia", [usuario("n2", "No dia seguinte.")], meia_noite + 60)]})
        self.sucesso(amb.copia(), "R02")
        self.assertTrue(amb.d(2, data="2026-03-14").is_file(), "R02: a data deve vir do primeiro turno")
        self.assertFalse(amb.pasta_conversa(data="2026-03-15").exists())
        # Migração automática antes da cópia, com a pasta antiga reaproveitada.
        amb = self.novo_ambiente()
        amb.formato_antigo("continua")
        amb.historico_b1()
        r = amb.rodada(respostas=("b3/redator/continua", "rodada-b1"))
        self.sucesso(r, "R02")
        self.documento(7, "R02", amb, data="2026-03-01")
        self.documento(2, "R02", amb, data="2026-03-01")
        self.assertFalse(amb.pasta_conversa().exists(), "R02: a rodada criou uma segunda pasta para a conversa migrada")
        chamadas = amb.chamadas()
        self.assertEqual(len(chamadas), 2)
        self.assertIn("CONTINUIDADE-MIGRADA", tag(chamadas[1]["stdin"], "handoff_anterior"))
        # Fork com turnos herdados. session_id, cwd do evento e variável herdada são armadilhas.
        amb = self.novo_ambiente()
        evento = json_de(CASOS / "b1/fork.json")
        nova = "01a2b3c4-5d6e-7f80-9a1b-0c1d2e3f4a5b"
        fork = copy.deepcopy(caso)
        fork["thread"].update(id=nova, sessionId=CONVERSA_B1, forkedFromId=CONVERSA_B1)
        fork["turns"].append(turno("t6", [usuario("r23", "Pedido próprio do fork.")], 1773501600))
        amb.grava_historico({"threads": [caso, fork]})
        self.sucesso(amb.copia(evento=json.dumps(evento), extra={"CODEX_THREAD_ID": CONVERSA_B1}), "R02")
        texto = self.documento(2, "R02", amb, codigo="2e3f4a5b")
        self.assertIn(nova, texto)
        self.assertIn("Quero seguir o sitema", texto)
        self.assertIn("M15-2e3f4a5b", texto)
        self.assertIn("Pedido próprio do fork.", texto)
        self.assertFalse(amb.pasta_conversa().exists(), "R02: o session_id de origem foi usado para o fork")
        resp = json.loads(le(amb.resposta("rodada-b1")).replace(CODIGO_B1, "2e3f4a5b"))
        arq = amb.respostas / "fork.json"
        grava_json(arq, resp)
        self.sucesso(amb.escrita(evento=json.dumps(evento), respostas=(), extra={PREFIXO + "SIMULADO": str(arq)}), "R02")
        self.documento(7, "R02", amb, codigo="2e3f4a5b")
        for comando in ("copia", "escrita"):
            for caminho in (None, "/tmp/rollout-sem-uuid.jsonl", "/tmp/rollout-uuid-invalido.jsonl.zst"):
                amb = self.novo_ambiente()
                amb.historico_b1()
                evento = json.loads(amb.evento())
                if caminho is None:
                    evento.pop("transcript_path")
                else:
                    evento["transcript_path"] = caminho
                r = getattr(amb, comando)(evento=json.dumps(evento))
                self.sucesso(r, "R02")
                self.assertFalse(amb.rpc(), "R02: entrada sem conversa não pode ler o histórico")
                self.assertEqual(len(amb.rodadas()), 1)
                self.assertIn("conversa não identificada", amb.rodadas()[0]["motivo"])
        amb = self.novo_ambiente()
        outra = copy.deepcopy(caso)
        outra_id = "01a2b3c5-5d6e-7f80-9a1b-f1e24e5f6a7b"
        outra["thread"]["id"] = outra_id
        amb.grava_historico({"threads": [caso, outra]})
        self.sucesso(amb.copia(), "R02")
        self.sucesso(amb.copia(outra_id), "R02")
        texto = self.documento(2, "R02", amb, codigo="f1e24e5f6a7b")
        self.assertIn(outra_id, texto)
        self.assertTrue(any(l.get("conversa") == outra_id and l.get("motivo") for l in amb.rodadas()), "R02: colisão sem registro")

    def test_R03_grava_somente_na_documentacao_e_nos_dados(self):
        """T03. Rodada completa, pacote intacto e ausência de gravações externas."""
        self.amb.historico_b1()
        (self.amb.projeto / "fonte.txt").write_text("Fonte sintética preservada.\n", encoding="utf-8")
        antes = inventario(self.amb.raiz, excluir=(self.amb.doc, self.amb.dados))
        pacote_antes = inventario(self.amb.pacote)
        r = self.amb.rodada()
        self.sucesso(r, "R03")
        self.terminou("R03")
        self.assertTrue(self.amb.chamadas(), "R03: a prova exige uma chamada ao redator simulado")
        self.documento(7, "R03")
        self.assertEqual(inventario(self.amb.raiz, excluir=(self.amb.doc, self.amb.dados)), antes,
                         "R03: uma gravação atingiu caminho fora das 2 pastas permitidas")
        self.assertEqual(inventario(self.amb.pacote), pacote_antes, "R03: o pacote instalado foi alterado")
        self.assertEqual(self.amb.dados.stat().st_mode & 0o777, 0o700, "R03: os dados devem usar modo 0700")
        self.assertFalse(list(self.amb.dados.rglob("*.tmp")), "R03: a rodada deixou temporários sem finalidade")


if __name__ == "__main__":
    import unittest
    unittest.main()
