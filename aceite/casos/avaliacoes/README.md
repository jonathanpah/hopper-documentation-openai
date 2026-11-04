# Avaliações de acionamento

Cada idioma tem 23 casos, com `prompt.md` e `esperado.json`. A origem é o
Anth na tag v2.0.0. São os 20 casos de `evals/acionamento` em português e
`evals/triggering` em inglês, mais os 3 casos de explicar, revisar e registrar.

Os pedidos preservam o texto original, com o nome da skill adaptado para
`hopper-documentation-openai` e `CLAUDE.md` trocado por `AGENTS.md`. O cabeçalho
do avaliador do Anth foi retirado. O Codex recebe só o pedido, conforme C28.
As opções do comando e o prazo de 600 segundos ficam em `aceite/avaliacoes.py`.

`exemplo-evento.json` é a cópia literal do evento de U1, item 8. A leitura dos
comandos exige os nomes e tipos desse contrato. Eventos de outros tipos, como
`agent_message` e `turn.completed`, não são tratados como comandos.

Uma execução sem `--idioma` seleciona os 46 casos. `--caso` pode aparecer mais
de 1 vez. Os resultados ficam em `<saida>/<idioma>/<caso>/`, com os eventos
JSONL, stderr e `resultado.json`; `resumo.json` reúne a execução.

```sh
python3 aceite/avaliacoes.py --idioma pt-br --caso sim-documenta-conversa --saida /tmp/avaliacoes-openai
```

Esse comando usa o Codex do PATH para avaliar o acionamento e precisa de rede.
O programa da skill usa o Codex simulado do apoio, com o histórico e a resposta
sintéticos de B1. A pasta temporária recebe a skill do idioma escolhido e uma
configuração de dados isolada. O redator não recebe chamadas reais.

Um caso positivo exige o comando de rodada e a repetição literal da linha final
na última resposta. Um negativo exige a ausência desse comando. Uma execução
incompleta, um código de falha ou um evento fora do contrato reprova o caso.
