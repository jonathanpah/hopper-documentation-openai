# Testes de aceite

A suíte tem 34 testes, 1 por requisito com verificador T na seção 5 de SPEC.md.
Os outros 11 requisitos usam o conferidor, avaliações ou roteiros reais.
Não existe implementação da versão 2 na criação destes critérios.

Execute pela raiz do repositório, com Python 3.9 ou mais novo.

```sh
TZ=UTC HOPPER_DOCUMENTATION_OPENAI_PACOTE=hopper-documentation-openai-pt-br python3 -B -m unittest discover -s aceite/testes -v
```

```sh
TZ=UTC HOPPER_DOCUMENTATION_OPENAI_PACOTE=hopper-documentation-openai-en python3 -B -m unittest discover -s aceite/testes -v
```

`HOPPER_DOCUMENTATION_OPENAI_PACOTE` aceita nome relativo à raiz ou caminho
absoluto. Os testes de execução usam uma cópia temporária desse pacote.
T34, T36, T42 e T44 verificam os arquivos públicos do próprio repositório.
As expectativas vêm da spec, dos casos manuscritos e da referência anth v2.0.0.

`apoio.py` implementa o Codex simulado. `Ambiente` cria projeto, pasta do Codex,
dados e configuração temporários. A chave `executavel` aponta para um lançador
desse simulador. O PATH contém apenas os executáveis sintéticos e Python.
O programa em teste só é chamado pelos 5 comandos de C36.

O simulador recebe o histórico por
`HOPPER_DOCUMENTATION_OPENAI_SIMULADO_HISTORICO` e grava suas chamadas em
`HOPPER_DOCUMENTATION_OPENAI_SIMULADO_REGISTRO`. Essas 2 variáveis são usadas
apenas pelo apoio. As respostas do redator usam a variável SIMULADO de C36.
Uma lista de respostas tem contador persistente por lista; a última se repete.
Os campos de controle de um envelope não entram na resposta escrita em `-o`.
As esperas do simulador também respeitam ESCALA_DE_TEMPO.

As verificações de U1 ajustaram C03. O app-server não aceita
`--ignore-user-config`. O redator recebe essa opção no `exec`, e só os servidores
MCP de outras camadas precisam ser desligados por opção. Os eventos não trazem
o modelo usado. T12 verifica o modelo e o esforço do comando, sem inventar um
campo de telemetria. As fontes são V-U1-06, D-02 e D-03 do registro privado.

O programa nulo fica fora do repositório. Contra ele, todos os testes devem
reprovar em asserções de comportamento. Um documento ainda não produzido é
lido como resultado vazio para a comparação específica do requisito.
Os arquivos de entrada usam leitura estrita, e erros neles não são ocultados.
Uma execução contra o programa nulo não valida os caminhos positivos futuros.
