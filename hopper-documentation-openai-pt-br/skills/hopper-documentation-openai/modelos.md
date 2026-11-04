# Modelos dos documentos

O programa grava os cabeçalhos, os títulos dos blocos e os identificadores finais. Você escreve o conteúdo. Use `N1`, `N2`… para os itens novos em qualquer campo; o programa troca essas referências pelos identificadores finais.

Cite só mensagens do trecho novo ou anteriores a ele e itens existentes na pasta. Use `N1`, `N2`… para itens novos desta resposta. Para falar do que vem depois do trecho novo, escreva sem identificador. Na migração, cite arquivos antigos e itens, pois as mensagens não existem.

## Documento 3, conversa simplificada

O campo `conversa_simplificada` é o corpo de 1 bloco. Ele começa com a linha de assunto e segue com parágrafos curtos. Cada parágrafo termina com as mensagens de origem entre parênteses, separadas por vírgula. Um intervalo usa a forma `M3-4e5f6a7b a M7-4e5f6a7b`.

```markdown
**Assunto: falha do registro automático do Codex.**

O registro automático do Codex falhou antes da compactação. O programa recusou 2 citações que não estavam iguais na conversa. (M1-4e5f6a7b)
```

Quando o trecho não traz nada relevante, devolva `nada_relevante` igual a `true` e deixe `conversa_simplificada` vazio.

## Documentos 4, 5 e 6, itens

Cada item de `itens_novos` tem `tipo` (`D` decisão, `F` função implementada, `PD` pendência), `texto` (1 ou 2 frases), `origem` (mensagens do trecho novo ou itens existentes), `situacao` e, só nas pendências, `recomendacao` e `depende_de`. "Função implementada" é qualquer entrega concluída na conversa: código, configuração, documento ou processo.

Situações permitidas:

| Tipo | Situações |
| --- | --- |
| D, decisões | `vigente`, `substituída por <ID>`, `revogada em <M-ID>` |
| F, funções implementadas | `concluída`, `substituída por <ID>`, `desfeita em <M-ID>` |
| PD, pendências | `aberta`, `encerrada em <M-ID> (<motivo curto>)` |

Como o programa grava um item:

```markdown
### PD1-4e5f6a7b
Escolher o formato do gráfico.

- Recomendação: comparar barras e linhas.
- Depende de: o usuário escolher o formato do gráfico.
- Origem: M66-4e5f6a7b
- Situação: aberta
- Intervalo da rodada: M56-4e5f6a7b a M80-4e5f6a7b
```

Para mudar a situação de um item que já existe, inclusive de outra conversa da mesma pasta, use `mudancas`, com o identificador, a situação nova e a origem. A origem de um item novo ou de uma mudança é uma mensagem do trecho novo ou um item existente, nunca uma mensagem de um trecho anterior. Na migração, a origem é o nome do arquivo antigo.

## Documento 7, handoff

As 9 chaves do campo `handoff` viram as 9 seções, nesta ordem: Objetivo; Pautas e estado atual; Próximo passo; Decisões e autorizações vigentes; Restrições vigentes; Descobertas e tentativas descartadas; Pendências e compromissos; Lacunas; Como retomar. Escreva cada seção em parágrafos curtos, cada um com as mensagens de origem entre parênteses. O handoff é reescrito inteiro a cada rodada: inclua o que ainda vale do handoff anterior.

## Resumo

O campo `resumo` tem até 80 caracteres e vai para o índice da pasta, na coluna "Assunto".

## Migração

A resposta traz `handoffs_antigos`, com 1 entrada por conversa dos arquivos desta parte. Cada entrada contém `conversa`, `resumo` de até 80 caracteres e `handoff` com as 9 chaves. O programa calcula as datas pelo nome do handoff mais antigo. Não inclua `data` na resposta.

Cada item novo também traz `conversa`. As origens citam os nomes dos arquivos antigos enviados. Cite nos parágrafos do handoff os arquivos de origem. Preserve no novo handoff o conteúdo vigente de `handoff_anterior` quando uma conversa continuar em outra parte.

`sem_conteudo` lista somente handoffs com menos de 200 caracteres úteis, sem títulos e referências. O programa confere a contagem. Um handoff intermediário com 200 ou mais caracteres precisa de origem em um item ou no handoff. O programa classifica `index.md` e `.state` sem enviá-los ao redator. Links simbólicos não são lidos.
