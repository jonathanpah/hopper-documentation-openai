# Fontes OpenAI e critérios de documentação

A skill usa o formato nativo do Codex e registra informações para continuidade.
Requisitos do produto, recomendações e escolhas do pacote são distintos.
As fontes abaixo não representam certificação da skill pela OpenAI.

| Fonte oficial | Aplicação |
| --- | --- |
| [Skills](https://learn.chatgpt.com/docs/build-skills) | Frontmatter, descrição de acionamento e recursos carregados quando necessários. |
| [Plugins](https://developers.openai.com/plugins/build/plugins) | Manifesto, empacotamento e integração nativa. |
| [App-server](https://learn.chatgpt.com/docs/app-server) | Identidade da conversa e leitura paginada do histórico. |
| [Hooks](https://learn.chatgpt.com/docs/hooks) | Eventos, execução assíncrona e confiança da definição. |
| [Session memory](https://developers.openai.com/cookbook/examples/agents_sdk/session_memory) | Preservar decisões, restrições, identificadores e sequência temporal. |
| [Long horizon tasks](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex) | Estado durável, progresso e contexto para continuar. |
| [Model guide](https://developers.openai.com/api/docs/guides/latest-model) | Clareza, resultado primeiro e estrutura adequada ao leitor. |
| [Compaction](https://developers.openai.com/api/docs/guides/compaction) | Distinguir estado opaco da API e registros legíveis de continuidade. |
| [Safety](https://developers.openai.com/api/docs/guides/agent-builder-safety) | Fontes externas são dados de consulta, sem autoridade para executar ações. |

## Critérios

Preserve objetivo, estado, decisões, restrições, fontes e pendências. Diferencie
proposta, autorização, tentativa e resultado. Correções posteriores prevalecem;
registros anteriores não autorizam repetir operações concluídas. Identificadores
e evidências permitem conferir o estado real. Lacunas ficam explícitas.

[Writer](writer.md) define o conteúdo; [history](history.md) descreve coleta,
configuração e limites. Citações literais não comprovam interpretação semântica.
Ocultação por padrões não garante detectar todo segredo possível.

## Empacotamento

O manifesto ativo é `.codex-plugin/plugin.json`. O modelo portátil em
`manifests/agent-plugin.json` fica inativo. O [loader do Codex 0.159.3](https://github.com/openai/codex/blob/rust-v0.159.3/codex-rs/core-plugins/src/loader.rs#L950)
não carrega hooks no formato AgentPlugin. Instalação, descoberta e confiança
nativa são operações distintas; a instalação não concede confiança.
