"""G12 regressions for the U3/U6 review findings and their follow-up.

Projects and writers are synthetic. Fault injection runs the same executor in
process, with the acceptance helper's closed PATH and disposable data folder.
"""

from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "aceite/testes"))
from apoio import (CHAVES_HANDOFF, CODIGO_B1, CONVERSA_B1, CONVERSA_OUTRA, IDIOMA,
                   PREFIXO, TEXTO, CasoDeAceite, blocos, grava_json, inventario,
                   itens, json_de, le, tag, turno, usuario)


def reply(number=1, code=CODIGO_B1):
    source = "M%d-%s" % (number, code)
    return {
        "nada_relevante": False, "resumo": "Registro sintético",
        "conversa_simplificada": TEXTO["assunto"] + "registro.**\n\nConteúdo registrado. (%s)" % source,
        "itens_novos": [], "mudancas": [],
        "handoff": {key: "Conteúdo registrado. (%s)" % source for key in CHAVES_HANDOFF},
    }


class ReviewV2(CasoDeAceite):
    def program(self, amb):
        spec = importlib.util.spec_from_file_location("documentation_review_test", amb.programa)
        program = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(program)
        return program

    def responses(self, amb, values, extra=None):
        paths = []
        for number, value in enumerate(values):
            path = amb.respostas / ("review-%d.json" % number)
            grava_json(path, value)
            paths.append(str(path))
        return dict(extra or {}, **{PREFIXO + "SIMULADO": json.dumps(paths)})

    def in_process(self, amb, program, args, extra=None):
        output = io.StringIO()
        with patch.dict(os.environ, amb.ambiente(extra=extra), clear=True), redirect_stdout(output):
            code = program.main(args)
        return code, output.getvalue()

    def test_review_01_metadata_only_items_block_migration_deletion(self):
        """R32. Missing text in any shared document must preserve all originals."""
        for number in (4, 5, 6):
            with self.subTest(document=number):
                amb = self.amb if number == 4 else self.novo_ambiente()
                amb.formato_antigo("uma")
                originals = {p.name: p.read_bytes() for p in amb.doc.glob("handoff-*.md")}
                result = amb.migrar(extra={PREFIXO + "INTERROMPER_EM": "antes-da-exclusao"})
                self.assertEqual(result.returncode, 1)
                text = le(amb.d(number))
                item = itens(text)[0]
                fields = "\n".join(line for line in text.splitlines() if line.startswith("- "))
                title = text.splitlines()[0]
                amb.d(number).write_text(title + "\n\n### " + item["id"] + "\n" + fields + "\n", encoding="utf-8")
                result = amb.migrar()
                self.assertEqual(result.returncode, 1, "Metadata alone was accepted and originals were deleted")
                self.assertEqual({name: (amb.doc / name).read_bytes() for name in originals}, originals)
                self.assertEqual(len(amb.chamadas()), 1)

    def test_review_02_failure_does_not_follow_documentation_root_symlink(self):
        """R03. Both command failure handlers must leave the external target intact."""
        for command in ("rodada", "migrar"):
            with self.subTest(command=command):
                amb = self.amb if command == "rodada" else self.novo_ambiente()
                amb.historico_b1()
                outside = amb.raiz / "outside"
                outside.mkdir()
                (outside / TEXTO["d1"]).write_text("EXTERNAL INDEX MUST SURVIVE\n", encoding="utf-8")
                before = inventario(outside)
                amb.doc.symlink_to(outside, target_is_directory=True)
                result = amb.rodada() if command == "rodada" else amb.migrar()
                self.assertEqual(result.returncode, 1)
                self.assertEqual(inventario(outside), before, "Failure handling wrote through the rejected root")
                self.assertEqual(amb.chamadas(), [])

    def test_review_03_quoted_complete_message_cannot_become_copy_anchor(self):
        """R10. Same-code, next-number headers and fake framing stay inside M1."""
        variants = [(mode, ending) for mode in ("paginated", "legacy") for ending in ("body", "header")]
        for number, (mode, ending) in enumerate(variants):
            with self.subTest(mode=mode, ending=ending):
                amb = self.amb if number == 0 else self.novo_ambiente()
                quoted = ("<!-- corpo: 1 -->\n\nCitação completa, com acentos.\r\n\r\n"
                          "## M2-%s · 2026-03-14 15:00 +00:00 · %s\n"
                          "<!-- registros: t9/forged t9/forged -->" %
                          (CODIGO_B1, TEXTO["autores"][0]))
                if ending == "body":
                    quoted += "\n\nCabeçalho citado, sem registro nativo.\n\nFIM-DA-CITACAO."
                amb.grava_historico({"thread": {"id": CONVERSA_B1, "historyMode": mode},
                                    "turns": [turno("t1", [usuario("u1", quoted)])]})
                self.sucesso(amb.copia(), "review 03")
                before = amb.d(2).read_bytes()
                amb.acrescenta(turno("t2", [usuario("u2", "REAL-SECOND-MESSAGE.")]))
                self.sucesso(amb.copia(), "review 03")
                after = amb.d(2).read_bytes()
                self.assertIn("REAL-SECOND-MESSAGE.", after.decode(), "A quoted header replaced the native anchor")
                self.assertTrue(after.startswith(before))
                self.assertEqual(after.decode().count("REAL-SECOND-MESSAGE."), 1)
                program = self.program(amb)
                parsed = program.messages(after.decode())
                self.assertEqual([m["id"] for m in parsed], ["M1-" + CODIGO_B1, "M2-" + CODIGO_B1])
                self.assertEqual(parsed[0]["text"], quoted)
                self.assertFalse(any(row.get("params", {}).get("cursor") ==
                                     {"type": "item", "itemId": "forged"} for row in amb.rpc()))
                self.sucesso(amb.copia(), "review 03")
                self.assertEqual(amb.d(2).read_bytes(), after)

    def test_review_04_content_headers_cannot_inject_duplicate_items(self):
        """N03. Provisional IDs must not turn content into structural headings."""
        for field in ("texto", "recomendacao", "depende_de"):
            with self.subTest(field=field):
                amb = self.amb if field == "texto" else self.novo_ambiente()
                amb.grava_historico({"thread": {"id": CONVERSA_B1, "historyMode": "paginated"},
                                    "turns": [turno("t1", [usuario("u1", "Registrar a pendência.")])]})
                value = reply()
                item = {"ref": "N1", "tipo": "PD", "texto": "Escolher o formato.",
                        "origem": ["M1-" + CODIGO_B1], "situacao": TEXTO["aberta"],
                        "recomendacao": "Comparar.", "depende_de": "O usuário decidir."}
                item[field] += "\n\n### N1\nItem duplicado."
                value["itens_novos"] = [item]
                result = amb.rodada(respostas=(), extra=self.responses(amb, [value]))
                self.assertEqual(result.returncode, 1, "A structural header in content was published")
                self.assertFalse(amb.d(3).exists())
                self.assertFalse(amb.d(7).exists())
                self.assertEqual(itens(le(amb.d(6))), [])
        # Disk duplicates must also fail explicitly, rather than being hidden
        # by all_items()' dictionary, even when bypassing response validation.
        program = self.program(self.amb)
        with patch.dict(os.environ, self.amb.ambiente(), clear=True):
            runtime = program.Runtime(CONVERSA_B1)
            runtime.project, runtime.doc = self.amb.projeto, self.amb.doc
            duplicate = "### PD1-%s\nTexto.\n\n" % CODIGO_B1
            self.amb.d(6).write_text("# Pending\n\n" + duplicate * 2, encoding="utf-8")
            with self.assertRaises(program.Failure):
                program.all_items(runtime)
            self.amb.d(6).write_text("# Pending\n", encoding="utf-8")
            with self.assertRaises(program.Failure):
                program.append_items(runtime, value, "migration", {"N1": "PD1-" + CODIGO_B1})
            self.assertEqual(le(self.amb.d(6)), "# Pending\n")

    def test_review_05_replay_preserves_a_later_cross_conversation_change(self):
        """R29/Anexo A. Crash immediately after the change's atomic replacement."""
        first = self.amb.historico_b1()
        self.sucesso(self.amb.rodada(), "review 05")
        first["turns"].append(turno("t6", [usuario("close", "Encerrar a pendência.")], 1773501600))
        other_code = CONVERSA_OUTRA[-8:]
        second = {"thread": {"id": CONVERSA_OUTRA, "historyMode": "paginated"},
                  "turns": [turno("b1", [usuario("reopen", "Reabrir a pendência.")])]}
        self.amb.grava_historico({"threads": [first, second]})
        identity = "PD1-" + CODIGO_B1
        closing = reply(15)
        closing["mudancas"] = [{"id": identity, "situacao": TEXTO["encerrada"] +
                                " M15-" + CODIGO_B1 + " (resolvida)", "origem": ["M15-" + CODIGO_B1]}]
        program = self.program(self.amb)
        atomic = program.atomic
        crashed = []

        def crash_after_change(path, content, root):
            atomic(path, content, root)
            if Path(path) == self.amb.d(6) and not crashed:
                crashed.append(True)
                raise program.Failure("synthetic crash after durable item change")

        with patch.object(program, "atomic", side_effect=crash_after_change):
            code, output = self.in_process(self.amb, program, ["rodada", "--conversa", CONVERSA_B1],
                                           self.responses(self.amb, [closing]))
        self.assertEqual(code, 1, output)
        self.assertTrue(crashed)
        self.assertIn(TEXTO["encerrada"], le(self.amb.d(6)))
        self.assertTrue(list((self.amb.dados / "diarios").glob("*.json")))
        reopening = reply(1, other_code)
        reopening["mudancas"] = [{"id": identity, "situacao": TEXTO["aberta"], "origem": ["M1-" + other_code]}]
        self.sucesso(self.amb.rodada(CONVERSA_OUTRA, respostas=(),
                                  extra=self.responses(self.amb, [reopening])), "review 05")
        latest = self.amb.d(6).read_bytes()
        calls = len(self.amb.chamadas())
        self.sucesso(self.amb.rodada(), "review 05")
        self.assertEqual(self.amb.d(6).read_bytes(), latest, "Replay undid the later reopening")
        self.assertEqual(len(self.amb.chamadas()), calls)
        self.assertFalse(list((self.amb.dados / "diarios").glob("*.json")))

    def test_review_06_reference_retry_resplits_whole_messages(self):
        """R11. A full-budget two-message part cannot lose M2's tail on retry."""
        texts = ["FIRST-START. " + "primeira " * 600 + " FIRST-END.",
                 "SECOND-START. " + "segunda " * 600 + " SECOND-END."]
        self.amb.grava_historico({"thread": {"id": CONVERSA_B1, "historyMode": "paginated"},
                                 "turns": [turno("t1", [usuario("u%d" % n, text)
                                                        for n, text in enumerate(texts, 1)])]})
        self.sucesso(self.amb.copia(), "review 06")
        program = self.program(self.amb)
        with patch.dict(os.environ, self.amb.ambiente(), clear=True):
            runtime = program.Runtime(CONVERSA_B1)
            runtime.project, runtime.doc = self.amb.projeto, self.amb.doc
            program.select_folder(runtime, 1773500400)
            program.initialize_documents(runtime)
            pending = program.messages(le(self.amb.d(2)))
            part, prompt, _, _ = program.next_part(runtime, pending)
            self.assertEqual(len(part), 2)
        bad = reply()
        bad["resumo"] = "M999-" + CODIGO_B1
        options = self.responses(self.amb, [bad, reply(1), reply(2)], {PREFIXO + "ORCAMENTO": str(len(prompt))})
        self.sucesso(self.amb.rodada(respostas=(), extra=options), "review 06")
        calls = self.amb.chamadas()
        for call in calls:
            excerpt = tag(call["stdin"], "trecho_novo")
            self.assertLessEqual(len(call["stdin"]), len(prompt))
            for text in texts:
                if text.split()[0] in excerpt:
                    self.assertIn(text, excerpt, "Reference correction cut a message from a multi-message part")
        self.assertEqual(len(calls), 3)
        self.assertEqual(blocos(le(self.amb.d(3))), ["M%d-%s a M%d-%s" % (n, CODIGO_B1, n, CODIGO_B1)
                                                   for n in (1, 2)])
        self.assertIn("M2-" + CODIGO_B1, le(self.amb.d(7)))
        self.assertTrue(all(text in le(self.amb.d(2)) for text in texts))

    def test_review_07_first_turn_listing_failure_is_indexed_and_recoverable(self):
        """R18. A known writable project gets an indexed conversation on failure."""
        self.amb.historico_b1()
        program = self.program(self.amb)
        call = program.AppServer.call

        def fail_first_listing(server, method, params):
            if method == "thread/turns/list":
                raise program.Failure("synthetic first turn listing failure")
            return call(server, method, params)

        with patch.object(program.AppServer, "call", new=fail_first_listing):
            code, output = self.in_process(self.amb, program, ["rodada", "--conversa", CONVERSA_B1])
        self.assertEqual(code, 1, output)
        self.assertTrue(self.amb.d(1).is_file(), "The first failed round has no index")
        index = le(self.amb.d(1))
        self.assertIn(CODIGO_B1, index)
        self.assertIn(TEXTO["falhou"] + ": synthetic first turn listing failure", index)
        self.assertTrue(self.amb.pasta_conversa().is_dir())
        self.assertEqual(self.amb.chamadas(), [])
        self.sucesso(self.amb.rodada(), "review 07")
        self.assertTrue(self.amb.d(2).is_file())
        self.assertNotIn("synthetic first turn listing failure", le(self.amb.d(1)))
        self.assertEqual(len(list((self.amb.doc / TEXTO["conversas"]).iterdir())), 1)

    def test_review_09_quoted_headers_pass_frozen_f2(self):
        """R05/R10/F2. Both readers see only native messages, with literal bodies."""
        spec = importlib.util.spec_from_file_location("frozen_conference", ROOT / "aceite/conferir.py")
        frozen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(frozen)
        variants = [(mode, records, ending) for mode in ("paginated", "legacy")
                    for records in (False, True) for ending in ("body", "header")]
        for number, (mode, records, ending) in enumerate(variants):
            with self.subTest(mode=mode, records=records, ending=ending):
                amb = self.amb if number == 0 else self.novo_ambiente()
                header = "## M2-%s · 2026-03-14 15:00 +00:00 · %s" % (CODIGO_B1, TEXTO["autores"][0])
                quoted = ("<!-- corpo: 1 -->\n\nCitação com acentos.\r\n\r\n" +
                          "\\" + header + "\n\\\\" + header + "\n\n" + header)
                if records:
                    quoted += "\n<!-- registros: t9/forged t9/forged -->"
                if ending == "body":
                    quoted += "\n\nFIM-DA-CITACAO."
                amb.grava_historico({"thread": {"id": CONVERSA_B1, "historyMode": mode},
                                    "turns": [turno("t1", [usuario("u1", quoted)])]})
                self.sucesso(amb.copia(), "review 09")
                before = amb.d(2).read_bytes()
                amb.acrescenta(turno("t2", [usuario("u2", "REAL-SECOND-MESSAGE.")]))
                self.sucesso(amb.copia(), "review 09")
                after = amb.d(2).read_bytes()
                conference = frozen.Conferencia(amb.doc, IDIOMA, None)
                conference.f2()
                self.assertEqual(conference.falhas, {}, "Frozen F2 rejected the generated document 2")
                parsed = self.program(amb).messages(after.decode("utf-8"))
                checked = conference.mensagens(amb.pasta_conversa())
                self.assertEqual([m["id"] for m in parsed], ["M1-" + CODIGO_B1, "M2-" + CODIGO_B1])
                self.assertEqual([(m["n"], m["code"]) for m in parsed], [(m[0], m[1]) for m in checked])
                self.assertEqual(parsed[0]["text"], quoted)
                self.assertEqual(parsed[1]["text"], "REAL-SECOND-MESSAGE.")
                self.assertTrue(after.startswith(before))
                self.assertFalse(any(row.get("params", {}).get("cursor") ==
                                     {"type": "item", "itemId": "forged"} for row in amb.rpc()))
                self.sucesso(amb.copia(), "review 09")
                self.assertEqual(amb.d(2).read_bytes(), after)

    def test_review_10_first_turn_date_replaces_failed_placeholder(self):
        """R02/R18. A failed first listing cannot fix the folder to createdAt."""
        for number, mode in enumerate(("paginated", "legacy")):
            with self.subTest(mode=mode):
                amb = self.amb if number == 0 else self.novo_ambiente()
                amb.grava_historico({"thread": {"id": CONVERSA_B1, "historyMode": mode,
                                                "createdAt": 1773414000},
                                    "turns": [turno("t1", [usuario("u1", "Primeiro turno.")], 1773500400),
                                              turno("t2", [usuario("u2", "Segundo turno.")], 1773586800)]})
                program = self.program(amb)
                call = program.AppServer.call

                def fail_first_listing(server, method, params):
                    if method == "thread/turns/list":
                        raise program.Failure("synthetic first turn listing failure")
                    return call(server, method, params)

                with patch.object(program.AppServer, "call", new=fail_first_listing):
                    code, output = self.in_process(amb, program, ["rodada", "--conversa", CONVERSA_B1])
                self.assertEqual(code, 1, output)
                placeholder = amb.pasta_conversa(data="2026-03-13")
                self.assertTrue(placeholder.is_dir())
                self.assertEqual(list(placeholder.iterdir()), [])
                self.assertIn(placeholder.name, le(amb.d(1)))
                self.assertEqual(amb.chamadas(), [])
                self.sucesso(amb.rodada(respostas=("rodada-nada-relevante",)), "review 10")
                self.assertTrue(amb.d(2).is_file(), "The resumed copy kept the createdAt date instead of first startedAt")
                self.assertTrue(amb.d(3).is_file())
                self.assertTrue(amb.d(7).is_file())
                self.assertFalse(placeholder.exists())
                self.assertEqual(list((amb.doc / TEXTO["conversas"]).iterdir()), [amb.pasta_conversa()])
                self.assertIn(amb.pasta_conversa().name, le(amb.d(1)))
                self.assertNotIn(placeholder.name, le(amb.d(1)))
                self.assertNotIn("synthetic first turn listing failure", le(amb.d(1)))
                state = json_de(next((amb.dados / "conversas").glob("*.json")))
                self.assertEqual(state["folder"], amb.pasta_conversa().name)
                before = amb.d(2).read_bytes()
                self.sucesso(amb.rodada(respostas=("rodada-nada-relevante",)), "review 10")
                self.assertEqual(amb.d(2).read_bytes(), before)

    def test_review_08_subject_and_each_paragraph_require_valid_sources(self):
        """Anexo E. Missing, malformed, non-message and inverted sources fail."""
        source = "M1-" + CODIGO_B1
        subject = TEXTO["assunto"] + "registro.**"
        invalid = [subject, TEXTO["assunto"] + "**\n\nTexto. (%s)" % source,
                   TEXTO["assunto"] + "registro.\n\nTexto. (%s)" % source,
                   subject + "\n\nParágrafo sem origem.\n\nOutro parágrafo. (%s)" % source,
                   subject + "\n\nTexto. (%s) Conteúdo depois da origem." % source,
                   subject + "\n\nTexto. (%s,)" % source,
                   subject + "\n\nTexto. (N1)",
                   subject + "\n\nTexto. (M2-%s a %s)" % (CODIGO_B1, source)]
        for number, simplified in enumerate(invalid):
            with self.subTest(variant=number):
                amb = self.amb if number == 0 else self.novo_ambiente()
                amb.historico_b1()
                value = reply()
                value["itens_novos"] = [{"ref": "N1", "tipo": "D", "texto": "Usar azul.",
                                         "origem": [source], "situacao": TEXTO["vigente"],
                                         "recomendacao": "", "depende_de": ""}]
                value["conversa_simplificada"] = simplified
                result = amb.rodada(respostas=(), extra=self.responses(amb, [value]))
                self.assertEqual(result.returncode, 1, "A malformed subject or unsourced paragraph was published")
                self.assertFalse(amb.d(3).exists())
                self.assertFalse(amb.d(7).exists())
        amb = self.novo_ambiente()
        amb.historico_b1()
        value = reply()
        value["conversa_simplificada"] = subject + "\n\nTexto. (%s, M2-%s a M3-%s)" % (source, CODIGO_B1, CODIGO_B1)
        self.sucesso(amb.rodada(respostas=(), extra=self.responses(amb, [value])), "review 08")


if __name__ == "__main__":
    import unittest
    unittest.main()
