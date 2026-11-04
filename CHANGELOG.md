# Alterações

## 2.0.0 (não publicada)

- Registra cada conversa em 7 documentos, com índice, conversa integral, conversa simplificada, decisões, funções implementadas, pendências e handoff.
- Copia o histórico por acréscimo, com paginação nativa, origens verificáveis, identificação por conversa e ocultação de segredos reconhecidos.
- Usa `gpt-6-luna` com esforço `xhigh` para redigir o trecho novo em partes, com validação, travas, diário e retomada após interrupções.
- Executa a cópia síncrona e a escrita em processo separado antes de compactações manuais e automáticas. A skill executa a mesma rodada a pedido.
- Migra o formato antigo para os documentos novos e apaga as origens somente depois das 4 verificações internas. Permite desligar a migração automática e excluir projetos dela.
- Centraliza configuração, diagnósticos e registros na pasta de dados do plugin. O comando `config` mostra o caminho e os valores efetivos.
- Distribui 2 plugins completos, em português e inglês, com manifesto nativo e programas que diferem somente em `LANGUAGE`.
- Remove programas, referências e manifestos antigos. Atualiza documentação, build reproduzível, nomes dos ZIPs e testes de empacotamento para Python 3.9 ou mais novo.
