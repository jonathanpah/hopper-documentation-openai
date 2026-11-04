"""G12/D-20. Test-conversation excerpts from the rc.2 acceptance evidence.

Only the relevant text and native record identifiers are retained. Projects,
processes and writer calls use the frozen, offline acceptance simulator.
"""

import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "aceite/testes"))
from apoio import (CHAVES_HANDOFF, CONVERSA_B1, PREFIXO, TEXTO, CasoDeAceite,
                   grava_json, itens, le, mensagens, turno, usuario)


ACTIVE_TURN = "01a1a618-b7ea-78c2-9664-60743d654297"
ACTIVE_USER = "01a1a618-b826-7db0-ba0e-b7820ac01bc9"
ACTIVE_AGENT = "msg_00e21fa967988ea6016aeb08616df087d2976ced853401039d"


def active_turn(status="interrupted"):
    """M14/M15 of a2-documento-2.md, before the spurious M16 event."""
    return turno(ACTIVE_TURN, [usuario(ACTIVE_USER, "Documente a conversa."),
        {"id": ACTIVE_AGENT, "type": "agentMessage", "text":
         "Vou atualizar os 7 arquivos com a skill `hopper-documentation-openai` "
         "e conferir se o registro do tema aparece como concluído."}],
        status=status, completedAt=None, error=None)


def writer_reply(code, simplified):
    return {"nada_relevante": False, "resumo": "Decisões do painel",
            "conversa_simplificada": TEXTO["assunto"] + "decisões do painel.**\n\n" + simplified,
            "itens_novos": [], "mudancas": [],
            "handoff": {key: "A cor azul foi escolhida. (M1-%s)" % code
                        for key in CHAVES_HANDOFF}}


