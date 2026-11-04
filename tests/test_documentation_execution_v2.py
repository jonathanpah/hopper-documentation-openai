"""Additional U5/U6 regressions. All histories, writers and projects are synthetic."""

import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'aceite/testes'))
from apoio import (CONVERSA_B1, IDIOMA, PREFIXO, SIMULADO, TEXTO, CasoDeAceite,
                   espera, grava_json, itens, json_de, le, linhas_json, mensagens, turno, usuario)


class ExecutionV2(CasoDeAceite):
    def strict_app_server(self):
        """Freeze the option names from `codex app-server --help` 0.166.0."""
        values = ('-c', '--config', '--enable', '--disable', '--startup-client-info',
                  '--cloud-skills-snapshot', '--code-mode-host', '--listen', '--ws-auth',
                  '--ws-token-file', '--ws-token-sha256', '--ws-shared-secret-file',
                  '--ws-issuer', '--ws-audience', '--ws-max-clock-skew-seconds')
        flags = ('--startup-sign-out', '--print-startup-config', '--strict-config',
                 '--stdio', '--analytics-default-enabled', '-h', '--help')
        launcher = self.amb.dados / 'codex-cli-0166'
        launcher.write_text('#!' + sys.executable + '\n' +
            'values = ' + repr(values) + '\nflags = ' + repr(flags) + '\n' + '''
import runpy
import sys
from pathlib import Path

if sys.argv[1:2] == ['app-server']:
    arguments = iter(sys.argv[2:])
    for argument in arguments:
        option, separator, value = argument.partition('=')
        if option not in values + flags or (option in flags and separator):
            message = "error: unexpected argument '%s' found" % option
            with Path(__file__ + '.errors').open('a', encoding='utf-8') as errors:
                errors.write(message + '\\n')
            print(message, file=sys.stderr)
            raise SystemExit(2)
        if option in values and not separator:
            if next(arguments, None) is None:
                print("error: a value is required for '%s'" % option, file=sys.stderr)
                raise SystemExit(2)
''' + 'runpy.run_path(' + repr(str(SIMULADO)) + ', run_name="__main__")\n',
            encoding='utf-8')
        launcher.chmod(0o755)
        self.amb.configura(executavel=str(launcher))
        return launcher

    def test_strict_app_server_rejects_options_absent_from_real_help(self):
        """G12/D-18. The fake must fail before its permissive RPC delegate."""
        launcher = self.strict_app_server()
        for option in ('--ignore-rules', '--ignore-user-config', '--unknown-option', '--lis'):
            with self.subTest(option=option):
                result = subprocess.run([str(launcher), 'app-server', '--listen', 'stdio://', option],
                                        capture_output=True, text=True, timeout=5,
                                        env=self.amb.ambiente(), cwd=str(self.amb.raiz))
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stderr.strip(), "error: unexpected argument '%s' found" % option)
        self.assertFalse(self.amb.servidores())
        self.assertFalse(self.amb.rpc())

    def test_round_writes_with_only_real_app_server_options(self):
        """G12/D-18. All readers must pass the real CLI option boundary."""
        self.amb.historico_b1()
        launcher = self.strict_app_server()
        result = self.amb.rodada()
        errors = Path(str(launcher) + '.errors')
        self.sucesso(result, 'G12/D-18\n' + (le(errors) if errors.is_file() else ''))
        self.assertFalse(errors.exists())
        self.assertEqual(len(mensagens(le(self.amb.d(2)))), 14)
        for number in (3, 7):
            self.assertTrue(self.amb.d(number).is_file())
            self.assertIn('M14-', le(self.amb.d(number)))
        self.terminou('G12/D-18')
        self.assertEqual(len(self.amb.chamadas()), 1)
        self.assertIn('--ignore-rules', self.amb.chamadas()[0]['argv'])
        self.assertEqual(sum(row['method'] == 'config/read' for row in self.amb.rpc()), 2)

    def slow_reader_startup(self, seconds):
        launcher = self.amb.dados / 'leitor-lento'
        launcher.write_text(
            '#!' + sys.executable + '\nimport runpy\nimport sys\nimport time\n'
            'if sys.argv[1:2] == ["app-server"]:\n    time.sleep(' + repr(seconds) + ')\n'
            'runpy.run_path(' + repr(str(SIMULADO)) + ', run_name="__main__")\n',
            encoding='utf-8')
        launcher.chmod(0o755)
        self.amb.configura(executavel=str(launcher))

    def slow_reader_shutdown(self, seconds):
        """Delay SIGTERM in the temporary simulator, never in the shipped program."""
        marker = self.amb.registro_simulado / 'encerramentos-lentos.jsonl'
        launcher = self.amb.dados / 'leitor-encerramento-lento'
        launcher.write_text(
            '#!' + sys.executable + '\nimport json\nimport os\nimport runpy\n'
            'import signal\nimport sys\nimport time\nfrom pathlib import Path\n'
            'if sys.argv[1:2] == ["app-server"]:\n'
            '    def stop(signum, frame):\n'
            '        with Path(' + repr(str(marker)) + ').open("a", encoding="utf-8") as stream:\n'
            '            stream.write(json.dumps({"pid": os.getpid()}) + "\\n")\n'
            '        time.sleep(' + repr(seconds) + ')\n'
            '        raise SystemExit(0)\n'
            '    signal.signal(signal.SIGTERM, stop)\n'
            'runpy.run_path(' + repr(str(SIMULADO)) + ', run_name="__main__")\n',
            encoding='utf-8')
        launcher.chmod(0o755)
        self.amb.configura(executavel=str(launcher))
        return marker

    def test_reader_shutdown_waits_fit_the_remaining_deadline(self):
        """R22. Both graceful shutdown and reaping share the time still available."""
        spec = importlib.util.spec_from_file_location('documentation_shutdown_test', self.amb.programa)
        program = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(program)
        elapsed = [9.75]
        deadline = 10.0
        process = Mock(stdin=io.BytesIO())
        process.poll.return_value = None
        process.terminate.side_effect = lambda: elapsed.__setitem__(0, elapsed[0] + 0.1)
        reaped = []

        def wait(timeout=None):
            self.assertIsNotNone(timeout, 'Reader reaping must have a deadline')
            self.assertLessEqual(timeout, max(0, deadline - elapsed[0]))
            needed = 0.03 if process.kill.called else 0.5
            elapsed[0] += min(timeout, needed)
            if timeout < needed:
                raise subprocess.TimeoutExpired('synthetic-reader', timeout)
            reaped.append(True)
            return 0

        process.wait.side_effect = wait
        selector = Mock()
        selector.select.return_value = [True]
        response = b'{"id": 1, "result": {}}\n'
        runtime = Mock(executable='synthetic-reader', data=self.amb.dados)
        with patch.dict(os.environ, {PREFIXO + 'ESCALA_DE_TEMPO': '1'}), \
                patch.object(program, 'time', Mock(monotonic=lambda: elapsed[0])), \
                patch.object(program.subprocess, 'Popen', return_value=process), \
                patch.object(program.selectors, 'DefaultSelector', return_value=selector), \
                patch.object(program.os, 'read', return_value=response):
            with program.AppServer(runtime, deadline=deadline):
                pass
        self.assertTrue(reaped, 'The reader must be reaped before returning')
        process.kill.assert_called_once_with()
        self.assertLessEqual(elapsed[0], deadline)
        self.assertTrue(process.stdin.closed)
        process.stdout.close.assert_called_once_with()

    def test_copy_reserves_time_for_slow_reader_shutdown(self):
        """R22. A blocked page and slow SIGTERM must leave saved messages recoverable."""
        case = {'thread': {'id': CONVERSA_B1, 'historyMode': 'paginated'},
                'turns': [turno('t1', [usuario('u1', 'Antes do atraso.')]),
                          turno('t2', [usuario('u2', 'Depois do atraso.')], 1773500460)],
                'opcoes': {'atraso': {'turno': 't2', 'segundos': 150}}}
        self.amb.grava_historico(case)
        marker = self.slow_reader_shutdown(0.5)
        started = time.monotonic()
        result = self.amb.copia(escala='0.03', tempo=6)
        elapsed = time.monotonic() - started
        self.sucesso(result, 'R22/slow shutdown')
        self.assertEqual(json.loads(result.stdout), {})
        self.assertLessEqual(elapsed, 3.2, 'R22: slow reader shutdown exceeded the copy limit')
        self.assertTrue(linhas_json(marker), 'The slow shutdown handler was not exercised')
        for server in self.amb.servidores():
            with self.assertRaises(ProcessLookupError):
                os.kill(server['pid'], 0)
        saved = self.amb.d(2).read_bytes()
        self.assertEqual(len(mensagens(saved.decode('utf-8'))), 1)
        self.assertTrue(any(row['etapa'] == 'copia' and row.get('motivo')
                            for row in self.amb.rodadas()))
        self.assertFalse(self.amb.chamadas())
        case.pop('opcoes')
        self.amb.grava_historico(case)
        self.amb.configura(executavel=str(self.amb.simulado))
        self.sucesso(self.amb.rodada(respostas=('rodada-nada-relevante',)), 'R22/recovery')
        self.assertTrue(self.amb.d(2).read_bytes().startswith(saved))
        self.assertEqual(len(mensagens(le(self.amb.d(2)))), 2)

    def test_reader_startup_has_a_floor_at_small_time_scale(self):
        """G12/T23/T24. Simulate 2 s per response without wall-clock timing."""
        spec = importlib.util.spec_from_file_location('documentation_reader_test', self.amb.programa)
        program = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(program)
        elapsed = [0.0]
        clock = Mock(monotonic=lambda: elapsed[0])
        process = Mock(stdin=io.BytesIO())
        process.poll.return_value = 0
        selector = Mock()

        def wait_for_response(timeout):
            elapsed[0] += min(2.0, timeout)
            return [True] if timeout >= 2.0 else []

        selector.select.side_effect = wait_for_response
        responses = [(json.dumps({'id': n, 'result': {'data': []}}) + '\n').encode('utf-8')
                     for n in range(1, 4)]
        runtime = Mock(executable='synthetic-reader', data=self.amb.dados)
        with patch.dict(os.environ, {PREFIXO + 'ESCALA_DE_TEMPO': '0.002'}), \
                patch.object(program, 'time', clock), \
                patch.object(program.subprocess, 'Popen', return_value=process), \
                patch.object(program.selectors, 'DefaultSelector', return_value=selector), \
                patch.object(program.os, 'read', side_effect=responses):
            with program.AppServer(runtime) as server:
                for method in ('thread/turns/list', 'thread/items/list'):
                    self.assertEqual(server.call(method, {}), {'data': []})
        self.assertEqual(elapsed[0], 6.0)

    def test_round_finishes_with_slow_reader_startup(self):
        """G12/T23/T24. Also exercise the real subprocess and complete writer round."""
        self.amb.historico_b1()
        self.slow_reader_startup(0.5)
        result = self.amb.rodada(escala='0.002', tempo=30)
        self.sucesso(result, 'G12/T23/T24')
        self.assertEqual(len(mensagens(le(self.amb.d(2)))), 14)
        self.assertTrue(self.amb.d(3).is_file())
        self.assertTrue(self.amb.d(7).is_file())
        self.assertEqual(len(self.amb.chamadas()), 1)

    def test_reader_pages_have_a_floor_at_small_time_scale(self):
        """G12. Slow turn and item pages must remain readable in both history modes."""
        variants = [('paginated', 'thread/turns/list'), ('paginated', 'thread/items/list'),
                    ('legacy', 'thread/turns/list')]
        for number, (mode, method) in enumerate(variants):
            with self.subTest(mode=mode, method=method):
                amb = self.amb if number == 0 else self.novo_ambiente()
                amb.grava_historico({'thread': {'id': CONVERSA_B1, 'historyMode': mode},
                    'turns': [turno('t1', [usuario('u1', 'Primeira mensagem.'),
                                           usuario('u2', 'Segunda mensagem.')]),
                              turno('t2', [usuario('u3', 'Terceira mensagem.')], 1773500460)],
                    'opcoes': {'pagina_turnos': 1, 'pagina_registros': 1,
                               'atraso': {'metodo': method, 'turno': 't1', 'segundos': 150}}})
                result = amb.rodada(respostas=('rodada-nada-relevante',), escala='0.002', tempo=10)
                self.sucesso(result, 'G12/pages')
                self.assertEqual([message[3].strip() for message in mensagens(le(amb.d(2)))],
                                 ['Primeira mensagem.', 'Segunda mensagem.', 'Terceira mensagem.'])
                self.assertTrue(any(row['method'] == method and row['params'].get('cursor')
                                    for row in amb.rpc()))

    def test_copy_deadline_still_limits_slow_reader_startup(self):
        """R22/G12. The scaled 100-second limit takes precedence over the reader floor."""
        self.amb.historico_b1()
        self.slow_reader_startup(0.5)
        result = self.amb.copia(escala='0.002', tempo=3)
        self.sucesso(result, 'R22/G12')
        self.assertEqual(json.loads(result.stdout), {})
        self.assertTrue(any(row['etapa'] == 'copia' and row['resultado'] == 'falhou'
                            and 'prazo de leitura' in row['motivo'] for row in self.amb.rodadas()))
        self.assertFalse(self.amb.servidores(), 'The reader outlived the scaled copy deadline')
        self.assertFalse(self.amb.rpc())
        self.assertFalse(self.amb.chamadas())

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
