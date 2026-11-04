"""Additional U3/U4 checks, using only synthetic histories and the frozen fake.

No test calls an authenticated Codex or changes the acceptance criteria. These
checks also exercise the U3/U4 portions of T02/T11/T18 that currently depend on
U6 migration or on the reference files scheduled for U7.
"""

import copy
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "aceite/testes"))
from apoio import (CHAVES_HANDOFF, CODIGO_B1, CONVERSA_B1, CONVERSA_OUTRA, IDIOMA,
                   PREFIXO, SKILL_REL, TEXTO, CasoDeAceite, blocos, grava_json,
                   espera, inventario, itens, json_de, le, linhas_json, tag, turno, usuario)


def response(start, kind="D"):
    source = "M%d-%s" % (start, CODIGO_B1)
    return {
        "nada_relevante": False, "resumo": "Parte %d registrada" % start,
        "conversa_simplificada": TEXTO["assunto"] + "parte %d.**\n\nConteúdo registrado. (%s)" % (start, source),
        "itens_novos": [{"ref": "N1", "tipo": kind, "texto": "Entrega da parte %d." % start,
                         "origem": [source], "situacao": TEXTO[{"D": "vigente", "F": "concluida", "PD": "aberta"}[kind]],
                         "recomendacao": "Comparar os formatos." if kind == "PD" else "",
                         "depende_de": "O usuário decidir." if kind == "PD" else ""}],
        "mudancas": [], "handoff": {key: "PARTE-%d. N1. (%s)" % (start, source) for key in CHAVES_HANDOFF},
    }


