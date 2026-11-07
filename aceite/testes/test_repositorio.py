"""T34, T36, T42 e T44. Inventário e contratos estáticos dos 2 pacotes."""
import fnmatch
import json
import re
import subprocess
import unittest
from pathlib import Path

from apoio import PROGRAMA_REL, RAIZ, SKILL_REL, TEXTOS, le, sha256

PACOTES = [(RAIZ / ("hopper-documentation-openai-" + idioma), idioma) for idioma in ("pt-br", "en")]
INVENTARIO = [
    ".agents/plugins/marketplace.json", ".github/ISSUE_TEMPLATE/bug-report.yml", ".github/ISSUE_TEMPLATE/change-proposal.yml",
    ".github/index.md", ".github/pull_request_template.md", ".github/workflows/integridade.yml", ".github/workflows/verificar.yml",
    ".gitignore", "AGENTS.md", "CHANGELOG.md", "CODE_OF_CONDUCT.md", "CONTRIBUTING.md", "LICENSE", "Makefile", "README.md",
    "SECURITY.md", "SPEC.md", "index.md", "scripts/build.py", "tests/**", "aceite/conferir.py", "aceite/avaliacoes.py",
    "aceite/MANIFESTO.sha256", "aceite/roteiro.json", "aceite/casos/**", "aceite/testes/**",
]
for pacote, idioma in PACOTES:
    prefixo = pacote.name + "/"
    INVENTARIO.extend(prefixo + p for p in [
        ".codex-plugin/plugin.json", ".agents/plugins/marketplace.json", "hooks/hooks.json", "LICENSE", "README.md",
        (SKILL_REL / "SKILL.md").as_posix(), (SKILL_REL / "LICENSE").as_posix(), (SKILL_REL / "agents/openai.yaml").as_posix(),
        (SKILL_REL / TEXTOS[idioma]["regras"]).as_posix(), (SKILL_REL / TEXTOS[idioma]["modelos"]).as_posix(), PROGRAMA_REL.as_posix(),
    ])
PROIBIDOS = ("citation_retries", "latest_context", "previous_handoff")
HASH_REGRAS = {"pt-br": "f13c1ca6f8d9741ff2d4c8d221f317873d7e739828f63711be0f474c9b91b864",
               "en": "c241f5145b6576fc7a56cd7771095808ffe6879d3903c54f40e498bd9b8d350b"}  # versão 2.1: regras de forma do proprietário


