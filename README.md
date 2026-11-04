# hopper-documentation-openai

Plugin do Codex que registra cada conversa em 7 documentos Markdown, a pedido e antes de toda compactação. O redator usa **gpt-6-luna, esforço xhigh**, em um processo separado. O modelo e o esforço da conversa principal são preservados.

A versão **2.0.0** segue o [SPEC.md](SPEC.md). Consulte a situação de publicação no [changelog](CHANGELOG.md). Os comandos de instalação exigem uma tag já publicada, de teste ou de release.

| Pacote | Idioma | Guia |
| --- | --- | --- |
| `hopper-documentation-openai-pt-br/` | Português brasileiro | [README](hopper-documentation-openai-pt-br/README.md) |
| `hopper-documentation-openai-en/` | Inglês | [README](hopper-documentation-openai-en/README.md) |

Cada pacote contém o plugin completo e seu próprio catálogo. Os programas Python diferem somente na linha `LANGUAGE`. Instale 1 idioma por conta. O catálogo da raiz seleciona português.

## Uso e documentos

Chame `$hopper-documentation-openai:hopper-documentation-openai` ou peça para registrar a conversa. O destino é `docs-by-hopper-documentation-openai/` na pasta do projeto informada pelo histórico do Codex.

O índice reúne as conversas. Cada conversa tem sua cópia integral, uma versão simplificada e 1 handoff atualizado. Decisões, funções implementadas e pendências ficam em documentos compartilhados do projeto. Os [nomes e a ordem de leitura](hopper-documentation-openai-pt-br/README.md#documentos-e-retomada) estão no guia do pacote.

O copiador preserva as mensagens por acréscimo, oculta segredos reconhecidos e resume cada uso de ferramenta em 1 linha. O redator recebe o trecho novo e os documentos atuais. Sem novidade, a rodada preserva os documentos e dispensa o redator.

O evento `PreCompact`, manual ou automático, executa a cópia síncrona com prazo de 120 segundos e inicia a escrita em processo separado. Depois de 3.500 segundos, o gatilho pode informar andamento enquanto a escrita continua. A retomada segue os documentos gravados e o registro de rodadas.

## Instalação

Requer Python 3.9 ou mais novo e Codex autenticado, com app-server e hooks compatíveis. O programa usa somente a biblioteca padrão. Não exige outra chave de API nem pacotes Python.

Para atualizar uma instalação existente, substitua `<tag>` por uma tag publicada e execute os 4 comandos na ordem abaixo. Para uma instalação nova, execute os 2 últimos.

```sh
codex plugin remove hopper-documentation-openai@hopper-documentation-openai
codex plugin marketplace remove hopper-documentation-openai
codex plugin marketplace add jonathanpah/hopper-documentation-openai --ref <tag>
codex plugin add hopper-documentation-openai@hopper-documentation-openai
```

A release final usa `v2.0.0`; as instalações de teste usam a tag escolhida pelo executor. Confira os arquivos instalados contra a tag. Revise os 2 comandos em `/hooks` ou em **Settings > Hooks** no aplicativo. A confiança depende da definição instalada. Abra uma sessão nova depois da troca.

A instalação pelo GitHub usa o catálogo da raiz, que seleciona o pacote em português. Os ZIPs dos 2 idiomas ficam na [release](https://github.com/jonathanpah/hopper-documentation-openai/releases) para conferência de `SHA256SUMS` e do conteúdo.

Antes de habilitar os hooks em uma atualização com documentos antigos, configure `migracao_automatica` como `false`. Confira a configuração pelo comando `config` e prepare a migração conforme o [guia em português](hopper-documentation-openai-pt-br/README.md#configuração-e-migração).

## Verificações locais

Requer Make e Python 3.9 ou mais novo. Os testes usam dados e Codex simulados, sem rede nem modelo real.

| Comando | Resultado |
| --- | --- |
| `make build` | Valida os pacotes e gera 2 ZIPs reproduzíveis e `SHA256SUMS` em `build/` |
| `make test` | Roda os testes do executor nos 2 idiomas |
| `make test-acceptance` | Roda os testes congelados de `aceite/testes/` nos 2 idiomas |
| `make check` | Executa build, testes do executor e testes de aceite |

Use `PYTHON=/usr/bin/python3` ou outro interpretador compatível para selecionar o Python. Os testes rodam com `TZ=UTC`. Consulte o [guia de contribuição](CONTRIBUTING.md) para conferir os critérios congelados, os casos do conferidor e os limites das provas locais.

O build gera `hopper-documentation-openai-2.0.0-pt-br.zip`, `hopper-documentation-openai-2.0.0-en.zip` e `SHA256SUMS`. Cada ZIP contém os arquivos da pasta do pacote, inclusive os manifestos ocultos, sem uma pasta adicional na raiz. `build/` é uma saída local ignorada pelo Git. A publicação segue C29 do [SPEC.md](SPEC.md), a partir da tag.

[Índice](index.md) · [Alterações](CHANGELOG.md) · [Segurança](SECURITY.md) · [Licença MIT](LICENSE)
