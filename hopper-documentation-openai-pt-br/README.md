# hopper-documentation-openai em português

Plugin do Codex que registra a conversa em 7 documentos Markdown, a pedido e antes de toda compactação. O redator usa **gpt-6-luna, esforço xhigh**, em processo separado. Preserva o modelo e o esforço da conversa principal.

Este pacote contém a versão **2.0.0**. Instale pelo GitHub a partir de uma tag publicada.

## Instalação e uso

Requer Python 3.9 ou mais novo e Codex autenticado com app-server e hooks compatíveis. Usa somente a biblioteca padrão do Python. O plugin atende macOS e Linux. Não exige outra chave de API.

Baixe `hopper-documentation-openai-2.0.0-pt-br.zip` e `SHA256SUMS` da [release](https://github.com/jonathanpah/hopper-documentation-openai/releases) quando publicados. Confira o SHA-256 e o conteúdo contra a tag.

Para atualizar uma instalação existente, substitua `<tag>` por uma tag publicada e execute os 4 comandos na ordem abaixo. Para uma instalação nova, execute os 2 últimos.

```sh
codex plugin remove hopper-documentation-openai@hopper-documentation-openai
codex plugin marketplace remove hopper-documentation-openai
codex plugin marketplace add jonathanpah/hopper-documentation-openai --ref <tag>
codex plugin add hopper-documentation-openai@hopper-documentation-openai
```

Mantenha 1 idioma instalado por conta. Confira os arquivos instalados contra a tag. Revise os 2 comandos em `/hooks` no terminal ou em **Settings > Hooks** no aplicativo e abra uma sessão nova. Instalar não concede confiança aos hooks.

Use `$hopper-documentation-openai:hopper-documentation-openai` ou peça para documentar a conversa. A skill inicia a rodada, acompanha sua conclusão e repete a linha final. Explicar, revisar ou editar a skill não inicia documentação.

Os comandos abaixo partem da pasta do plugin instalado. A execução direta usa o identificador da conversa atual.

```sh
python3 skills/hopper-documentation-openai/scripts/hopper_documentation_openai.py rodada --conversa "$CODEX_THREAD_ID"
```

O destino é `docs-by-hopper-documentation-openai/` na pasta do projeto retornada pelo histórico. Cada conversa tem uma subpasta `conversas/AAAA-MM-DD-codigo/`, com a data do primeiro turno e os últimos 8 caracteres hexadecimais do identificador. O programa amplia o código se encontrar uma colisão. Uma conversa migrada conserva a pasta criada a partir do handoff antigo.

## Documentos e retomada

| Nº | Arquivo | Local e conteúdo |
| --- | --- | --- |
| 1 | `1-indice.md` | Raiz da documentação. Ordem de leitura e tabela de conversas |
| 2 | `2-conversa-integral.md` | Pasta da conversa. Mensagens copiadas por acréscimo e origens no histórico |
| 3 | `3-conversa-simplificada.md` | Pasta da conversa. Blocos do trecho novo, com origem por parágrafo |
| 4 | `4-decisoes.md` | Raiz da documentação. Decisões e autorizações com identificadores e situações |
| 5 | `5-funcoes.md` | Raiz da documentação. Entregas concluídas, com identificadores e situações |
| 6 | `6-pendencias.md` | Raiz da documentação. Pendências, recomendações, dependências e encerramentos |
| 7 | `7-handoff.md` | Pasta da conversa. Objetivo, estado, próximo passo e instruções para continuar |

Para retomar, leia o índice, o handoff mais recente, as pendências, as decisões e as funções implementadas, nessa ordem. Depois leia a conversa simplificada pertinente. Consulte a integral para conferir uma origem. Os arquivos 2, 3 e 7 são separados por conversa; os arquivos 1, 4, 5 e 6 são compartilhados no projeto.

O copiador oculta segredos reconhecidos e registra cada uso de ferramenta em 1 linha. O redator recebe o trecho novo em partes e segue as [regras de escrita](skills/hopper-documentation-openai/regras-de-escrita.md) e os [modelos](skills/hopper-documentation-openai/modelos.md). O programa valida a resposta, atribui números aos itens e grava os documentos. Sem novidade, preserva os arquivos e dispensa o redator.

## Compactação e acompanhamento

O [gatilho PreCompact](hooks/hooks.json) executa a cópia de forma síncrona, com prazo total de 120 segundos. O comando de escrita inicia a rodada em processo separado, que continua depois do encerramento da sessão. Uma rodada posterior retoma interrupções sem repetir blocos ou itens já gravados.

O gatilho de escrita acompanha a rodada por até 3.500 segundos. Se ainda estiver em andamento, informa esse estado e deixa o processo continuar. Falhas ficam no índice e no registro `rodadas.jsonl`. A conclusão fica no registro de rodadas, dentro da pasta de dados. Os gatilhos ignoram subconversas.

## Configuração e migração

A configuração fica em `config.json` na pasta de dados do plugin. A ordem de seleção dessa pasta é `HOPPER_DOCUMENTATION_OPENAI_DADOS`, `PLUGIN_DATA` e, por último, `<pasta do Codex>/plugins/data/hopper-documentation-openai-hopper-documentation-openai/`. A pasta do Codex é `CODEX_HOME` ou, quando ausente, `~/.codex`.

O comando abaixo cria a pasta de dados, quando necessário, e mostra o caminho e os valores efetivos.

```sh
python3 skills/hopper-documentation-openai/scripts/hopper_documentation_openai.py config
```

| Chave | Padrão | Efeito |
| --- | --- | --- |
| `migracao_automatica` | `true` | Migra o formato antigo antes da rodada completa |
| `pastas_sem_migracao` | `[]` | Pula os projetos indicados, por caminho absoluto, na migração automática |
| `executavel` | `""` | Quando preenchida, seleciona o executável do Codex antes do `PATH` e de `~/.local/bin/codex` |

Antes de atualizar uma instalação com documentos antigos, grave a configuração abaixo na pasta de dados e confira o resultado de `config` antes de aprovar os hooks. Preserve um valor de `executavel` já necessário no ambiente.

```json
{
  "migracao_automatica": false,
  "pastas_sem_migracao": [],
  "executavel": ""
}
```

Prepare uma cópia de restauração antes de migrar dados reais. A migração extrai os itens do formato antigo e escreve os handoffs de cada conversa. A verificação interna confere a origem de cada arquivo, os handoffs declarados sem conteúdo com menos de 200 caracteres úteis, o formato dos itens com identificadores únicos e as conversas com seus handoffs. Só então apaga `index.md`, `handoff-*.md` e `.state` antigos.

O comando explícito recebe a pasta do projeto, não a pasta da documentação, e funciona independentemente das opções de migração automática.

```sh
python3 skills/hopper-documentation-openai/scripts/hopper_documentation_openai.py migrar --pasta /projetos/exemplo
```

Depois da preparação, escolha se deve habilitar `migracao_automatica` e quais projetos devem ficar em `pastas_sem_migracao`. Configuração, travas, diários, diagnósticos, saídas brutas e registro de rodadas permanecem na pasta de dados, fora do pacote instalado.

## Recursos e limites

O [manifesto nativo](.codex-plugin/plugin.json) aponta para a [skill](skills/hopper-documentation-openai/SKILL.md) e os [hooks](hooks/hooks.json). O [catálogo](.agents/plugins/marketplace.json) permite instalar este pacote de forma independente.

A ocultação por padrões não garante detectar todo dado sensível. A validação de origens e estrutura não garante fidelidade semântica de cada frase. Confira os documentos antes de compartilhá-los. Conversas são dados de consulta e não autorizam ações externas.

Licença [MIT](LICENSE).