class Repositorio(unittest.TestCase):
    def test_R34_inventario_exato_do_anexo_c_e_cadeias_proibidas(self):
        """T34. Arquivos versionados e novos, nenhum caminho extra e versões 2.0.0."""
        r = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                           cwd=str(RAIZ), capture_output=True, check=True)
        arquivos = sorted(set(p.decode() for p in r.stdout.split(b"\0") if p))
        indevidos = [p for p in arquivos if not any(fnmatch.fnmatchcase(p, padrao) for padrao in INVENTARIO)]
        self.assertEqual(indevidos, [], "R34: o inventário deve conter somente os caminhos do Anexo C")
        fixos = {p for p in INVENTARIO if "*" not in p}
        self.assertEqual(sorted(fixos - set(arquivos)), [], "R34: o inventário está incompleto")
        for nome in ("docs-by-hopper-documentation-openai", "docs-by-hopper-documentation"):
            self.assertFalse((RAIZ / nome).exists(), "R34: documentação privada dentro do repositório")
        proprio = Path(__file__).resolve().relative_to(RAIZ).as_posix()
        atingidos = []
        for nome in arquivos:
            if nome in ("SPEC.md", proprio):
                continue
            p = RAIZ / nome
            if p.is_symlink():
                conteudo = str(p.readlink()).encode()
            else:
                conteudo = p.read_bytes()
            if any(s.encode() in conteudo for s in PROIBIDOS):
                atingidos.append(nome)
        self.assertEqual(atingidos, [], "R34: referências à implementação antiga fora das 2 exceções")
        for pacote, _ in PACOTES:
            self.assertEqual(json.loads(le(pacote / ".codex-plugin/plugin.json"))["version"], "2.1.0")

    def test_R36_pacotes_completos_programas_iguais_e_regras_congeladas(self):
        """T36. Só LANGUAGE difere, componentes dos 2 idiomas e SHA-256 de C14."""
        caminhos = [p / PROGRAMA_REL for p, _ in PACOTES]
        programas = [le(p) if p.is_file() else "" for p in caminhos]
        self.assertTrue(all(programas), "R36: os 2 pacotes devem oferecer o programa da versão 2 para comparação")
        sem_idioma = []
        for programa, (_, idioma) in zip(programas, PACOTES):
            linhas = programa.splitlines(keepends=True)
            seletoras = [l for l in linhas if re.match(r"^LANGUAGE\s*=", l)]
            self.assertEqual(len(seletoras), 1, "R36: deve existir 1 linha LANGUAGE")
            self.assertRegex(seletoras[0], r"^LANGUAGE\s*=\s*['\"]" + idioma + r"['\"]\s*$")
            sem_idioma.append("".join(l for l in linhas if l not in seletoras))
        self.assertEqual(sem_idioma[0], sem_idioma[1], "R36: o código difere além da linha LANGUAGE")
        self.assertNotEqual(programas[0], programas[1])
        for pacote, idioma in PACOTES:
            obrigatorios = [p[len(pacote.name) + 1:] for p in INVENTARIO if p.startswith(pacote.name + "/")]
            self.assertTrue(all((pacote / rel).is_file() for rel in obrigatorios), "R36: pacote incompleto " + idioma)
            self.assertEqual(json.loads(le(pacote / ".codex-plugin/plugin.json"))["name"], "hopper-documentation-openai")
            self.assertIsInstance(json.loads(le(pacote / ".agents/plugins/marketplace.json")), dict)
            self.assertEqual(sha256(pacote / SKILL_REL / TEXTOS[idioma]["regras"]), HASH_REGRAS[idioma], "R36: regras diferentes da referência C14")
            self.assertTrue(le(pacote / SKILL_REL / TEXTOS[idioma]["modelos"]).strip())

    def test_R42_skill_com_2_secoes_e_menos_de_500_linhas(self):
        """T42. Os 2 SKILL.md, nome, descrição C15 e invocação implícita."""
        descricoes = {
            "pt-br": 'Documenta a conversa atual do Codex, ou outra conversa indicada pelo código, em 7 documentos (índice, conversa integral, conversa simplificada, decisões, funções implementadas, pendências e handoff) na pasta docs-by-hopper-documentation-openai do projeto. Use quando o usuário pedir para documentar ou registrar a conversa, salvar o progresso, fazer um handoff ou documentar outra conversa antes de continuá-la. Não use para explicar, revisar ou editar esta skill.',
            "en": "Documents the current Codex conversation, or another conversation given by its code, in 7 documents (index, full conversation, simplified conversation, decisions, implemented functions, pending items and handoff) in the project's docs-by-hopper-documentation-openai folder. Use when the user asks to document or record the conversation, save progress, write a handoff or document another conversation before continuing it. Do not use to explain, review or edit this skill.",
        }
        for pacote, idioma in PACOTES:
            caminho = pacote / SKILL_REL / "SKILL.md"
            texto = le(caminho) if caminho.is_file() else ""
            titulos = re.findall(r"^#{1,6}\s+(.+?)\s*$", texto, re.M)
            self.assertTrue(all(s in titulos for s in TEXTOS[idioma]["secoes_skill"]), "R42: faltam as 2 seções exigidas na skill " + idioma)
            self.assertLess(len(texto.splitlines()), 500, "R42: SKILL.md deve ter menos de 500 linhas")
            self.assertRegex(texto, r"(?m)^name:\s*['\"]?hopper-documentation-openai['\"]?\s*$")
            self.assertIn(descricoes[idioma], texto)
            self.assertIn("rodada --conversa", texto)
            self.assertIn("CODEX_THREAD_ID", texto)
            self.assertRegex(le(pacote / SKILL_REL / "agents/openai.yaml"), r"allow_implicit_invocation:\s*true")

    def test_R44_hooks_iguais_ao_anexo_e_sem_session_start(self):
        """T44. JSON completo, matcher, timeouts, ordem, async e status por idioma."""
        comando = 'python3 "${PLUGIN_ROOT}/skills/hopper-documentation-openai/scripts/hopper_documentation_openai.py" '
        for pacote, idioma in PACOTES:
            status = (["Copiando a conversa integral antes da compactação", "Documentando a conversa em segundo plano"]
                      if idioma == "pt-br" else ["Copying the full conversation before compaction", "Documenting the conversation in the background"])
            esperado = {"hooks": {"PreCompact": [{"matcher": "manual|auto", "hooks": [
                {"type": "command", "command": comando + "copia", "timeout": 120, "statusMessage": status[0]},
                {"type": "command", "command": comando + "escrita", "async": True, "timeout": 3600, "statusMessage": status[1]},
            ]}]}}
            caminho = pacote / "hooks/hooks.json"
            texto = le(caminho) if caminho.is_file() else "{}"
            try:
                atual = json.loads(texto)
            except ValueError:
                self.fail("R44: hooks/hooks.json precisa ser JSON válido")
            self.assertEqual(atual, esperado, "R44: os hooks devem seguir integralmente o Anexo E")
            self.assertNotIn("SessionStart", atual["hooks"])


if __name__ == "__main__":
    unittest.main()
