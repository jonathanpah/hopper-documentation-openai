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

O contrato é experimental; outras versões precisam de validação. Não há parser de rollout como alternativa silenciosa.
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
continua do ponto confirmado. O índice é atualizado após cada handoff publicado,
antecipando uma possível falha na parte seguinte. Na retomada, o índice é
reconstruído antes do modelo, inclusive quando não há itens novos.

## Redator

Usa `codex exec` com modelo e esforço explícitos, sessão efêmera, diretório
temporário próprio, sandbox somente leitura, JSON Schema e hooks, plugins,
apps, delegação, ferramentas de shell e injeção de memórias desabilitados.
O executor consulta o catálogo nativo de skills, desabilita todos os caminhos
descobertos somente no processo do redator e confere que nenhum permaneceu
habilitado. Se essa conferência falhar, não inicia o modelo. Preferências globais
e autenticação permanecem intactas. O código usa a biblioteca padrão do Python.

O esquema permite apenas referências das fontes efetivamente enviadas.
O prompt também proíbe ferramentas e novas tarefas. Os controles descritos
não garantem a ausência de toda capacidade de leitura em qualquer versão do
Codex. A conferência literal não prova fidelidade semântica de toda afirmação.

Uma citação inválida permite, por padrão, uma única tentativa de correção com
o mesmo modelo e as mesmas fontes. O reparo informa posição, referência e trecho;
pode trocar uma referência inexistente por uma fonte enviada. Preserva fatos e
citações válidas; ajusta somente marcadores de referências substituídas quando
nenhuma citação original daquele marcador permanece. A conferência literal
preserva maiúsculas, minúsculas e pontuação, normalizando apenas espaços e
quebras de linha. Se falhar, a parte não é publicada e seu estado não avança.
Não há nova tentativa automática para erros de execução ou mudança de modelo.

Uma falha informa a posição, a referência e o motivo de cada citação rejeitada.
O diagnóstico contém fontes enviadas, prompt, resposta original, reparos e
respostas combinadas, após ocultar padrões conhecidos de segredos. Fica em
`~/.local/state/hopper-documentation-openai/diagnostics/failure-*/failure.json`,
fora do projeto, de repositórios e do Dropbox: diretórios `0700`, arquivo `0600`.
Sucessos não guardam transcrições. A ocultação não detecta todo segredo possível;
não publique diagnósticos nem acrescente-os ao repositório da skill.

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
