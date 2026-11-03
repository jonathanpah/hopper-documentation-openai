#!/usr/bin/env python3
"""Avaliações de acionamento de C28. Só biblioteca padrão, Python 3.9.

Sem --idioma, roda os 46 casos. --caso pode aparecer várias vezes.
O Codex da avaliação é o do PATH; o programa da skill recebe outro
executável, o simulador de aceite/testes/apoio.py. Nunca há chamada real
ao redator. O exemplo de command_execution é congelado de U1, item 8.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

RAIZ = Path(__file__).resolve().parents[1]
CASOS = RAIZ / "aceite/casos/avaliacoes"
EXEMPLO = CASOS / "exemplo-evento.json"
PREFIXO = "HOPPER_DOCUMENTATION_OPENAI_"
PRAZO_SEGUNDOS = 600
RE_RODADA = re.compile(r"hopper_documentation_openai\.py[\"']?\s+[\"']?rodada(?:[\"']?(?:\s|$))")
RE_TIPO = re.compile(r"[a-z_]+(?:\.[a-z_]+)*")
TIPOS_DE_EVENTO = {"thread.started", "turn.started", "turn.completed", "turn.failed",
                   "item.started", "item.updated", "item.completed", "error"}


class FormatoInvalido(ValueError):
    """O fluxo deixou de seguir o contrato congelado de codex exec --json."""


def grava_json(caminho, valor):
    Path(caminho).write_text(json.dumps(valor, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def carrega_exemplo():
    exemplo = json.loads(EXEMPLO.read_text(encoding="utf-8"))
    campos = {"id": str, "type": str, "command": str, "aggregated_output": str,
              "exit_code": int, "status": str}
    if not isinstance(exemplo, dict) or set(exemplo) != {"type", "item"} or exemplo["type"] != "item.completed":
        raise FormatoInvalido("exemplo-evento.json não é um item.completed")
    item = exemplo["item"]
    if not isinstance(item, dict) or set(item) != set(campos):
        raise FormatoInvalido("campos do exemplo de command_execution fora do contrato")
    if any(type(item[k]) is not tipo for k, tipo in campos.items()):
        raise FormatoInvalido("tipos de campos do exemplo fora do contrato")
    if item["type"] != "command_execution" or item["status"] != "completed":
        raise FormatoInvalido("tipo ou status do exemplo fora do contrato")
    return exemplo


def le_eventos(caminho, exemplo):
    eventos = []
    for n, linha in enumerate(Path(caminho).read_text(encoding="utf-8").splitlines(), 1):
        if not linha.strip():
            continue
        try:
            evento = json.loads(linha)
        except ValueError as erro:
            raise FormatoInvalido(f"linha {n}: JSON inválido") from erro
        if not isinstance(evento, dict) or not isinstance(evento.get("type"), str) or not RE_TIPO.fullmatch(evento["type"]):
            raise FormatoInvalido(f"linha {n}: evento sem type no formato snake_case")
        tipo = evento["type"]
        if tipo not in TIPOS_DE_EVENTO:
            raise FormatoInvalido(f"linha {n}: type desconhecido no contrato de exec --json: {tipo}")
        if tipo.startswith("item."):
            item = evento.get("item")
            if not isinstance(item, dict) or not isinstance(item.get("type"), str) or not RE_TIPO.fullmatch(item["type"]):
                raise FormatoInvalido(f"linha {n}: item.type fora do formato snake_case")
            if any(k in item for k in ("command", "aggregated_output", "aggregatedOutput", "exit_code", "exitCode")):
                if item["type"] != "command_execution":
                    raise FormatoInvalido(f"linha {n}: comando com item.type diferente de command_execution")
            if item["type"] == "command_execution":
                modelo = exemplo["item"]
                if set(evento) != set(exemplo) or set(item) != set(modelo):
                    raise FormatoInvalido(f"linha {n}: campos de command_execution diferem de exemplo-evento.json")
                for chave, valor in modelo.items():
                    if chave == "exit_code" and tipo in ("item.started", "item.updated") and item[chave] is None:
                        continue
                    if type(item[chave]) is not type(valor):
                        raise FormatoInvalido(f"linha {n}: tipo de {chave} difere de exemplo-evento.json")
            if tipo == "item.completed" and item["type"] == "agent_message" and not isinstance(item.get("text"), str):
                raise FormatoInvalido(f"linha {n}: agent_message sem text")
        eventos.append(evento)
    if not eventos:
        raise FormatoInvalido("nenhum evento JSON recebido")
    return eventos


def confere_eventos(eventos, aciona):
    comandos = [e["item"] for e in eventos if e["type"] == "item.completed"
                and e["item"]["type"] == "command_execution" and RE_RODADA.search(e["item"]["command"])]
    falhas = []
    if not any(e["type"] == "turn.completed" for e in eventos):
        falhas.append("turn.completed ausente")
    if any(e["type"] in ("turn.failed", "error") for e in eventos):
        falhas.append("a execução informou falha")
    if not aciona:
        chamadas = [e["item"] for e in eventos if e["type"].startswith("item.")
                    and e["item"]["type"] == "command_execution" and RE_RODADA.search(e["item"]["command"])]
        if chamadas:
            falhas.append("o caso negativo executou o comando de documentação")
        return falhas, comandos, ""
    if not comandos:
        falhas.append("comando hopper_documentation_openai.py rodada ausente")
        return falhas, comandos, ""
    linhas = [l for l in comandos[-1]["aggregated_output"].splitlines() if l.strip()]
    ultima = linhas[-1] if linhas else ""
    respostas = [e["item"]["text"] for e in eventos if e["type"] == "item.completed" and e["item"]["type"] == "agent_message"]
    if not ultima:
        falhas.append("o comando não devolveu uma linha final")
    elif not respostas or ultima not in respostas[-1]:
        falhas.append("a última mensagem do agente não contém a linha final literal do comando")
    return falhas, comandos, ultima


def prepara_ambiente(temporario, idioma):
    """Instala só a skill na pasta do caso e prepara o redator simulado de C28."""
    pasta = Path(temporario).resolve()
    projeto, dados = pasta / "projeto", pasta / "dados"
    projeto.mkdir()
    dados.mkdir(mode=0o700)
    origem = RAIZ / ("hopper-documentation-openai-" + idioma) / "skills/hopper-documentation-openai"
    destino = projeto / ".agents/skills/hopper-documentation-openai"
    shutil.copytree(str(origem), str(destino), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    simulado = dados / "codex-simulado"
    # O app-server simulado recebe a identidade da conversa da avaliação.
    # O histórico e a resposta de B1 permanecem sintéticos. Nenhum histórico real é lido.
    corpo = '''import json, os, runpy
from pathlib import Path
p = Path(os.environ["HOPPER_DOCUMENTATION_OPENAI_DADOS"])
raiz = Path(RAIZ_SINTETICA)
ident = os.environ.get("CODEX_THREAD_ID", "01a2b3c4-5d6e-7f80-9a1b-2c3d4e5f6a7b")
codigo = ident.replace("-", "")[-8:]
historico = json.loads((raiz / "aceite/casos/b1/historico.json").read_text(encoding="utf-8"))
historico["thread"].update(id=ident, cwd=str(p.parent / "projeto"))
resposta = json.loads((raiz / "aceite/casos/redator/rodada-b1.json").read_text(encoding="utf-8").replace("4e5f6a7b", codigo))
if IDIOMA_SINTETICO == "en":
    for item in resposta["itens_novos"]:
        item["situacao"] = {"vigente": "in force", "concluída": "done", "aberta": "open"}[item["situacao"]]
    resposta["conversa_simplificada"] = resposta["conversa_simplificada"].replace("**Assunto: ", "**Subject: ")
for nome, valor in (("historico.json", historico), ("resposta.json", resposta)):
    temporario = p / (nome + "." + str(os.getpid()) + ".tmp")
    temporario.write_text(json.dumps(valor, ensure_ascii=False), encoding="utf-8")
    temporario.replace(p / nome)
runpy.run_path(str(raiz / "aceite/testes/apoio.py"), run_name="__main__")
'''
    corpo = "RAIZ_SINTETICA = " + repr(str(RAIZ)) + "\nIDIOMA_SINTETICO = " + repr(idioma) + "\n" + corpo
    simulado.write_text("#!" + sys.executable + "\n" + corpo, encoding="utf-8")
    simulado.chmod(0o700)
    grava_json(dados / "config.json", {"executavel": str(simulado), "migracao_automatica": False})
    env = dict(os.environ)
    for chave in list(env):
        if chave.startswith(PREFIXO):
            env.pop(chave)
    env.update({"CHAT_MEMORY_WORKER": "1", "PYTHONDONTWRITEBYTECODE": "1", "TZ": "UTC",
                PREFIXO + "DADOS": str(dados), PREFIXO + "SIMULADO_HISTORICO": str(dados / "historico.json"),
                PREFIXO + "SIMULADO_REGISTRO": str(dados / "registro-simulado"),
                PREFIXO + "SIMULADO": json.dumps([str(dados / "resposta.json")])})
    return projeto, env


def encerra_grupo(processo):
    try:
        os.killpg(processo.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    processo.wait()


def roda_caso(executavel, caso, saida, exemplo):
    idioma = caso.parent.name
    destino = saida / idioma / caso.name
    destino.mkdir(parents=True, exist_ok=True)
    esperado = json.loads((caso / "esperado.json").read_text(encoding="utf-8"))
    if not isinstance(esperado, dict) or set(esperado) != {"aciona"} or type(esperado["aciona"]) is not bool:
        raise ValueError(f"{caso}: esperado.json deve conter somente aciona booleano")
    prompt = (caso / "prompt.md").read_text(encoding="utf-8")
    resultado = {"idioma": idioma, "caso": caso.name, "esperado": esperado, "prazo_segundos": PRAZO_SEGUNDOS,
                 "exemplo_sha256": hashlib.sha256(EXEMPLO.read_bytes()).hexdigest(), "falhas": []}
    eventos_path = destino / "eventos.jsonl"
    inicio = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="hopper-avaliacao-") as temporario:
        projeto, env = prepara_ambiente(temporario, idioma)
        comando = [executavel, "exec", "--json", "--disable", "plugins", "-m", "gpt-6.1-sol",
                   "-c", 'model_reasoning_effort="medium"', "-c", 'service_tier="priority"',
                   "-s", "workspace-write", "--skip-git-repo-check", "-C", str(projeto), prompt]
        resultado["comando"] = comando
        resultado["ambiente"] = {k: v for k, v in env.items() if k.startswith(PREFIXO) or k == "CHAT_MEMORY_WORKER"}
        with eventos_path.open("w", encoding="utf-8") as eventos, (destino / "stderr.txt").open("w", encoding="utf-8") as erros:
            processo = None
            try:
                processo = subprocess.Popen(comando, stdin=subprocess.DEVNULL, stdout=eventos, stderr=erros,
                                            cwd=str(projeto), env=env, start_new_session=True)
                restante = max(0, PRAZO_SEGUNDOS - (time.monotonic() - inicio))
                resultado["codigo_codex"] = processo.wait(timeout=restante)
            except subprocess.TimeoutExpired:
                encerra_grupo(processo)
                resultado["codigo_codex"] = processo.returncode
                resultado["falhas"].append("prazo esgotado")
            except OSError as erro:
                resultado["codigo_codex"] = None
                resultado["falhas"].append(f"não foi possível executar o Codex: {erro}")
            except BaseException:
                if processo is not None:
                    encerra_grupo(processo)
                raise
        if resultado["codigo_codex"] != 0 and "prazo esgotado" not in resultado["falhas"]:
            resultado["falhas"].append(f"Codex saiu com código {resultado['codigo_codex']}")
        try:
            eventos = le_eventos(eventos_path, exemplo)
            falhas, comandos, ultima = confere_eventos(eventos, esperado["aciona"])
            resultado["falhas"].extend(falhas)
            resultado.update(eventos=len(eventos), comandos_de_documentacao=len(comandos), ultima_linha=ultima)
        except (FormatoInvalido, UnicodeError) as erro:
            resultado["falhas"].append(f"formato de eventos inválido: {erro}")
        # Os eventos e o resultado ficam; a skill, os dados e os processos simulados são temporários.
    resultado["segundos"] = round(time.monotonic() - inicio, 3)
    resultado["aprovado"] = not resultado["falhas"]
    grava_json(destino / "resultado.json", resultado)
    return resultado


def seleciona_casos(idioma, nomes):
    pastas = [CASOS / i for i in ([idioma] if idioma else ["pt-br", "en"])]
    todos = sorted(p for pasta in pastas for p in pasta.iterdir() if p.is_dir())
    if not nomes:
        if any(len([p for p in todos if p.parent == pasta]) != 23 for pasta in pastas):
            raise ValueError("a execução completa exige 23 casos por idioma")
        return todos
    faltam = set(nomes) - {p.name for p in todos}
    if faltam:
        raise ValueError("casos inexistentes: " + ", ".join(sorted(faltam)))
    return [p for p in todos if p.name in nomes]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--idioma", choices=["pt-br", "en"])
    parser.add_argument("--caso", action="append", default=[])
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    try:
        exemplo = carrega_exemplo()  # Antes de qualquer execução, inclusive nos casos negativos.
        casos = seleciona_casos(args.idioma, args.caso)
        executavel = shutil.which("codex")
        if not executavel:
            raise ValueError("codex não encontrado no PATH")
        args.saida.mkdir(parents=True, exist_ok=True)
        resultados = []
        for caso in casos:
            resultado = roda_caso(executavel, caso, args.saida.resolve(), exemplo)
            resultados.append(resultado)
            estado = "aprovada" if resultado["aprovado"] else "reprovada"
            detalhes = "; ".join(resultado["falhas"])
            print(f"{caso.parent.name}/{caso.name}: {estado}" + (f" · {detalhes}" if detalhes else ""), flush=True)
        aprovadas = sum(r["aprovado"] for r in resultados)
        resumo = {"total": len(resultados), "aprovadas": aprovadas, "reprovadas": len(resultados) - aprovadas,
                  "casos": resultados}
        grava_json(args.saida / "resumo.json", resumo)
        print(f"avaliações rodadas: {len(resultados)}, aprovadas: {aprovadas}, reprovadas: {len(resultados) - aprovadas}")
        return 0 if aprovadas == len(resultados) else 1
    except (OSError, ValueError) as erro:
        print(f"falha ao preparar as avaliações: {erro}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
