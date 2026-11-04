# Casos sintéticos

Estes arquivos vêm dos Anexos B e D de SPEC.md. Nenhuma conversa real foi usada.

- `b1/` guarda o histórico abreviado, o acréscimo da segunda rodada, o turno em
  andamento, a entrada do fork e os corpos esperados em português e inglês.
  O corpo em português é literal da spec. A tradução altera somente textos fixos.
- `b2/ocultacao.json` é uma cópia sem mudança da referência anth `v2.0.0`.
  Ela já contém os 3 casos adicionais de B2 da spec do Codex.
- `b3/uma/` tem 1 conversa e 3 handoffs. `duas/` tem 2 conversas, 2 handoffs
  cada e um link para `uma/`. `continua/` usa o identificador de B1.
  `partes/` tem 2 handoffs da mesma conversa para dividir a migração.
  As 4 pastas foram escritas à mão. O handoff sem identificador é um caso extra.
- `b3/redator/` guarda as respostas manuscritas da migração. As respostas
  incompletas são JSON válido e falham nas condições internas do Anexo E.
- `redator/` guarda respostas manuscritas de rodadas, incluindo uma fora do
  esquema, uma com referência recusada e uma com mudança de item inexistente.
  Os perfis de falha usam o envelope de controle descrito em `apoio.py`.

O simulador completa campos de transporte que o histórico abreviado não mostra,
como `commandActions`, `cwd`, `arguments` e `hookRunId`. Os campos usados para
copiar a conversa permanecem iguais. As respostas foram conferidas com os
esquemas locais do app-server 0.166.0.

Os testes combinam estes casos e fazem alterações sintéticas pontuais para
limites de tamanho, tempo, referências e situações inválidas. Esses ajustes
nunca usam saídas do programa em teste para construir a expectativa.
