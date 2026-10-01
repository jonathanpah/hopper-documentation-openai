# Execução, história e limites

## Histórico nativo

O coletor usa o Codex app-server por stdio, inicializa a capacidade experimental
e consulta `thread/read` sem hidratar turnos. Confere identidade e diretório,
depois percorre `thread/turns/list` em ordem ascendente, com itens completos,
até o fim das páginas disponíveis. Não inicia nem retoma o trabalho da conversa.

Coleta mensagens, execuções de comandos, alterações de arquivos e resultados
de ferramentas MCP e dinâmicas. Exclui raciocínio, compactação opaca e contexto
injetado reconhecido. IDs e conteúdo determinam o que é novo: a conclusão
posterior de um comando já conhecido é informação nova para o registro.

Antes de particionar o prompt, o executor apresenta comando e saída como
texto, preservando quebras de linha e aspas originais. O snapshot e seus
digests continuam estruturados; a apresentação evita rejeitar citações
corretas por diferenças de escape JSON. A conferência literal permanece ativa.

O contrato é experimental. Foi conferido no Codex `0.159.3`; outras versões
precisam de validação. Não há parser de rollout como alternativa silenciosa.
Falha de leitura não avança o estado. `max_turns` limita a coleta e falha quando
excedido, sem descartar páginas silenciosamente.

## Estado e gravação

O destino é `docs-by-hopper-documentation-openai` no diretório da conversa.
Handoffs são arquivos imutáveis com nomes únicos. O índice lista os registros;
`.state` guarda digests, o último arquivo e travas. Não armazena transcrição bruta.

Se o repositório proibir registros privados ou tiver inventário fechado,
abra a conversa no diretório privado de trabalho e mantenha a fonte em uma
subpasta. Confira essa regra local antes de escolher o diretório da conversa.

Uma trava por conversa, antes da coleta e do modelo, impede redatores duplicados.
Outra trava protege publicação e índice no destino compartilhado. Arquivos
completos são publicados por link exclusivo, sem substituir handoffs. Requer
um sistema de arquivos com hard links. 
O estado avança após resposta válida e, havendo mudança material, publicação.
Metadados publicados recuperam uma queda entre handoff e atualização do estado.
Se outra parte falhar, as anteriores ficam preservadas e a próxima execução
continua do ponto confirmado. O índice é reconstruído mesmo sem chamar o modelo.

## Redator

Usa `codex exec` com modelo e esforço explícitos, sessão efêmera, diretório
temporário próprio, sandbox somente leitura, JSON Schema e hooks, plugins,
apps e delegação desabilitados. O código usa a biblioteca padrão do Python.

O prompt manda usar somente as fontes e não usar ferramentas. O Codex não
oferece neste fluxo garantia geral de ausência de toda ferramenta de leitura
local. Isolamento e prompt não comprovam essa propriedade. Citações literais
são verificadas, mas isso não prova fidelidade semântica de toda afirmação.

Uma citação inválida permite, por padrão, uma única tentativa de correção com
o mesmo modelo e as mesmas fontes. Somente as citações inválidas são substituídas;
o documento e as citações já válidas são preservados. A tentativa passa pela
conferência literal; se falhar, a parte não é publicada e seu estado não avança. Não há
nova tentativa automática para erros de execução ou mudança de modelo.

## Configuração

Em `~/.config/hopper-documentation-openai/config.json`:

| Campo | Padrão | Uso |
| --- | --- | --- |
| `model` | `gpt-6-luna` | Modelo do redator, sem fallback automático. |
| `effort` | `xhigh` | Esforço explicitamente enviado ao Codex. |
| `timeout` | `600` | Segundos por chamada. |
| `part_chars` | `100000` | Texto novo por parte. |
| `item_chars` | `24000` | Texto por item; truncamentos ficam explícitos. |
| `max_turns` | `5000` | Limite de turnos; falha quando excedido. |
| `citation_retries` | `1` | Correções após citação inválida, de 0 a 3 por parte. Cada correção chama o modelo novamente. |
| `timezone` | `America/Sao_Paulo` | Fuso de apresentação; metadados usam UTC. |
| `executable` | `codex` | Executável resolvido no PATH. |

`HOPPER_DOCUMENTATION_OPENAI_CONFIG` seleciona um arquivo alternativo para
avaliações isoladas. `config` mostra os valores. Limites e organização são
escolhas locais, não requisitos da OpenAI.

## Hooks

`PreCompact` usa `command` com `async: true`, nos gatilhos `manual|auto`.
`SessionStart` lê os registros recentes da mesma conversa em `startup|resume|compact`. Ambos usam
`PLUGIN_ROOT`. O redator desativa hooks para impedir recursão.

A compactação pode terminar antes do redator: a retomada imediata pode receber
o registro anterior. Os registros são apresentados em ordem cronológica,
com correções posteriores prevalecendo. Até 24.000 caracteres de conteúdo são
incluídos; os demais são indicados por caminho. Cada nova atualização vincula
o registro anterior. Se o último registro exceder sozinho o limite, o contexto
indica seu caminho e o índice. Não há
promessa de que o resumo termine antes da compactação ou desperte um chat
ocioso. Encerrar a sessão pode cancelar o hook.

A confiança é revisada no mecanismo nativo `/hooks`, sem bypass. Falhas
retornam JSON com `systemMessage`, preservando a compactação e partes confirmadas.

Fontes: [app-server](https://learn.chatgpt.com/docs/app-server),
[hooks](https://learn.chatgpt.com/docs/hooks) e
[compactação](https://developers.openai.com/api/docs/guides/compaction).
