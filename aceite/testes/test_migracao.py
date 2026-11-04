"""T31 a T33. Casos B3 manuscritos e condições do Anexo E."""
import copy
import hashlib
import os
import re
import shutil

from apoio import (CASOS, CONVERSA_B1, PREFIXO, TEXTO, CasoDeAceite,
                   espera, grava_json, itens, json_de, le, sha256, tag)


class Migracao(CasoDeAceite):
    def antigos(self, amb):
        return {p.name: (os.readlink(str(p)) if p.is_symlink() else p.read_bytes())
                for p in amb.doc.iterdir() if p.name in ("index.md", ".state") or p.name.startswith("handoff-")}

    def preservados(self, amb, antes):
        self.assertEqual(self.antigos(amb), antes, "R32/R33: arquivos antigos mudaram antes de uma migração válida")

    def migrados(self, amb, conversas, arquivos):
        self.assertFalse(self.antigos(amb), "R31: arquivos do formato antigo sobraram")
        textos = "\n".join(self.documento(n, "R31", amb) for n in (4, 5, 6))
        for arquivo in arquivos:
            self.assertIn(arquivo, textos, "R31: origem antiga não foi preservada nos itens")
        for codigo, data, ident in conversas:
            texto = self.documento(7, "R31", amb, codigo=codigo, data=data)
            self.assertIn("- " + TEXTO["conversa"] + ": " + ident, texto)
            self.assertIn("- " + TEXTO["ultima"] + ": " + TEXTO["sem_integral"], texto)
            self.assertEqual(re.findall(r"^## (.+)$", texto, re.M), TEXTO["secoes_d7"])
            self.assertFalse(amb.d(2, codigo=codigo, data=data).exists())
            self.assertFalse(amb.d(3, codigo=codigo, data=data).exists())
            indice = self.documento(1, "R31", amb)
            linha = next(l for l in indice.splitlines() if l.startswith("| [" + codigo + "]"))
            campos = [c.strip() for c in linha.strip("|").split("|")]
            self.assertEqual(campos[1:3], [data, TEXTO["sem_integral"]])
        for n in (4, 5, 6):
            for item in itens(le(amb.d(n))):
                self.assertEqual(item["campos"][TEXTO["intervalo"]], TEXTO["migracao"])
        for chamada in amb.chamadas():
            entrada = chamada["stdin"]
            self.assertIsNotNone(tag(entrada, "arquivos_antigos"))
            self.assertIsNone(tag(entrada, "trecho_novo"))
            self.assertNotIn("<!-- hopper-documentation-openai", entrada)
            self.assertNotIn("REFERENCIA-EXCLUIR", entrada)
            self.assertNotIn("## Referências", entrada)

    def test_R31_migra_4_casos_anonimo_link_partes_e_concorrencia(self):
        """T31. B3 completo, origens, datas, link ignorado, anônimo, partes e trava."""
        self.amb.formato_antigo("uma")
        antes = self.antigos(self.amb)
        self.sucesso(self.amb.migrar(), "R31")
        self.assertEqual(len(self.amb.chamadas()), 1, "R31: a migração deve extrair os arquivos antigos")
        arquivos = sorted(n for n in antes if n.startswith("handoff-"))
        self.migrados(self.amb, [("a1b2c3d4", "2026-02-20", "019ca123-4000-7000-8000-1010a1b2c3d4")], arquivos)
        for n, tipo in ((4, "D"), (5, "F"), (6, "PD")):
            self.assertEqual([i["id"] for i in itens(le(self.amb.d(n)))], [tipo + "1-a1b2c3d4"])
        etapas = [l["etapa"] for l in self.amb.rodadas() if l.get("acionamento") == "migrar"]
        self.assertIn("migracao", etapas)
        self.assertIn("exclusao", etapas)
        self.assertLess(etapas.index("migracao"), etapas.index("exclusao"))
        amb = self.novo_ambiente()
        amb.formato_antigo("duas")
        shutil.copytree(str(CASOS / "b3/uma"), str(amb.projeto / "uma"))
        alvo = amb.projeto / "uma/handoff-20260220-100000-a1b2c3d4.md"
        alvo.write_text(le(alvo) + "\nLINK-NAO-ENVIAR\n", encoding="utf-8")
        antes_alvo = sha256(alvo)
        arquivos = [p.name for p in amb.doc.glob("handoff-*.md") if not p.is_symlink()]
        self.sucesso(amb.migrar(respostas=("b3/redator/duas",)), "R31")
        self.migrados(amb, [("b1c2d3e4", "2026-01-10", "019ca124-4000-7000-8000-1010b1c2d3e4"),
                            ("c1d2e3f4", "2026-01-12", "019ca125-4000-7000-8000-1010c1d2e3f4")], arquivos)
        self.assertEqual(sha256(alvo), antes_alvo, "R31: a migração alterou o alvo do link")
        self.assertNotIn("LINK-NAO-ENVIAR", amb.chamadas()[0]["stdin"])
        for n in (4, 5, 6):
            self.assertEqual(len(itens(le(amb.d(n)))), 2)
        # O caso de continuidade reaproveita a pasta, sem refazer os turnos antigos.
        amb = self.novo_ambiente()
        amb.formato_antigo("continua")
        self.sucesso(amb.migrar(respostas=("b3/redator/continua",)), "R31")
        anterior = self.documento(7, "R31", amb, data="2026-03-01")
        amb.historico_b1()
        self.sucesso(amb.rodada(), "R31")
        self.assertEqual(tag(amb.chamadas()[-1]["stdin"], "handoff_anterior"), anterior.strip())
        self.documento(2, "R31", amb, data="2026-03-01")
        self.assertFalse(amb.pasta_conversa().exists())
        # Sem UUID no nome ou nos metadados. O cálculo vem da regra explícita da spec.
        amb = self.novo_ambiente()
        nome = "handoff-20260501-120000.md"
        amb.doc.mkdir()
        shutil.copyfile(str(CASOS / "b3" / nome), str(amb.doc / nome))
        codigo = "antigo" + hashlib.sha256(nome.encode()).hexdigest()[:4]
        resposta = le(amb.resposta("b3/redator/continua")).replace(CONVERSA_B1, codigo).replace("handoff-20260301-090000-4e5f6a7b.md", nome)
        arq = amb.respostas / "anonima.json"
        arq.write_text(resposta, encoding="utf-8")
        self.sucesso(amb.migrar(respostas=(), extra={PREFIXO + "SIMULADO": str(arq)}), "R31")
        self.migrados(amb, [(codigo, "2026-05-01", codigo)], [nome])
        for n, tipo in ((4, "D"), (5, "F"), (6, "PD")):
            self.assertEqual([i["id"] for i in itens(le(amb.d(n)))], [tipo + "1-" + codigo])
        amb = self.novo_ambiente()
        amb.formato_antigo("partes")
        nomes = sorted(p.name for p in amb.doc.glob("handoff-*.md"))
        tamanhos = [len(le(amb.doc / n)) for n in nomes]
        limite = max(tamanhos) + 100
        self.assertLess(limite, sum(tamanhos))
        r = amb.migrar(respostas=("b3/redator/partes-1", "b3/redator/partes-2"), extra={PREFIXO + "LIMITE_DA_PARTE": str(limite)})
        self.sucesso(r, "R31")
        self.assertEqual(len(amb.chamadas()), 2)
        for n, c in enumerate(amb.chamadas()):
            arquivos = tag(c["stdin"], "arquivos_antigos")
            self.assertIn(nomes[n], arquivos)
            self.assertNotIn(nomes[1 - n], arquivos)
            self.assertLessEqual(len(arquivos), limite)
        self.assertIn("ROXO-PRESERVAR", tag(amb.chamadas()[1]["stdin"], "handoff_anterior"))
        final = self.documento(7, "R31", amb, codigo="d1e2f3a4", data="2026-04-01")
        self.assertIn("ROXO-PRESERVAR", final)
        self.assertIn("FIM-PRESERVAR", final)
        self.assertEqual([i["id"] for i in itens(le(amb.d(5)))], ["F1-d1e2f3a4", "F2-d1e2f3a4"])
        self.assertFalse(self.antigos(amb))
        # Duas migrações concorrentes usam apenas a interface pública.
        amb = self.novo_ambiente()
        amb.formato_antigo("uma")
        perfil = amb.respostas / "migra-lenta.json"
        grava_json(perfil, {"resposta": json_de(amb.resposta("b3/redator/uma")), "espera_segundos": 125})
        p = amb.inicia("migrar", "--pasta", str(amb.projeto), respostas=(), extra={PREFIXO + "SIMULADO": str(perfil)})
        self.assertTrue(espera(lambda: bool(amb.chamadas()), 5))
        self.sucesso(amb.migrar(), "R31")
        out, err = p.communicate(timeout=8)
        self.assertEqual(p.returncode, 0, out + err)
        self.assertEqual(len(amb.chamadas()), 1, "R31: a migração concorrente repetiu a extração")
        for n in (4, 5, 6):
            self.assertEqual(len(itens(self.documento(n, "R31", amb))), 1)
        self.assertFalse(self.antigos(amb))

    def test_R32_preserva_antigos_ate_as_4_condicoes_e_retoma_exclusao(self):
        """T32. Destino, 200 caracteres, situação, conversas, documento 7 e interrupção."""
        for defeito in ("destino", "conteudo", "situacao", "sem_conversa", "conversa_extra"):
            amb = self.amb if defeito == "destino" else self.novo_ambiente()
            amb.formato_antigo("uma")
            antes = self.antigos(amb)
            nomes = {"destino": "migracao-incompleta", "conteudo": "migracao-sem-conteudo-longo", "sem_conversa": "migracao-sem-conversa"}
            if defeito in nomes:
                resposta = amb.resposta("b3/redator/" + nomes[defeito])
            else:
                valor = json_de(amb.resposta("b3/redator/uma"))
                if defeito == "situacao":
                    valor["itens_novos"][0]["situacao"] = "situação inventada"
                else:
                    extra = copy.deepcopy(valor["handoffs_antigos"][0])
                    extra["conversa"] = "019ca999-4000-7000-8000-1010ffffffff"
                    valor["handoffs_antigos"].append(extra)
                resposta = amb.respostas / (defeito + ".json")
                grava_json(resposta, valor)
            r = amb.migrar(respostas=(), extra={PREFIXO + "SIMULADO": str(resposta)})
            self.assertEqual(r.returncode, 1, "R32: a migração inválida deve reprovar na condição " + defeito)
            self.preservados(amb, antes)
            self.assertFalse(any(l.get("etapa") == "exclusao" and l.get("resultado") == "concluída" for l in amb.rodadas()))
        # A verificação conta caracteres úteis. 199 pode ser sem conteúdo; 200 não.
        for tamanho in (199, 200):
            amb = self.novo_ambiente()
            amb.doc.mkdir()
            nome = "handoff-20260502-120000.md"
            (amb.doc / nome).write_text("x" * tamanho, encoding="utf-8")
            codigo = "antigo" + hashlib.sha256(nome.encode()).hexdigest()[:4]
            valor = json_de(amb.resposta("b3/redator/uma"))
            valor["itens_novos"] = []
            valor["sem_conteudo"] = [nome]
            valor["handoffs_antigos"][0]["conversa"] = codigo
            valor["handoffs_antigos"][0]["handoff"] = {k: "Conteúdo sintético reduzido." for k in valor["handoffs_antigos"][0]["handoff"]}
            arq = amb.respostas / "limite.json"
            grava_json(arq, valor)
            r = amb.migrar(respostas=(), extra={PREFIXO + "SIMULADO": str(arq)})
            self.assertEqual(r.returncode, 0 if tamanho == 199 else 1, "R32: limite de 200 caracteres úteis")
            self.assertEqual((amb.doc / nome).exists(), tamanho == 200)
        # Retomada entre gravação e exclusão, sem repetir extração.
        amb = self.novo_ambiente()
        amb.formato_antigo("uma")
        antes = self.antigos(amb)
        r = amb.migrar(extra={PREFIXO + "INTERROMPER_EM": "antes-da-exclusao"})
        self.assertEqual(r.returncode, 1)
        self.preservados(amb, antes)
        self.documento(7, "R32", amb, codigo="a1b2c3d4", data="2026-02-20")
        self.sucesso(amb.migrar(), "R32")
        self.assertFalse(self.antigos(amb))
        self.assertEqual(len(amb.chamadas()), 1, "R32: a retomada deve verificar os documentos já gravados")
        # A resposta continua válida. Só os documentos no disco são adulterados.
        for n in (4, 5, 6):
            for defeito in ("sem_origem", "situacao", "id_duplicado"):
                with self.subTest(documento=n, defeito=defeito):
                    amb = self.novo_ambiente()
                    amb.formato_antigo("uma")
                    antes = self.antigos(amb)
                    r = amb.migrar(extra={PREFIXO + "INTERROMPER_EM": "antes-da-exclusao"})
                    self.assertEqual(r.returncode, 1)
                    self.preservados(amb, antes)
                    originais = {d: self.documento(d, "R32", amb) for d in (4, 5, 6)}
                    esperados = {d: itens(texto) for d, texto in originais.items()}
                    for d in esperados:
                        self.assertEqual(len(esperados[d]), 1, "R32: a migração não gravou os itens antes da exclusão")
                    texto = originais[n]
                    if defeito == "sem_origem":
                        texto, qtd = re.subn(r"^- " + re.escape(TEXTO["origem"]) + r": .*\n?", "", texto, flags=re.M)
                        self.assertEqual(qtd, 1)
                    elif defeito == "situacao":
                        texto, qtd = re.subn(r"(^- " + re.escape(TEXTO["situacao"]) + r": ).*$",
                                            r"\1inventada", texto, flags=re.M)
                        self.assertEqual(qtd, 1)
                    else:
                        texto += "\n" + texto[texto.index("### "):]
                    amb.d(n).write_text(texto, encoding="utf-8")
                    r = amb.migrar()
                    if r.returncode == 0:
                        for d in esperados:
                            self.assertEqual(itens(self.documento(d, "R32", amb)), esperados[d],
                                             "R32: excluiu os antigos sem restaurar os itens válidos do documento %d" % d)
                        self.assertFalse(self.antigos(amb))
                    else:
                        self.preservados(amb, antes)
        # Documento 7 removido depois da interrupção. Só pode excluir após restaurá-lo.
        amb = self.novo_ambiente()
        amb.formato_antigo("uma")
        antes = self.antigos(amb)
        r = amb.migrar(extra={PREFIXO + "INTERROMPER_EM": "antes-da-exclusao"})
        self.assertEqual(r.returncode, 1)
        d7 = amb.d(7, codigo="a1b2c3d4", data="2026-02-20")
        self.assertTrue(d7.is_file())
        d7.unlink()
        r = amb.migrar(respostas=("b3/redator/migracao-sem-conversa",))
        if r.returncode == 0:
            texto = self.documento(7, "R32", amb, codigo="a1b2c3d4", data="2026-02-20")
            self.assertEqual(re.findall(r"^## (.+)$", texto, re.M), TEXTO["secoes_d7"])
        else:
            self.preservados(amb, antes)
        self.assertTrue(d7.exists() or self.antigos(amb) == antes, "R32: apagou os antigos sem documento 7")

    def test_R33_respeita_configuracao_e_excecoes_sem_impedir_migracao_explicita(self):
        """T33. Desligada, pasta excluída, comando explícito e padrão automático verdadeiro."""
        for excluida in (False, True):
            amb = self.amb if not excluida else self.novo_ambiente()
            amb.formato_antigo("uma")
            amb.historico_b1()
            if excluida:
                amb.configura(migracao_automatica=True, pastas_sem_migracao=[str(amb.projeto)])
            else:
                amb.configura(migracao_automatica=False)
            antes = self.antigos(amb)
            self.sucesso(amb.rodada(), "R33")
            self.terminou("R33", amb)
            self.preservados(amb, antes)
            self.assertEqual(len(amb.chamadas()), 1)
            self.assertIsNone(tag(amb.chamadas()[0]["stdin"], "arquivos_antigos"))
            self.assertNotIn("a1b2c3d4", self.documento(4, "R33", amb))
            self.sucesso(amb.migrar(), "R33")
            self.assertFalse(self.antigos(amb), "R33: configuração não deve impedir o comando migrar")
            self.assertEqual(len(amb.chamadas()), 2)
        amb = self.novo_ambiente()
        amb.formato_antigo("uma")
        amb.historico_b1()
        self.sucesso(amb.rodada(respostas=("b3/redator/uma", "rodada-b1")), "R33")
        self.assertFalse(self.antigos(amb))
        self.assertEqual(len(amb.chamadas()), 2)
        self.assertIsNotNone(tag(amb.chamadas()[0]["stdin"], "arquivos_antigos"))
        self.documento(7, "R33", amb)


if __name__ == "__main__":
    import unittest
    unittest.main()
