"""G12/D-22. Writer-owned migration destinations, one retry and disk verification.

All projects, identifiers, legacy metadata and writer replies are synthetic.
Only the public executor and the frozen offline Codex simulator are used.
"""

import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "aceite/testes"))
from apoio import (CHAVES_HANDOFF, CONVERSA_B1, CONVERSA_OUTRA, PREFIXO, TEXTO,
                   CasoDeAceite, espera, grava_json, inventario, itens, json_de, le, tag)


class MigrationV2(CasoDeAceite):
    def legacy(self, amb, counts=(3,)):
        amb.doc.mkdir()
        (amb.doc / "index.md").write_text("# Índice sintético\n", encoding="utf-8")
        state = amb.doc / ".state"
        state.mkdir()
        (state / "cursor.json").write_text('{"marcador": "ESTADO-NAO-ENVIAR"}', encoding="utf-8")
        (state / "publication.lock").touch()
        groups = {}
        for group, count in enumerate(counts):
            identity = (CONVERSA_B1, CONVERSA_OUTRA)[group]
            names = []
            for number in range(1, count + 1):
                name = "handoff-2026040%d-1000%02d-%06d-ab12cd3%d-%08x.md" % (
                    group + 1, number, number, group, number)
                meta = {"version": 1, "thread_id": identity,
                        "created_at": "2026-04-0%dT10:00:%02d.000001Z" % (group + 1, number),
                        "previous" + "_handoff": names[-1] if names else "", "summary": "Registro sintético",
                        "model": "modelo-sintetico", "effort": "xhigh", "trigger": "manual_request",
                        "processed": {"mensagem-sintetica": "0" * 64}}
                body = ("# Registro sintético\n\nAtualizado em: " + meta["created_at"] +
                        "\nConversa: " + identity + "\nProjeto: /projeto-sintetico\n" +
                        "Cobertura: registros sintéticos.\nRedator: modelo-sintetico\n\n" +
                        "## Estado para continuar\n\n" + "Preservar o painel sintético. " * 45 +
                        "\n\n## Pautas\n\nConferir o painel.\n\n" +
                        "## Decisões e restrições\n\nUsar azul somente no projeto local.\n\n" +
                        "## Pendências\n\nConferir o gráfico.\n\n" +
                        "## Lacunas e limites\n\nA conferência aguarda o usuário.\n\n" +
                        "## Referências\n\nREFERENCIAS-NAO-ENVIAR\n")
                (amb.doc / name).write_text("<!-- hopper-documentation-openai " +
                                            json.dumps(meta) + " -->\n" + body, encoding="utf-8")
                names.append(name)
            groups[identity] = names
        return groups

    def reply(self, identities, origin=None, cited=None):
        value = {"nada_relevante": False, "resumo": "Migração sintética",
                 "itens_novos": [], "mudancas": [], "sem_conteudo": [],
                 "handoffs_antigos": [{"conversa": identity, "resumo": "Painel sintético",
                    "handoff": {key: "Preservar o painel e conferir o gráfico." for key in CHAVES_HANDOFF}}
                    for identity in identities]}
        for handoff in value["handoffs_antigos"]:
            citations = cited.get(handoff["conversa"], "") if isinstance(cited, dict) else cited
            if citations:
                if not isinstance(citations, str):
                    citations = ", ".join(citations)
                handoff["handoff"]["como_retomar"] += " Origens: " + citations + "."
        if origin:
            value["itens_novos"] = [{"ref": "N1", "tipo": "D", "texto": "Usar azul.",
                "conversa": identities[0], "origem": [origin], "situacao": TEXTO["vigente"],
                "recomendacao": "", "depende_de": ""}]
        return value

    def responses(self, amb, values, extra=None):
        paths = []
        for number, value in enumerate(values):
            path = amb.respostas / ("migration-%d.json" % number)
            grava_json(path, value)
            paths.append(str(path))
        return dict(extra or {}, **{PREFIXO + "SIMULADO": json.dumps(paths)})

    def handoff(self, amb, identity):
        matches = [p for p in (amb.doc / TEXTO["conversas"]).glob("*/7-handoff.md")
                   if "- " + TEXTO["conversa"] + ": " + identity + "\n" in le(p)]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def preserved(self, amb, before):
        after = inventario(amb.doc)
        self.assertEqual({name: after.get(name) for name in before}, before)

    def unpublished(self, amb):
        self.assertFalse(list((amb.doc / TEXTO["conversas"]).glob("*/7-handoff.md")))
        for number in (4, 5, 6):
            path = amb.d(number)
            self.assertFalse(itens(le(path)) if path.exists() else [])

    def set_useful(self, amb, name, count):
        path = amb.doc / name
        first_line = le(path).splitlines()[0]
        path.write_text(first_line + "\n# Registro sintético\n\n" +
                        "## Estado para continuar\n\n" + "x" * count +
                        "\n\n## Pautas\n\n## Decisões e restrições\n\n" +
                        "## Pendências\n\n## Lacunas e limites\n\n" +
                        "## Referências\n\nREFERENCIAS-NAO-ENVIAR\n", encoding="utf-8")

    def part_limit(self, amb, groups):
        return max(len(le(amb.doc / name)) for names in groups.values() for name in names)

    def test_D22_missing_destinations_retry_before_publication_and_delete_after_verification(self):
        groups = self.legacy(self.amb)
        names = groups[CONVERSA_B1]
        first = self.reply([CONVERSA_B1], origin=names[-1])
        complete = self.reply([CONVERSA_B1], origin=names[-1], cited=names[:-1])
        before = inventario(self.amb.doc)
        extra = self.responses(self.amb, [first, {"resposta": complete, "espera_segundos": 60}],
                               {PREFIXO + "INTERROMPER_EM": "antes-da-exclusao"})
        process = self.amb.inicia("migrar", "--pasta", str(self.amb.projeto), respostas=(), extra=extra)
        self.assertTrue(espera(lambda: len(self.amb.chamadas()) == 2, 10))
        self.assertIsNone(process.poll())
        self.preserved(self.amb, before)
        self.unpublished(self.amb)
        out, err = process.communicate(timeout=15)
        self.assertEqual(process.returncode, 1, out + err)
        self.assertIn("antes-da-exclusao", out)
        self.preserved(self.amb, before)
        text = le(self.handoff(self.amb, CONVERSA_B1))
        self.assertTrue(all(name in text for name in names[:-1]))
        self.assertNotIn(names[-1], text, "The executor must not add an uncited handoff source")
        self.assertEqual(itens(le(self.amb.d(4)))[0]["campos"][TEXTO["origem"]], names[-1])
        self.assertEqual(re.findall(r"^## (.*)$", text, re.M), TEXTO["secoes_d7"])
        calls = self.amb.chamadas()
        self.assertEqual(len(calls), 2)
        correction = calls[1]["stdin"]
        self.assertEqual(tag(correction, "arquivos_sem_destino").splitlines(), names[:-1])
        self.assertEqual(json.loads(tag(correction, "resposta_anterior")), first)
        for field in ("arquivos_antigos", "handoff_anterior", "decisoes", "funcoes", "pendencias"):
            self.assertEqual(tag(correction, field), tag(calls[0]["stdin"], field))
        self.assertIn("sem_conteudo", correction)
        self.assertIn("200", correction)
        self.assertTrue(any(row["etapa"] == "migracao" and row["resultado"] == "concluída"
                            for row in self.amb.rodadas()))
        self.assertFalse(any(row["etapa"] == "exclusao" for row in self.amb.rodadas()))
        self.sucesso(self.amb.migrar(respostas=(), extra=self.responses(self.amb, [complete])), "G12/D-22")
        self.assertFalse(list(self.amb.doc.glob("handoff-*.md")))
        self.assertFalse((self.amb.doc / "index.md").exists())
        self.assertFalse((self.amb.doc / ".state").exists())
        self.assertEqual(len(self.amb.chamadas()), 2)
        stages = [row["etapa"] for row in self.amb.rodadas() if row["resultado"] == "concluída"]
        self.assertLess(stages.index("migracao"), stages.index("exclusao"))
        for call in calls:
            for marker in ("<!-- hopper-documentation-openai", "ESTADO-NAO-ENVIAR", "REFERENCIAS-NAO-ENVIAR"):
                self.assertNotIn(marker, call["stdin"])

    def test_D22_missing_destinations_twice_preserve_originals_and_publish_nothing(self):
        groups = self.legacy(self.amb)
        names = groups[CONVERSA_B1]
        before = inventario(self.amb.doc)
        response = self.reply([CONVERSA_B1], origin=names[-1])
        result = self.amb.migrar(respostas=(), extra=self.responses(self.amb, [response, response]))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("arquivos sem destino", result.stdout)
        self.assertEqual(len(self.amb.chamadas()), 2)
        self.preserved(self.amb, before)
        self.unpublished(self.amb)
        journals = list((self.amb.dados / "diarios").glob("migracao-*.json"))
        self.assertEqual(len(journals), 1)
        journal = json_de(journals[0])
        self.assertEqual(journal["cursor"], [0, 0])
        self.assertIsNone(journal["current"])
        self.assertFalse(any(row["etapa"] == "exclusao" for row in self.amb.rodadas()))

    def test_D22_sources_belong_only_to_their_metadata_conversation(self):
        groups = self.legacy(self.amb, (2, 2))
        response = self.reply(list(groups), cited=groups)
        self.sucesso(self.amb.migrar(respostas=(), extra=self.responses(self.amb, [response])), "R31/R32")
        for identity, names in groups.items():
            text = le(self.handoff(self.amb, identity))
            self.assertTrue(all(name in text for name in names))
            self.assertFalse(any(name in text for other, values in groups.items() if other != identity for name in values))

    def test_D22_foreign_handoff_and_summary_citations_do_not_supply_a_destination(self):
        for location in ("other_conversation", "summary"):
            with self.subTest(location=location):
                amb = self.amb if location == "other_conversation" else self.novo_ambiente()
                groups = self.legacy(amb, (1, 1))
                first, other = groups[CONVERSA_B1][0], groups[CONVERSA_OUTRA][0]
                response = self.reply(list(groups), cited={CONVERSA_OUTRA: [other]})
                if location == "other_conversation":
                    response["handoffs_antigos"][1]["handoff"]["como_retomar"] += " Origem: " + first
                else:
                    response["handoffs_antigos"][0]["resumo"] = first
                before = inventario(amb.doc)
                result = amb.migrar(respostas=(), extra=self.responses(amb, [response]))
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("arquivos sem destino", result.stdout)
                self.assertEqual(len(amb.chamadas()), 2)
                self.preserved(amb, before)
                self.unpublished(amb)

    def test_D22_multipart_sources_accumulate_without_claiming_unread_files(self):
        groups = self.legacy(self.amb)
        names = groups[CONVERSA_B1]
        replies = [self.reply([CONVERSA_B1], cited=names[:number + 1]) for number in range(len(names))]
        extra = self.responses(self.amb, replies,
                               {PREFIXO + "LIMITE_DA_PARTE": self.part_limit(self.amb, groups)})
        self.sucesso(self.amb.migrar(respostas=(), extra=extra), "R31/parts")
        calls = self.amb.chamadas()
        self.assertEqual(len(calls), len(names))
        for number, call in enumerate(calls):
            excerpt = tag(call["stdin"], "arquivos_antigos")
            self.assertEqual(re.findall(r"^### (handoff-\S+)$", excerpt, re.M), [names[number]])
            previous = tag(call["stdin"], "handoff_anterior")
            if number:
                self.assertTrue(all(name in previous for name in names[:number]))
            else:
                self.assertEqual(previous, "")
            self.assertFalse(any(name in previous for name in names[number:]))
        self.assertTrue(all(name in le(self.handoff(self.amb, CONVERSA_B1)) for name in names))

    def test_D22_multipart_item_can_cite_a_previous_processed_source(self):
        groups = self.legacy(self.amb, (2,))
        first, second = groups[CONVERSA_B1]
        replies = [self.reply([CONVERSA_B1], cited=first),
                   self.reply([CONVERSA_B1], origin=first, cited=second)]
        extra = self.responses(self.amb, replies,
                               {PREFIXO + "LIMITE_DA_PARTE": self.part_limit(self.amb, groups)})
        self.sucesso(self.amb.migrar(respostas=(), extra=extra), "G12/references from previous part")
        self.assertEqual(len(self.amb.chamadas()), 2, "A known previous source must not trigger a retry")
        self.assertEqual(itens(le(self.amb.d(4)))[0]["campos"][TEXTO["origem"]], first)
        self.assertIn(first, tag(self.amb.chamadas()[1]["stdin"], "handoff_anterior"))

    def test_D22_one_file_split_between_parts_keeps_one_source(self):
        groups = self.legacy(self.amb, (1,))
        names = groups[CONVERSA_B1]
        extra = self.responses(self.amb, [self.reply([CONVERSA_B1], cited=names)],
                               {PREFIXO + "LIMITE_DA_PARTE": 900})
        self.sucesso(self.amb.migrar(respostas=(), extra=extra), "R31/split file")
        calls = self.amb.chamadas()
        self.assertGreater(len(calls), 1)
        for call in calls[1:]:
            self.assertIn(names[0], tag(call["stdin"], "handoff_anterior"))
        self.assertEqual(le(self.handoff(self.amb, CONVERSA_B1)).count(names[0]), 1)

    def test_D22_recovery_publishes_only_validated_citations_without_repeating_the_writer(self):
        for stage in ("depois-do-diario", "meio-da-gravacao"):
            with self.subTest(stage=stage):
                amb = self.amb if stage == "depois-do-diario" else self.novo_ambiente()
                groups = self.legacy(amb)
                response = self.reply([CONVERSA_B1], cited=groups[CONVERSA_B1])
                before = inventario(amb.doc)
                extra = self.responses(amb, [response], {PREFIXO + "INTERROMPER_EM": stage})
                result = amb.migrar(respostas=(), extra=extra)
                self.assertEqual(result.returncode, 1)
                self.assertIn(stage, result.stdout)
                self.assertEqual({name: inventario(amb.doc)[name] for name in before}, before)
                self.sucesso(amb.migrar(respostas=(), extra=self.responses(amb, [response])), "R29/R31")
                self.assertTrue(all(name in le(self.handoff(amb, CONVERSA_B1)) for name in groups[CONVERSA_B1]))
                self.assertEqual(len(amb.chamadas()), 1)

    def test_D22_reference_retry_corrects_the_origin_with_the_same_migration_schema(self):
        groups = self.legacy(self.amb, (1,))
        name = groups[CONVERSA_B1][0]
        unknown = "handoff-20260101-000000-000000-ffffffff-00000000.md"
        first = self.reply([CONVERSA_B1], origin=unknown, cited=name)
        complete = self.reply([CONVERSA_B1], origin=name, cited=name)
        self.sucesso(self.amb.migrar(respostas=(), extra=self.responses(self.amb, [first, complete])), "G12/references retry")
        calls = self.amb.chamadas()
        self.assertEqual(len(calls), 2)
        self.assertIn(unknown, calls[1]["stdin"][len(calls[0]["stdin"]):])
        self.assertEqual(tag(calls[0]["stdin"], "arquivos_antigos"), tag(calls[1]["stdin"], "arquivos_antigos"))
        self.assertEqual(itens(le(self.amb.d(4)))[0]["campos"][TEXTO["origem"]], name)
        self.assertFalse(list(self.amb.doc.glob("handoff-*.md")))

    def test_D22_missing_destinations_and_references_share_one_retry(self):
        for order in ("destination_first", "reference_first"):
            with self.subTest(order=order):
                amb = self.amb if order == "destination_first" else self.novo_ambiente()
                groups = self.legacy(amb, (2,))
                names = groups[CONVERSA_B1]
                missing = self.reply([CONVERSA_B1], origin=names[-1])
                rejected = self.reply([CONVERSA_B1], origin="unknown.md", cited=names)
                replies = [missing, rejected] if order == "destination_first" else [rejected, missing]
                before = inventario(amb.doc)
                result = amb.migrar(respostas=(), extra=self.responses(amb, replies))
                self.assertEqual(result.returncode, 1)
                self.assertEqual(len(amb.chamadas()), 2)
                self.preserved(amb, before)
                self.unpublished(amb)

    def test_D22_unknown_future_and_other_conversation_item_sources_are_rejected(self):
        for defect in ("unknown", "future", "other_conversation"):
            with self.subTest(defect=defect):
                amb = self.amb if defect == "unknown" else self.novo_ambiente()
                groups = self.legacy(amb, (2, 1))
                first, future = groups[CONVERSA_B1]
                origin = {"unknown": "handoff-20260101-000000-000000-ffffffff-00000000.md",
                          "future": future, "other_conversation": groups[CONVERSA_OUTRA][0]}[defect]
                before = inventario(amb.doc)
                replies = [self.reply([CONVERSA_B1], origin=origin, cited=first)]
                extra = self.responses(amb, replies,
                                       {PREFIXO + "LIMITE_DA_PARTE": self.part_limit(amb, groups)})
                result = amb.migrar(respostas=(), extra=extra)
                self.assertEqual(result.returncode, 1)
                self.assertIn("referências recusadas", result.stdout)
                self.assertEqual({name: inventario(amb.doc)[name] for name in before}, before)
                self.assertEqual(len(amb.chamadas()), 2)

    def test_D22_disk_verification_rejects_removed_or_foreign_writer_citations(self):
        for defect in ("removed", "foreign"):
            with self.subTest(defect=defect):
                amb = self.amb if defect == "removed" else self.novo_ambiente()
                groups = self.legacy(amb, (2, 1))
                before = inventario(amb.doc)
                response = self.reply(list(groups), cited=groups)
                extra = self.responses(amb, [response], {PREFIXO + "INTERROMPER_EM": "antes-da-exclusao"})
                result = amb.migrar(respostas=(), extra=extra)
                self.assertEqual(result.returncode, 1)
                self.assertIn("antes-da-exclusao", result.stdout)
                path = self.handoff(amb, CONVERSA_B1)
                text = le(path)
                replacement = "" if defect == "removed" else ", ".join(groups[CONVERSA_OUTRA])
                path.write_text(text.replace(", ".join(groups[CONVERSA_B1]), replacement), encoding="utf-8")
                result = amb.migrar(respostas=(), extra=self.responses(amb, [response]))
                self.assertEqual(result.returncode, 1)
                self.assertIn("verificação da migração", result.stdout)
                self.assertEqual({name: inventario(amb.doc)[name] for name in before}, before)
                self.assertEqual(len(amb.chamadas()), 1)

    def test_D22_invalid_empty_content_claim_and_conversation_sets_preserve_originals(self):
        for defect in ("empty_content", "missing_conversation", "extra_conversation"):
            with self.subTest(defect=defect):
                amb = self.amb if defect == "empty_content" else self.novo_ambiente()
                groups = self.legacy(amb, (1,))
                names = groups[CONVERSA_B1]
                response = self.reply([CONVERSA_B1], cited=names[0])
                if defect == "empty_content":
                    response["sem_conteudo"] = names
                elif defect == "missing_conversation":
                    response["handoffs_antigos"] = []
                else:
                    response["handoffs_antigos"] += self.reply([CONVERSA_OUTRA])["handoffs_antigos"]
                before = inventario(amb.doc)
                result = amb.migrar(respostas=(), extra=self.responses(amb, [response]))
                self.assertEqual(result.returncode, 1)
                self.assertEqual({name: inventario(amb.doc)[name] for name in before}, before)

    def test_D22_empty_content_threshold_remains_199_allowed_and_200_rejected(self):
        for useful in (199, 200):
            with self.subTest(useful=useful):
                amb = self.amb if useful == 199 else self.novo_ambiente()
                groups = self.legacy(amb, (1,))
                name = groups[CONVERSA_B1][0]
                path = amb.doc / name
                self.set_useful(amb, name, useful)
                response = self.reply([CONVERSA_B1])
                response["sem_conteudo"] = [name]
                before = inventario(amb.doc)
                result = amb.migrar(respostas=(), extra=self.responses(amb, [response]))
                self.assertEqual(result.returncode, 0 if useful == 199 else 1, result.stdout)
                self.assertEqual(path.exists(), useful == 200)
                if useful == 200:
                    self.assertEqual({name: inventario(amb.doc)[name] for name in before}, before)

    def test_D22_retry_sem_conteudo_still_counts_199_allowed_and_200_rejected(self):
        for useful in (199, 200):
            with self.subTest(useful=useful):
                amb = self.amb if useful == 199 else self.novo_ambiente()
                groups = self.legacy(amb, (1,))
                name = groups[CONVERSA_B1][0]
                self.set_useful(amb, name, useful)
                before = inventario(amb.doc)
                first = self.reply([CONVERSA_B1])
                second = self.reply([CONVERSA_B1])
                second["sem_conteudo"] = [name]
                result = amb.migrar(respostas=(), extra=self.responses(amb, [first, second]))
                self.assertEqual(result.returncode, 0 if useful == 199 else 1, result.stdout)
                self.assertEqual(len(amb.chamadas()), 2)
                if useful == 200:
                    self.preserved(amb, before)
                    self.unpublished(amb)
                else:
                    self.assertFalse((amb.doc / name).exists())

    def test_D22_disk_item_status_and_missing_handoff_still_block_deletion(self):
        for number in (4, 5, 6, 7):
            with self.subTest(document=number):
                amb = self.amb if number == 4 else self.novo_ambiente()
                groups = self.legacy(amb, (2,))
                names = groups[CONVERSA_B1]
                response = self.reply([CONVERSA_B1], origin=names[-1], cited=", ".join(names))
                if number in (5, 6):
                    item = response["itens_novos"][0]
                    item["tipo"] = "F" if number == 5 else "PD"
                    item["situacao"] = TEXTO["concluida"] if number == 5 else TEXTO["aberta"]
                    if number == 6:
                        item.update(recomendacao="Conferir o gráfico.", depende_de="O usuário aprovar.")
                before = inventario(amb.doc)
                extra = self.responses(amb, [response], {PREFIXO + "INTERROMPER_EM": "antes-da-exclusao"})
                result = amb.migrar(respostas=(), extra=extra)
                self.assertEqual(result.returncode, 1)
                self.assertIn("antes-da-exclusao", result.stdout)
                if number == 7:
                    self.handoff(amb, CONVERSA_B1).unlink()
                else:
                    path = amb.d(number)
                    text = re.sub(r"^- " + re.escape(TEXTO["situacao"]) + r": .*?$",
                                  "- " + TEXTO["situacao"] + ": estado inventado", le(path), flags=re.M)
                    path.write_text(text, encoding="utf-8")
                result = amb.migrar(respostas=(), extra=self.responses(amb, [response]))
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("verificação da migração", result.stdout)
                self.assertEqual({name: inventario(amb.doc)[name] for name in before}, before)
                self.assertEqual(len(amb.chamadas()), 1)

    def test_D22_preexisting_journal_with_complete_narrative_sources_can_resume(self):
        groups = self.legacy(self.amb, (2,))
        names = groups[CONVERSA_B1]
        response = self.reply([CONVERSA_B1], cited=", ".join(names))
        extra = self.responses(self.amb, [response], {PREFIXO + "INTERROMPER_EM": "antes-da-exclusao"})
        result = self.amb.migrar(respostas=(), extra=extra)
        self.assertEqual(result.returncode, 1)
        self.assertIn("antes-da-exclusao", result.stdout)
        path = self.handoff(self.amb, CONVERSA_B1)
        # rc.3 documents have narrative citations and no executor source field.
        text = re.sub(r"^- " + re.escape(TEXTO["origem"]) + r": .*\n", "", le(path), flags=re.M)
        path.write_text(text, encoding="utf-8")
        self.sucesso(self.amb.migrar(respostas=(), extra=self.responses(self.amb, [response])), "R29/rc.3 journal")
        self.assertFalse(list(self.amb.doc.glob("handoff-*.md")))
        self.assertEqual(len(self.amb.chamadas()), 1)


if __name__ == "__main__":
    import unittest
    unittest.main()
