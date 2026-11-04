"""T38, T39 e T45. Pastas, executável e configuração pela interface C36."""
from pathlib import Path

from apoio import CONVERSA_B1, PASTA_DADOS, PREFIXO, CasoDeAceite, grava_json, linhas_json


class Localizacao(CasoDeAceite):
    def test_R38_encontra_codex_home_definida_e_padrao(self):
        """T38. CODEX_HOME definida e padrão HOME/.codex, com rodada completa."""
        for definido in (True, False):
            amb = self.amb if definido else self.novo_ambiente()
            amb.historico_b1()
            codex = amb.raiz / "outra-pasta-codex" if definido else amb.casa / ".codex"
            dados = codex / PASTA_DADOS
            dados.mkdir(parents=True)
            dados.chmod(0o700)
            grava_json(dados / "config.json", {"executavel": str(amb.simulado)})
            extra = {"CODEX_HOME": str(codex) if definido else None, PREFIXO + "DADOS": None, "PLUGIN_DATA": None}
            r = amb.roda("config", extra=extra)
            self.sucesso(r, "R38")
            self.assertIn(str(dados), r.stdout, "R38: o caminho dos dados deve respeitar a pasta do Codex")
            self.sucesso(amb.rodada(extra=extra), "R38")
            self.documento(2, "R38", amb)
            self.documento(7, "R38", amb)
            registro = linhas_json(dados / "rodadas.jsonl")
            self.assertTrue(any(l.get("conversa") == CONVERSA_B1 and l.get("etapa") == "escrita" and l.get("resultado") == "concluída" for l in registro))
            self.assertTrue(all(s["env"].get("CODEX_HOME", str(amb.casa / ".codex")) == str(codex) for s in amb.servidores()))

    def test_R39_escolhe_executavel_config_antes_path_antes_local(self):
        """T39. 3 candidatos isolados e caminho efetivo no registro da rodada."""
        for escolha in ("config", "PATH", "local"):
            amb = self.amb if escolha == "config" else self.novo_ambiente()
            amb.historico_b1()
            local = amb.instala_simulado(amb.casa / ".local/bin/codex")
            if escolha == "config":
                esperado = amb.simulado
            else:
                amb.configura(executavel="")
                esperado = amb.bin / "codex"
                if escolha == "local":
                    esperado.unlink()
                    esperado = local
            self.sucesso(amb.rodada(), "R39")
            linhas = [l for l in amb.rodadas() if l.get("etapa") == "escrita" and l.get("resultado") == "concluída"]
            self.assertTrue(linhas, "R39: a rodada deve registrar o executável realmente usado")
            self.assertEqual(Path(linhas[-1]["executavel"]).resolve(), esperado.resolve())
            self.assertTrue(amb.chamadas(), "R39: o candidato escolhido deve executar o redator simulado")

    def test_R45_config_mostra_pasta_valores_padrao_e_efetivos(self):
        """T45. Precedência DADOS, PLUGIN_DATA e Codex; criação 0700 e 3 valores."""
        preferida = self.amb.raiz / "dados-preferidos"
        plugin_data = self.amb.raiz / "plugin-data"
        extra = {PREFIXO + "DADOS": str(preferida), "PLUGIN_DATA": str(plugin_data)}
        r = self.amb.roda("config", extra=extra)
        self.sucesso(r, "R45")
        self.assertIn(str(preferida), r.stdout, "R45: config deve informar a pasta de dados efetiva")
        for chave in ("migracao_automatica", "pastas_sem_migracao", "executavel"):
            self.assertIn(chave, r.stdout)
        self.assertRegex(r.stdout, r"migracao_automatica[\"']?\s*[:=]\s*(?:true|True|verdadeir[ao])")
        self.assertRegex(r.stdout, r"pastas_sem_migracao[\"']?\s*[:=]\s*\[\s*\]")
        self.assertRegex(r.stdout, r"(?m)executavel[\"']?\s*[:=]\s*(?:\"\"|''|vazio|empty|$)")
        self.assertTrue(preferida.is_dir())
        self.assertEqual(preferida.stat().st_mode & 0o777, 0o700)
        excluida = str(self.amb.projeto)
        grava_json(preferida / "config.json", {"migracao_automatica": False, "pastas_sem_migracao": [excluida], "executavel": str(self.amb.simulado)})
        r = self.amb.roda("config", extra=extra)
        self.sucesso(r, "R45")
        for valor in (str(preferida), "migracao_automatica", "pastas_sem_migracao", "executavel", excluida, str(self.amb.simulado)):
            self.assertIn(valor, r.stdout)
        self.assertRegex(r.stdout, r"migracao_automatica[\"']?\s*[:=]\s*(?:false|False|fals[ao])")
        r = self.amb.roda("config", extra={PREFIXO + "DADOS": None, "PLUGIN_DATA": str(plugin_data)})
        self.sucesso(r, "R45")
        self.assertIn(str(plugin_data), r.stdout)
        self.assertEqual(plugin_data.stat().st_mode & 0o777, 0o700)
        r = self.amb.roda("config", extra={PREFIXO + "DADOS": None, "PLUGIN_DATA": None})
        self.sucesso(r, "R45")
        self.assertIn(str(self.amb.codex / PASTA_DADOS), r.stdout)


if __name__ == "__main__":
    import unittest
    unittest.main()
