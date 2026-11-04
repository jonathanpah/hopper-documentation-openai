"""Additional U5/U6 regressions. All histories, writers and projects are synthetic."""

import importlib.util
import io
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'aceite/testes'))
from apoio import (CONVERSA_B1, IDIOMA, PREFIXO, TEXTO, CasoDeAceite,
                   espera, grava_json, itens, json_de, le, linhas_json, turno, usuario)


class ExecutionV2(CasoDeAceite):
    def test_round_completion_is_logged_after_all_writer_parts_finish(self):
        self.amb.grava_historico({'thread': {'id': CONVERSA_B1, 'historyMode': 'paginated'},
            'turns': [turno('t1', [usuario('p%d' % n, 'Parte %d. ' % n + 'palavra ' * 100)
                                  for n in range(1, 4)])]})
        profile = self.amb.respostas / 'partes-lentas.json'
        grava_json(profile, {'resposta': json_de(self.amb.resposta('rodada-nada-relevante')),
                            'espera_segundos': 30})
        process = self.amb.inicia('rodada', '--conversa', CONVERSA_B1, respostas=(), escala='0.02',
            extra={PREFIXO + 'SIMULADO': str(profile), PREFIXO + 'LIMITE_DA_PARTE': '1400'})
        self.assertTrue(espera(lambda: len(self.amb.chamadas()) == 3, 8))
        self.assertFalse(any(row['etapa'] == 'escrita' and row['resultado'] == 'concluída'
                             for row in self.amb.rodadas()))
        output, error = process.communicate(timeout=8)
        self.assertEqual(process.returncode, 0, output + error)
        self.assertEqual(len(linhas_json(self.amb.registro_simulado / 'exec-fins.jsonl')), 3)
        completed = [row for row in self.amb.rodadas()
                     if row['etapa'] == 'escrita' and row['resultado'] == 'concluída']
        self.assertEqual(len(completed), 1)

    def test_migration_rechecks_disk_title_and_range_before_deleting(self):
        for defect in ('title', 'range'):
            amb = self.amb if defect == 'title' else self.novo_ambiente()
            amb.formato_antigo('uma')
            result = amb.migrar(extra={PREFIXO + 'INTERROMPER_EM': 'antes-da-exclusao'})
            self.assertEqual(result.returncode, 1)
            original = le(amb.d(4))
            if defect == 'title':
                corrupted = original.replace('# ' + ('Decisões' if IDIOMA == 'pt-br' else 'Decisions'), '# Alterado', 1)
            else:
                corrupted = original.replace(TEXTO['migracao'], 'intervalo inválido')
            amb.d(4).write_text(corrupted, encoding='utf-8')
            result = amb.migrar()
            self.assertEqual(result.returncode, 1)
            self.assertEqual(len(list(amb.doc.glob('handoff-*.md'))), 3)
            self.assertEqual(len(amb.chamadas()), 1)

    def test_migration_rejects_changed_original_before_any_deletion(self):
        self.amb.formato_antigo('uma')
        result = self.amb.migrar(extra={PREFIXO + 'INTERROMPER_EM': 'antes-da-exclusao'})
        self.assertEqual(result.returncode, 1)
        originals = {p.name for p in self.amb.doc.iterdir() if p.name.startswith('handoff-')}
        target = self.amb.doc / sorted(originals)[-1]
        target.write_text(le(target) + '\nALTERACAO-POSTERIOR\n', encoding='utf-8')
        result = self.amb.migrar()
        self.assertEqual(result.returncode, 1)
        self.assertIn('mudou durante a migração', result.stdout)
        self.assertTrue(all((self.amb.doc / name).exists() for name in originals))
        self.assertIn('ALTERACAO-POSTERIOR', le(target))
        self.assertEqual(len(self.amb.chamadas()), 1)

    def test_migration_recovers_journal_and_partial_publication(self):
        for stage in ('depois-do-diario', 'meio-da-gravacao'):
            amb = self.amb if stage == 'depois-do-diario' else self.novo_ambiente()
            amb.formato_antigo('uma')
            originals = {p.name: p.read_bytes() for p in amb.doc.glob('handoff-*.md')}
            result = amb.migrar(extra={PREFIXO + 'INTERROMPER_EM': stage})
            self.assertEqual(result.returncode, 1)
            self.assertEqual({name: (amb.doc / name).read_bytes() for name in originals}, originals)
            self.sucesso(amb.migrar(), 'R29/R31')
            self.assertEqual(len(amb.chamadas()), 1)
            for number, kind in ((4, 'D'), (5, 'F'), (6, 'PD')):
                self.assertEqual([item['id'] for item in itens(le(amb.d(number)))], [kind + '1-a1b2c3d4'])
            self.assertFalse(list(amb.doc.glob('handoff-*.md')))

    def test_migration_handles_state_directory_and_dangling_links(self):
        self.amb.formato_antigo('uma')
        state = self.amb.doc / '.state'
        state.unlink()
        state.mkdir()
        (state / 'cursor.json').write_text('{"sintetico": true}', encoding='utf-8')
        outside = self.amb.projeto / 'preservar.txt'
        outside.write_text('ESTADO-NAO-ENVIAR', encoding='utf-8')
        (state / 'referencia').symlink_to(outside)
        dangling = self.amb.doc / 'handoff-20260219-090000-inexistente.md'
        dangling.symlink_to(self.amb.projeto / 'nao-existe')
        self.sucesso(self.amb.migrar(), 'R31/R32')
        self.assertFalse(state.exists())
        self.assertFalse(dangling.is_symlink())
        self.assertEqual(outside.read_text(), 'ESTADO-NAO-ENVIAR')
        self.assertNotIn('ESTADO-NAO-ENVIAR', self.amb.chamadas()[0]['stdin'])

    def test_migration_disambiguates_two_new_conversations_with_equal_suffix(self):
        self.amb.formato_antigo('duas')
        old_a = '019ca124-4000-7000-8000-1010b1c2d3e4'
        old_b = '019ca125-4000-7000-8000-1010c1d2e3f4'
        new_a = '019ca124-4000-7000-8000-10104e5f6a7b'
        new_b = '019ca125-4000-7000-8000-20204e5f6a7b'
        for path in self.amb.doc.glob('handoff-*.md'):
            if not path.is_symlink():
                path.write_text(le(path).replace(old_a, new_a).replace(old_b, new_b), encoding='utf-8')
        response = json_de(self.amb.resposta('b3/redator/duas'))
        response = json.loads(json.dumps(response).replace(old_a, new_a).replace(old_b, new_b))
        response_path = self.amb.respostas / 'colisao.json'
        grava_json(response_path, response)
        self.sucesso(self.amb.migrar(respostas=(), extra={PREFIXO + 'SIMULADO': str(response_path)}), 'R02/R31')
        handoffs = sorted((self.amb.doc / TEXTO['conversas']).glob('*/7-handoff.md'))
        self.assertEqual(len(handoffs), 2)
        self.assertEqual({p.parent.name.split('-', 3)[-1] for p in handoffs}, {'4e5f6a7b', '20204e5f6a7b'})
        for number, kind in ((4, 'D'), (5, 'F'), (6, 'PD')):
            self.assertCountEqual([item['id'] for item in itens(le(self.amb.d(number)))],
                                  [kind + '1-4e5f6a7b', kind + '1-20204e5f6a7b'])

    def test_hooks_ignore_empty_agent_id_without_starting_reader(self):
        for command in ('copia', 'escrita'):
            amb = self.amb if command == 'copia' else self.novo_ambiente()
            result = getattr(amb, command)(evento=amb.evento(agent_id=''))
            self.sucesso(result, 'R30')
            self.assertEqual(json.loads(result.stdout), {})
            self.assertEqual(len(amb.rodadas()), 1)
            self.assertEqual(amb.rodadas()[0]['resultado'], 'subconversa ignorada')
            self.assertFalse(amb.servidores())

    def test_program_reports_sandbox_block_with_literal_final_line(self):
        spec = importlib.util.spec_from_file_location('documentation_sandbox_test', self.amb.programa)
        program = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(program)
        output = io.StringIO()
        env = self.amb.ambiente(extra={'CODEX_SANDBOX': 'seatbelt'})
        with patch.dict(os.environ, env, clear=True), patch('sys.stdout', output), \
                patch.object(program.subprocess, 'Popen', side_effect=PermissionError(1, 'Operation not permitted')):
            code = program.main(['rodada', '--conversa', CONVERSA_B1])
        self.assertEqual(code, 1)
        expected = ('Documentação falhou: o sandbox da sessão bloqueou o acesso necessário.' if IDIOMA == 'pt-br'
                    else 'Documentation failed: the session sandbox blocked the required access.')
        self.assertEqual(output.getvalue().splitlines()[-1], expected)


if __name__ == '__main__':
    import unittest
    unittest.main()
