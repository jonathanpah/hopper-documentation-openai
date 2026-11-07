---
name: hopper-documentation-openai
description: Documenta a conversa atual do Codex, ou outra conversa indicada pelo código, em 7 documentos (índice, conversa integral, conversa simplificada, decisões, funções implementadas, pendências e handoff) na pasta docs-by-hopper-documentation-openai do projeto. Use quando o usuário pedir para documentar ou registrar a conversa, salvar o progresso, fazer um handoff ou documentar outra conversa antes de continuá-la. Não use para explicar, revisar ou editar esta skill.
---

# hopper-documentation-openai

## O que a skill produz

A skill registra a conversa atual em 7 documentos Markdown na pasta `docs-by-hopper-documentation-openai` do projeto. Existe 1 subpasta por conversa, identificada pela data do primeiro turno e pelo código da conversa.

- O índice reúne a ordem de leitura e as conversas do projeto.
- A conversa integral preserva as mensagens por acréscimo. O programa oculta segredos e resume cada uso de ferramenta em 1 linha.
- A conversa simplificada reescreve o conteúdo em frases curtas, com a origem de cada parágrafo.
- Decisões, funções implementadas e pendências têm identificadores, origens e situações. Funções implementadas incluem qualquer entrega concluída.
- O handoff reúne objetivo, estado atual, próximo passo, decisões, autorizações, restrições, descobertas, pendências, lacunas e instruções para retomar.

O programa copia a conversa integral. O redator usa `gpt-6-luna` com esforço `xhigh`, isolado de ferramentas, seguindo [regras-de-escrita.md](regras-de-escrita.md) e [modelos.md](modelos.md). O programa valida a resposta, numera os itens e grava os documentos.

O gatilho executa a cópia antes de toda compactação e inicia a mesma rodada em processo separado. Com migração automática ligada, a primeira rodada migra os handoffs antigos e só os apaga depois da verificação interna. As pastas excluídas na configuração ficam fora da migração automática.

## Como a skill roda

1. Inicie o comando abaixo nesta resposta. Substitua `<pasta desta skill>` pela pasta que contém este `SKILL.md`. Use a ferramenta de comando do Codex em segundo plano, com espera inicial curta.

   ```sh
   python3 "<pasta desta skill>/scripts/hopper_documentation_openai.py" rodada --conversa "$CODEX_THREAD_ID"
   ```

   Se o pedido for para documentar outra conversa, troque `"$CODEX_THREAD_ID"` pelo código que o usuário indicar. O código tem 8 ou 12 letras e aparece na tabela do índice da pasta, como em "documente a conversa 57f1a26f". O identificador completo também serve. A outra conversa precisa ter rodado nesta mesma máquina e nesta mesma conta.

2. Diga em 1 frase que a documentação começou em segundo plano.
3. Acompanhe o mesmo processo até terminar. Se a ferramenta devolver um identificador de sessão, use-o para obter a saída restante.
4. Repita ao usuário a última linha da saída do programa, sem mudar o texto, inclusive quando ela informar falha ou ausência de novidade.

Se o sandbox da sessão impedir o acesso necessário, o programa informa `Documentação falhou: o sandbox da sessão bloqueou o acesso necessário.` Repita essa linha. Preserve as permissões da sessão e informe o resultado do programa.

Deixe a gravação dos documentos a cargo do programa. Preserve o modelo e o esforço do redator. Um pedido para explicar, revisar ou editar esta skill, ou para explicar o que é um handoff, pede somente essa análise ou alteração, sem executar a rodada.