class DocumentationV2(CasoDeAceite):
    def synthetic_response(self, amb, name, value):
        path = amb.respostas / (name + ".json")
        grava_json(path, value)
        return path

    def run_with(self, amb, paths, extra=None):
        extra = dict(extra or {})
        extra[PREFIXO + "SIMULADO"] = json.dumps([str(path) for path in paths])
        return amb.rodada(respostas=(), extra=extra)

    def test_R02_fork_collision_and_reuse_without_running_migration(self):
        original = self.amb.historico_b1()
        fork_id = "01a2b3c4-5d6e-7f80-9a1b-0c1d2e3f4a5b"
        fork = copy.deepcopy(original)
        fork["thread"].update(id=fork_id, sessionId=CONVERSA_B1, forkedFromId=CONVERSA_B1)
        self.amb.grava_historico({"threads": [original, fork]})
        event = self.amb.evento(fork_id, session_id=CONVERSA_B1, cwd="/tmp/destino-incorreto")
        self.sucesso(self.amb.copia(evento=event, extra={"CODEX_THREAD_ID": CONVERSA_B1}), "R02")
        fork_text = le(self.amb.d(2, codigo="2e3f4a5b"))
        self.assertIn(fork_id, fork_text)
        self.assertIn("Quero seguir o sitema", fork_text)
        self.assertFalse(self.amb.pasta_conversa().exists())
        other_id = "01a2b3c5-5d6e-7f80-9a1b-f1e24e5f6a7b"
        other = copy.deepcopy(original)
        other["thread"]["id"] = other_id
        self.amb.grava_historico({"threads": [original, other]})
        self.sucesso(self.amb.copia(), "R02")
        self.sucesso(self.amb.copia(other_id), "R02")
        self.assertIn(other_id, le(self.amb.d(2, codigo="f1e24e5f6a7b")))
        self.assertTrue(any("colisão" in row["motivo"] for row in self.amb.rodadas()))
        amb = self.novo_ambiente()
        amb.historico_b1()
        old_folder = amb.pasta_conversa(data="2026-03-01")
        old_folder.mkdir(parents=True)
        old_handoff = ("# Handoff · " + CODIGO_B1 + "\n\n- " + TEXTO["conversa"] + ": " + CONVERSA_B1 +
                       "\n- " + TEXTO["ultima"] + ": " + TEXTO["sem_integral"] + "\nCONTINUIDADE-ANTERIOR\n")
        amb.d(7, data="2026-03-01").write_text(old_handoff, encoding="utf-8")
        self.sucesso(amb.rodada(), "R02")
        self.assertTrue(amb.d(2, data="2026-03-01").is_file())
        self.assertFalse(amb.pasta_conversa().exists())
        self.assertEqual(tag(amb.chamadas()[0]["stdin"], "handoff_anterior"), old_handoff.strip())
        for command in ("copia", "escrita"):
            for transcript in (None, "/tmp/rollout-sem-uuid.jsonl", "/tmp/rollout-uuid-invalido.jsonl.zst"):
                amb = self.novo_ambiente()
                event = json.loads(amb.evento())
                if transcript is None:
                    event.pop("transcript_path")
                else:
                    event["transcript_path"] = transcript
                result = getattr(amb, command)(evento=json.dumps(event))
                self.sucesso(result, "R02")
                self.assertEqual(json.loads(result.stdout), {})
                self.assertEqual(len(amb.rodadas()), 1)
                self.assertEqual(amb.rodadas()[0]["motivo"], "conversa não identificada")
                self.assertEqual(amb.rpc(), [])

    def test_R02_concurrent_suffix_collision_keeps_both_transcripts(self):
        first = self.amb.historico_b1()
        other_id = "01a2b3c5-5d6e-7f80-9a1b-f1e24e5f6a7b"
        second = copy.deepcopy(first)
        second["thread"]["id"] = other_id
        self.amb.grava_historico({"threads": [first, second],
                                 "opcoes": {"atraso": {"turno": "t1", "segundos": 30}}})
        process = self.amb.inicia("copia", entrada=self.amb.evento(), respostas=())
        self.assertTrue(espera(lambda: any(
            row["method"] == "thread/items/list" and row["params"].get("threadId") == CONVERSA_B1
            for row in linhas_json(self.amb.registro_simulado / "rpc-inicios.jsonl")), 5))
        self.sucesso(self.amb.copia(other_id), "R02")
        output, error = process.communicate(timeout=6)
        self.assertEqual(process.returncode, 0, output + error)
        self.assertIn(CONVERSA_B1, le(self.amb.d(2)))
        self.assertIn(other_id, le(self.amb.d(2, codigo="f1e24e5f6a7b")))

    def test_R11_parts_publish_in_order_and_resume_partial_failure(self):
        for partial in (False, True):
            amb = self.amb if not partial else self.novo_ambiente()
            texts = ["MENSAGEM-%d. " % n + "palavra " * 100 for n in range(1, 4)]
            amb.grava_historico({"thread": {"id": CONVERSA_B1, "historyMode": "paginated"},
                                "turns": [turno("partes", [usuario("p%d" % n, text) for n, text in enumerate(texts, 1)])]})
            paths = [self.synthetic_response(amb, "parte-%d" % n, response(n, kind))
                     for n, kind in enumerate(("D", "F", "PD"), 1)]
            options = {PREFIXO + "LIMITE_DA_PARTE": "1400"}
            if partial:
                invalid = self.synthetic_response(amb, "invalida", {"resumo": "Fora do esquema"})
                result = self.run_with(amb, [paths[0], invalid], options)
                self.assertEqual(result.returncode, 1)
                self.assertTrue(any(row["resultado"] == "parcial" for row in amb.rodadas()))
                before = le(amb.d(3))
                self.assertEqual(blocos(before), ["M1-%s a M1-%s" % (CODIGO_B1, CODIGO_B1)])
                self.sucesso(self.run_with(amb, paths[1:], options), "R11")
                self.assertTrue(le(amb.d(3)).startswith(before))
            else:
                self.sucesso(self.run_with(amb, paths, options), "R11")
            calls = amb.chamadas()
            accepted = [calls[0], calls[-2], calls[-1]] if partial else calls
            self.assertEqual(len(accepted), 3)
            for n, call in enumerate(accepted, 1):
                prompt = call["stdin"]
                excerpt = tag(prompt, "trecho_novo")
                raw_excerpt = re.search(r"<trecho_novo>(.*?)</trecho_novo>", prompt, re.S)[1]
                self.assertIn(texts[n - 1], raw_excerpt)
                self.assertEqual(re.findall(r"^## (M\d+-\S+) ·", excerpt, re.M), ["M%d-%s" % (n, CODIGO_B1)])
                self.assertLessEqual(len(excerpt), 1400)
                self.assertLessEqual(len(prompt), 600000)
                if n > 1:
                    self.assertIn("D1-" + CODIGO_B1, tag(prompt, "decisoes"))
                    self.assertIn("PARTE-%d" % (n - 1), tag(prompt, "handoff_anterior"))
            self.assertIn("PARTE-3", le(amb.d(7)))
            self.assertEqual(len(blocos(le(amb.d(3)))), 3)
            for n, kind in ((4, "D"), (5, "F"), (6, "PD")):
                self.assertEqual([item["id"] for item in itens(le(amb.d(n)))], [kind + "1-" + CODIGO_B1])

    def test_R11_budget_cuts_only_writer_input_and_rejects_large_context(self):
        full = "INICIO-PRESERVAR. " + "conteúdo " * 3000 + "FIM-INTEGRAL."
        self.amb.grava_historico({"thread": {"id": CONVERSA_B1, "historyMode": "paginated"},
                                 "turns": [turno("grande", [usuario("g1", full)])]})
        reply = self.synthetic_response(self.amb, "uma", response(1))
        self.sucesso(self.run_with(self.amb, [reply], {PREFIXO + "LIMITE_DA_PARTE": "1800"}), "R11")
        prompt = self.amb.chamadas()[0]["stdin"]
        self.assertIn(full, le(self.amb.d(2)))
        self.assertNotIn("FIM-INTEGRAL", tag(prompt, "trecho_novo"))
        self.assertRegex(tag(prompt, "trecho_novo"), r"\[(?:mensagem cortada para o redator|message truncated for the writer): \d+ (?:caracteres omitidos|characters omitted)\]")
        amb = self.novo_ambiente()
        amb.grava_historico(json_de(self.amb.arquivo_historico))
        reply = self.synthetic_response(amb, "uma", response(1))
        overhead = len(prompt) - len(tag(prompt, "trecho_novo"))
        budget = overhead + 1000
        self.sucesso(self.run_with(amb, [reply], {PREFIXO + "ORCAMENTO": str(budget)}), "R11")
        self.assertLessEqual(len(amb.chamadas()[0]["stdin"]), budget)
        self.assertIn(full, le(amb.d(2)))
        self.amb.d(4).write_text(le(self.amb.d(4)) + "\n" + "documento " * 57000, encoding="utf-8")
        before = {n: self.amb.d(n).read_bytes() for n in (3, 4, 5, 6, 7)}
        self.amb.acrescenta(turno("novo", [usuario("g2", "Pedido adicional.")]))
        result = self.amb.rodada()
        self.assertEqual(result.returncode, 1)
        self.assertIn("documentos grandes demais para o redator", result.stdout)
        self.assertEqual(len(self.amb.chamadas()), 1)
        self.assertEqual({n: self.amb.d(n).read_bytes() for n in before}, before)

    def test_R11_uses_packaged_materials_verbatim_when_available(self):
        self.amb.historico_b1()
        skill = self.amb.pacote / SKILL_REL
        rules, templates = "# Regras de teste\n\nRegra exata.\n", "# Modelo de teste\n\nModelo exato.\n"
        (skill / TEXTO["regras"]).write_text(rules, encoding="utf-8")
        (skill / TEXTO["modelos"]).write_text(templates, encoding="utf-8")
        before = inventario(self.amb.pacote)
        self.sucesso(self.amb.rodada(), "R11")
        prompt = self.amb.chamadas()[0]["stdin"]
        self.assertEqual(tag(prompt, "regras_de_escrita"), rules.strip())
        self.assertEqual(tag(prompt, "modelos"), templates.strip())
        self.assertEqual(inventario(self.amb.pacote), before)

    def test_R15_R19_R20_R21_generated_documents_pass_frozen_checker_with_roteiro(self):
        script = json_de(ROOT / "aceite/roteiro.json")
        prompts = script["mensagens"]
        # The case's 6 prompts are independent of the writer implementation.
        prompts = [entry["texto"] if isinstance(entry, dict) else entry for entry in prompts]
        turns = []
        for n, prompt in enumerate(prompts, 1):
            entries = [usuario("u%d" % n, prompt)]
            if n == 4:
                entries.append({"id": "arquivo", "type": "fileChange", "changes": [{"path": str(self.amb.projeto / "nota.txt")}]})
            if n == 6:
                entries.append({"id": "resultado", "type": "agentMessage",
                                "text": TEXTO["sucesso"] + "arquivos gerados."})
            turns.append(turno("t%d" % n, entries, 1773500400 + n * 60))
        self.amb.grava_historico({"thread": {"id": CONVERSA_B1, "historyMode": "paginated"}, "turns": turns})
        def m(n):
            return "M%d-%s" % (n, CODIGO_B1)
        value = {
            "nada_relevante": False, "resumo": "Painel azul, nota.txt criado e formato do gráfico pendente",
            "conversa_simplificada": TEXTO["assunto"] + "painel azul e gráfico.**\n\nO painel deve usar azul. (%s)\n\nO arquivo nota.txt foi criado. (%s)\n\nO formato do gráfico continua pendente. (%s)" % (m(1), m(5), m(6)),
            "itens_novos": [], "mudancas": [],
            "handoff": {key: "O painel deve usar azul. O gráfico continua pendente. (%s, %s)" % (m(1), m(6)) for key in CHAVES_HANDOFF},
        }
        for n, kind, text, source in ((1, "D", "Usar azul no painel.", 1),
                                       (2, "F", "Criar o arquivo nota.txt.", 5),
                                       (3, "PD", "Escolher o formato do gráfico.", 6)):
            item = response(source, kind)["itens_novos"][0]
            item.update(ref="N%d" % n, texto=text)
            value["itens_novos"].append(item)
        path = self.synthetic_response(self.amb, "roteiro", value)
        self.sucesso(self.run_with(self.amb, [path]), "R15/R19/R20/R21")
        result = subprocess.run([sys.executable, "-B", str(ROOT / "aceite/conferir.py"), str(self.amb.doc),
                                 "--idioma", IDIOMA, "--roteiro", str(ROOT / "aceite/roteiro.json")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("10", result.stdout)
        self.assertNotIn("Pl4nt@d4#2026", le(self.amb.d(2)))

    def test_R20_unknown_summary_reference_is_retried_and_rejected(self):
        self.amb.historico_b1()
        value = json_de(self.amb.resposta("rodada-b1"))
        value["resumo"] = "Referência M999-" + CODIGO_B1
        path = self.synthetic_response(self.amb, "referencia-no-resumo", value)
        result = self.run_with(self.amb, [path])
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(self.amb.chamadas()), 2)
        self.assertFalse(self.amb.d(3).exists())
        self.assertFalse(self.amb.d(7).exists())

    def test_R29_replay_merges_with_another_conversation(self):
        first = self.amb.historico_b1()
        second = copy.deepcopy(first)
        second["thread"]["id"] = CONVERSA_OUTRA
        self.amb.grava_historico({"threads": [first, second]})
        result = self.amb.rodada(extra={PREFIXO + "INTERROMPER_EM": "meio-da-gravacao"})
        self.assertEqual(result.returncode, 1)
        other_code = CONVERSA_OUTRA[-8:]
        reply = json.loads(le(self.amb.resposta("rodada-b1")).replace(CODIGO_B1, other_code))
        path = self.synthetic_response(self.amb, "outra-conversa", reply)
        result = self.amb.rodada(CONVERSA_OUTRA, respostas=(), extra={PREFIXO + "SIMULADO": str(path)})
        self.sucesso(result, "R29")
        before = self.amb.d(2).read_bytes()
        self.sucesso(self.amb.rodada(), "R29")
        self.assertEqual(self.amb.d(2).read_bytes(), before)
        self.assertEqual(len(self.amb.chamadas()), 2)
        for n, kind in ((4, "D"), (5, "F"), (6, "PD")):
            self.assertCountEqual([item["id"] for item in itens(le(self.amb.d(n)))],
                                  [kind + "1-" + CODIGO_B1, kind + "1-" + other_code])
        self.assertFalse(list((self.amb.dados / "diarios").glob("*.json")))

    def test_R03_symlink_cannot_overwrite_an_external_file(self):
        self.amb.historico_b1()
        external = self.amb.projeto / "fonte-preservada.txt"
        external.write_text("Fonte intocada.\n", encoding="utf-8")
        path = self.amb.d(2)
        path.parent.mkdir(parents=True)
        path.symlink_to(external)
        result = self.amb.rodada()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(le(external), "Fonte intocada.\n")
        self.assertEqual(self.amb.chamadas(), [])

    def test_R12_failure_removes_temporary_writer_directory(self):
        self.amb.historico_b1()
        result = self.amb.rodada(respostas=("falha-exec",))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(list((self.amb.dados / "temporarios").iterdir()), [])
        self.assertTrue(list((self.amb.dados / "saidas").glob("*.log")))
        self.assertFalse(self.amb.d(7).exists())


if __name__ == "__main__":
    unittest.main()
