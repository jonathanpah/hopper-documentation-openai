# Alterações

## 2.1.0 (2026-11-07)

- O índice manda documentar a conversa antes de continuá-la e ler só o handoff dela. Os demais documentos ficam para consulta.
- O redator recebe só as decisões vigentes, as funções implementadas da conversa e as pendências abertas.
- A rodada a pedido aceita o código de 8 ou 12 letras do índice, para documentar outra conversa.
- Uma decisão vigente repetida com o mesmo texto reaproveita o identificador.
- Recomendação e dependência preenchidas em decisão ou função são limpas, sem recusar a resposta inteira.
- Regras de escrita alinhadas às regras de forma do proprietário.
- Critérios congelados ajustados com o "sim" do proprietário, na marca `criterios-v2.1.0`.

## 2.0.0 (2026-11-04)

- Registra cada conversa em 7 documentos, com índice, conversa integral, conversa simplificada, decisões, funções implementadas, pendências e handoff.
- Copia o histórico por acréscimo, com paginação nativa, origens verificáveis, identificação por conversa e ocultação de segredos reconhecidos.
- Usa `gpt-6-luna` com esforço `xhigh` para redigir o trecho novo em partes, com validação, travas, diário e retomada após interrupções.
- Executa a cópia síncrona e a escrita em processo separado antes de compactações manuais e automáticas. A skill executa a mesma rodada a pedido.
- Migra o formato antigo para os documentos novos e apaga as origens somente depois das 4 verificações internas. Permite desligar a migração automática e excluir projetos dela.
- Centraliza configuração, diagnósticos e registros na pasta de dados do plugin. O comando `config` mostra o caminho e os valores efetivos.
- Distribui 2 plugins completos, em português e inglês, com manifesto nativo e programas que diferem somente em `LANGUAGE`.
- Remove programas, referências e manifestos antigos. Atualiza documentação, build reproduzível, nomes dos ZIPs e testes de empacotamento para Python 3.9 ou mais novo.
- Limitação conhecida: em pastas grandes do formato antigo, a migração pode parar com "arquivos sem destino", "referências recusadas" ou "conversas diferentes das dos arquivos antigos". Nesse caso nenhum arquivo antigo é apagado, o próximo `migrar` retoma pela parte que falhou, e a pasta pode entrar em `pastas_sem_migracao`.