class AcceptanceRegressionsV2(CasoDeAceite):
    def write_with(self, amb, conversation, response, name):
        path = amb.respostas / (name + ".json")
        grava_json(path, response)
        return amb.rodada(conversa=conversation, respostas=(),
                          extra={PREFIXO + "SIMULADO": json.dumps([str(path)])})

    def test_D20_active_terminal_status_needs_evidence_and_resumes_native_items(self):
        """R04/R08. A separate reader's last interrupted turn is still writable."""
        for mode in ("paginated", "legacy"):
            for status in ("interrupted", "failed"):
                with self.subTest(mode=mode, status=status):
                    amb = self.novo_ambiente()
                    current = active_turn(status)
                    if mode == "legacy":
                        current.pop("completedAt")
                    history = {"thread": {"id": CONVERSA_B1, "historyMode": mode},
                               "turns": [current], "opcoes": {"pagina_turnos": 1,
                                                               "pagina_registros": 1}}
                    amb.grava_historico(history)
                    self.sucesso(amb.copia(), "D-20/1")
                    initial = amb.d(2).read_bytes()
                    self.assertEqual(len(mensagens(initial.decode())), 2,
                                     "An unconfirmed last-turn status produced a false Event")
                    self.assertNotIn(ACTIVE_TURN + "/status", initial.decode())
                    self.sucesso(amb.copia(), "D-20/1")
                    self.assertEqual(amb.d(2).read_bytes(), initial)

                    continuation = {"id": "msg_continuation", "type": "agentMessage",
                                    "text": "O registro do tema foi concluído."}
                    current["items"].append(continuation)
                    current.update(status="completed", completedAt=1773500460)
                    amb.grava_historico(history)
                    self.sucesso(amb.copia(), "D-20/1")
                    continued = amb.d(2).read_bytes()
                    self.assertTrue(continued.startswith(initial))
                    self.assertEqual(len(mensagens(continued.decode())), 3)
                    self.assertEqual(continued.decode().count(continuation["text"]), 1)
                    if mode == "paginated":
                        self.assertTrue(any(row["params"].get("cursor") ==
                                            {"type": "item", "itemId": ACTIVE_AGENT}
                                            for row in amb.rpc()))

                    # With no completion metadata, only a later turn confirms
                    # the real interruption/failure. It is on another page.
                    uncertain = turno("later", [usuario("later-user", "Continue o teste.")],
                                      1773500520, status, error=None)
                    history["turns"].append(uncertain)
                    amb.grava_historico(history)
                    self.sucesso(amb.copia(), "D-20/1")
                    before_successor = amb.d(2).read_bytes()
                    self.assertNotIn("later/status", before_successor.decode())
                    history["turns"].append(turno("successor", [usuario("next", "Próximo pedido.")],
                                                   1773500580))
                    amb.grava_historico(history)
                    self.sucesso(amb.copia(), "D-20/1")
                    confirmed = amb.d(2).read_bytes()
                    self.assertTrue(confirmed.startswith(before_successor))
                    self.assertEqual(confirmed.decode().count("later/status later/status"), 1)
                    event = mensagens(confirmed.decode())[-2]
                    self.assertTrue(event[1].endswith(" · " + TEXTO["autores"][3]))
                    self.assertLess(confirmed.decode().index("later/status"),
                                    confirmed.decode().index("Próximo pedido."))

                    # The schema's non-null completedAt confirms even the last
                    # turn. A failed turn's own error also confirms its failure
                    # in older histories without completion timestamps (B1).
                    terminal = turno("terminal", [usuario("last", "Último pedido.")],
                                     1773500640, status, completedAt=1773500700)
                    history["turns"].append(terminal)
                    amb.grava_historico(history)
                    self.sucesso(amb.copia(), "D-20/1")
                    self.assertIn("terminal/status terminal/status", le(amb.d(2)))
                    if status == "failed":
                        history["turns"].append(turno("failure", [usuario("failure-user", "Gere o gráfico.")],
                            1773500760, "failed", error={"message": "limite de uso atingido"}))
                        amb.grava_historico(history)
                        self.sucesso(amb.copia(), "D-20/1")
                        self.assertIn("failure/status failure/status", le(amb.d(2)))
                        self.assertIn("limite de uso atingido", le(amb.d(2)))
                    final = amb.d(2).read_bytes()
                    self.sucesso(amb.copia(), "D-20/1")
                    self.assertEqual(amb.d(2).read_bytes(), final)
                    self.assertFalse(any(row["params"].get("cursor") ==
                                         {"type": "item", "itemId": "status"} for row in amb.rpc()))
                    self.assertEqual(amb.chamadas(), [])

    def test_D20_paragraph_origins_keep_messages_and_preserve_other_sources(self):
        """Anexo E. Normalize the refused A1 paragraph before validation/publication."""
        amb, code = self.amb, "fbe84425"
        conversation = "01a2b3c4-5d6e-7f80-9a1b-0000fbe84425"
        first = turno("initial", [usuario("u%d" % n, text) for n, text in enumerate([
            "Vamos testar a documentação. Decidimos usar a cor azul no painel.",
            "Registro sintético 2.", "Registro sintético 3.", "Registro sintético 4.",
            "Registro sintético 5."], 1)])
        history = {"thread": {"id": conversation, "historyMode": "paginated"}, "turns": [first]}
        amb.grava_historico(history)
        seed = writer_reply(code, "A cor azul foi escolhida. (M1-%s)" % code)
        seed["itens_novos"] = [{"ref": "N1", "tipo": "D", "texto": "Usar azul no painel.",
            "origem": ["M1-" + code], "situacao": TEXTO["vigente"], "recomendacao": "", "depende_de": ""}]
        self.sucesso(self.write_with(amb, conversation, seed, "seed"), "D-20/2 seed")

        history["turns"].append(turno("theme", [usuario("theme-user", "O painel deve seguir o tema do sistema."),
            {"id": "theme-agent", "type": "agentMessage", "text": "Vou manter o azul já definido."}],
            1773500460, "interrupted", completedAt=1773500520))
        amb.grava_historico(history)
        # Verbatim paragraph from a1-escrita-recusada.log.
        paragraph = ("O usuário definiu que o painel siga o tema claro ou escuro do sistema. "
                     "O Codex indicou que manteria o azul já definido, mas a resposta foi interrompida. "
                     "(M6-fbe84425 a M8-fbe84425, D1-fbe84425)")
        mixed = "O azul continua definido. (D1-fbe84425, M6-fbe84425, F99-fbe84425, M7-fbe84425, PD99-fbe84425, N1)"
        valid = "O azul continua definido. (M6-fbe84425 a M8-fbe84425)"
        response = writer_reply(code, paragraph + "\n\n" + mixed + "\n\n" + valid)
        response["itens_novos"] = [{"ref": "N1", "tipo": "D", "texto": "O painel deve acompanhar o tema do sistema.",
            "origem": ["M6-" + code, "M7-" + code, "D1-" + code],
            "situacao": TEXTO["vigente"], "recomendacao": "", "depende_de": ""}]
        response["handoff"]["pautas_e_estado"] = "O azul continua definido. (D1-fbe84425, M6-fbe84425, M7-fbe84425)"
        self.sucesso(self.write_with(amb, conversation, response, "mixed"), "D-20/2")
        simplified = le(amb.d(3, codigo=code))
        self.assertIn(paragraph.replace(", D1-fbe84425)", ")"), simplified)
        self.assertIn("O azul continua definido. (M6-fbe84425, M7-fbe84425)", simplified)
        self.assertIn(valid, simplified)
        self.assertNotIn("D1-fbe84425", simplified)
        self.assertNotIn("F99-fbe84425", simplified)
        self.assertNotIn("PD99-fbe84425", simplified)
        self.assertEqual(len(amb.chamadas()), 2, "Normalization must not spend a writer retry")
        self.assertEqual(itens(le(amb.d(4)))[-1]["campos"][TEXTO["origem"]],
                         "M6-fbe84425, M7-fbe84425, D1-fbe84425")
        self.assertIn(response["handoff"]["pautas_e_estado"], le(amb.d(7, codigo=code)))

        # Normalization cannot rescue a paragraph without a message, invent a
        # missing message, accept invalid ranges, or accept a dangling comma.
        history["turns"].append(turno("next", [usuario("next-user", "Continue.")], 1773500580))
        amb.grava_historico(history)
        unchanged = {n: amb.d(n, codigo=code).read_bytes() for n in range(3, 8)}
        invalid = ["Texto. (D1-fbe84425, N1)",
                   "Texto. (M6-fbe84425, D1-fbe84425)\n\nOutro parágrafo. (D1-fbe84425)",
                   "Texto. (M999-fbe84425, D1-fbe84425)",
                   "Texto. (M8-fbe84425 a M6-fbe84425, D1-fbe84425)",
                   "Texto. (M6-fbe84425 a M8-outro, D1-fbe84425)",
                   "Texto. (M6-fbe84425,)"]
        for number, body in enumerate(invalid):
            with self.subTest(invalid=body):
                rejected = writer_reply(code, body)
                result = self.write_with(amb, conversation, rejected, "invalid-%d" % number)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertEqual({n: amb.d(n, codigo=code).read_bytes() for n in range(3, 8)}, unchanged)
