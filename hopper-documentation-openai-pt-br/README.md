# hopper-documentation-openai — português

Plugin do Codex para registrar conversas e retomar o trabalho com estado,
decisões, fontes e pendências. O redator usa **GPT-6 Luna, esforço xhigh** em uma
sessão separada. Preserva o modelo e o esforço da conversa principal.

## Instalação e uso

Requer Python 3.9+ e Codex autenticado, com as interfaces de histórico e hooks
indicadas em [histórico e limites](skills/hopper-documentation-openai/references/history.md).
Não requer outra API key nem dependências Python.

Mantenha este pacote em um diretório permanente:

```sh
codex plugin marketplace add /caminho/absoluto/deste-pacote
codex plugin add hopper-documentation-openai@hopper-documentation-openai
```

Revise os dois hooks em `/hooks` e confie somente nas definições conferidas.
Habilite o recurso nativo `hooks` se estiver desativado. A instalação não concede
confiança. Uma sessão nova carrega a skill instalada.

Use `$hopper-documentation-openai:hopper-documentation-openai` ou peça o registro
da conversa. Para executar diretamente, informe a conversa e seu diretório:

```sh
python3 skills/hopper-documentation-openai/scripts/hopper_documentation.py run --thread-id ID --cwd DIRETORIO
```

`PreCompact` registra em segundo plano antes de compactações manuais ou
automáticas. `SessionStart` fornece registros recentes da mesma conversa.
O destino é `DIRETORIO/docs-by-hopper-documentation-openai`. Sem novidade, não
chama o modelo. O registro pode terminar depois da compactação; a retomada
imediata pode receber o registro anterior.

Configuração opcional: `~/.config/hopper-documentation-openai/config.json`.
`python3 skills/hopper-documentation-openai/scripts/hopper_documentation.py config`
mostra os valores efetivos. Não há troca silenciosa de modelo.

## Recursos e verificação

O manifesto ativo é `.codex-plugin/plugin.json`. Os runtimes instalados ainda
não carregam hooks no formato portátil. `manifests/agent-plugin.json` preserva
o modelo portátil para uma migração futura, que exige nova verificação. A skill fica em
`skills/hopper-documentation-openai`; hooks em `hooks/hooks.json`. O pacote é
para Codex e não declara instalação no Claude.

Consulte as [fontes OpenAI](skills/hopper-documentation-openai/references/openai-research.md)
e os limites do executor descritos acima.
