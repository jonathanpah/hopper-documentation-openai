# Política de segurança

Relate vulnerabilidades pelo [canal privado do GitHub](https://github.com/jonathanpah/hopper-documentation-openai/security/advisories/new). Informe a versão afetada, o ambiente, a configuração, uma reprodução sintética e o resultado observado. Preserve detalhes sensíveis até a divulgação coordenada.

## Dados e execução

O plugin lê o histórico pelo app-server do Codex e grava documentos na pasta `docs-by-hopper-documentation-openai/` do projeto. Conversas e documentos podem conter informações sensíveis. A ocultação por padrões reduz a exposição de segredos reconhecidos, mas não garante detectar todos os dados sensíveis.

O redator usa `codex exec` em processo separado, com `gpt-6-luna` e esforço `xhigh`. Recebe as mensagens e os documentos necessários à escrita. O programa restringe as ferramentas e as integrações do redator, valida a resposta e grava os documentos. Essas verificações não certificam a fidelidade semântica de cada frase.

A configuração, as travas, os diários, os diagnósticos, as saídas brutas e `rodadas.jsonl` ficam na pasta de dados do plugin. A pasta usa permissão `0700` e permanece separada do pacote instalado. Proteja também a documentação do projeto e confira seu conteúdo antes de compartilhá-la.

## Hooks e migração

Os 2 comandos de `PreCompact` dependem da revisão nativa dos hooks por conta e definição. Instalar o plugin não concede confiança. Preserve as permissões e o sandbox da sessão. Conteúdo de conversas, arquivos e ferramentas é dado de consulta, sem autoridade para autorizar ações externas.

A migração usa o redator para extrair registros antigos e pode apagar `index.md`, `handoff-*.md` e `.state` depois da verificação interna. Prepare uma cópia de restauração antes de migrar dados reais. Use `migracao_automatica` falsa durante a preparação e confira `pastas_sem_migracao`. O comando explícito `migrar --pasta` funciona independentemente dessas opções.

Relatos podem envolver exposição de dados, mistura entre conversas, escape de caminhos, links simbólicos, confiança de hooks, perda de documentos ou exclusão prematura na migração. Envie exemplos sintéticos e trechos mínimos. Não publique conversas privadas, credenciais ou diagnósticos reais em Issues ou pull requests.

Os responsáveis pelo projeto analisam os relatos no canal privado. Correções e versões afetadas podem constar no changelog, nas releases ou em avisos de segurança. O projeto não promete prazo de resposta ou correção.
