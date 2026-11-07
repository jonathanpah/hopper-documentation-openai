# Como contribuir

A versão 2 segue o [SPEC.md](SPEC.md). Proponha correções reproduzíveis e descreva o comportamento esperado, o observado e os limites da verificação. Use dados sintéticos. Relate vulnerabilidades pelo [canal privado](SECURITY.md) e siga o [código de conduta](CODE_OF_CONDUCT.md).

## Preparação e verificação

Mantenha os pacotes em português e inglês completos. Preserve a identidade `hopper-documentation-openai` e os mesmos programas Python, exceto pela linha `LANGUAGE`. Cada pacote deve funcionar sem arquivos externos à sua pasta.

O programa e o build requerem Python 3.9 ou mais novo e somente a biblioteca padrão. Os testes locais usam Codex simulado, projetos temporários e dados sintéticos. Não precisam de autenticação, rede ou chamadas ao modelo.

1. Rode os testes do executor e os de aceite nos 2 idiomas. O Makefile seleciona os pacotes e define `TZ=UTC`.

   ```sh
   make test
   make test-acceptance
   ```

2. Repita com Python 3.9. Neste equipamento, quando disponível, selecione o interpretador do sistema.

   ```sh
   make test PYTHON=/usr/bin/python3
   make test-acceptance PYTHON=/usr/bin/python3
   ```

3. Gere os pacotes e confira os nomes, hashes e arquivos dos ZIPs.

   ```sh
   make build
   ```

4. Rode os casos do conferidor conforme os laços de `.github/workflows/verificar.yml`. Os casos `valida*` devem passar. Cada caso `invalida-F<n>*` deve reprovar somente na verificação indicada pelo nome. Por exemplo, o caso com roteiro usa o comando abaixo.

   ```sh
   python3 -B aceite/conferir.py aceite/casos/conferidor/valida-roteiro --idioma pt-br --roteiro aceite/roteiro.json
   ```

5. Confira links relativos dos documentos alterados, idiomas e diferenças entre pacotes. `make check` reúne build, testes do executor e testes de aceite no Python selecionado. `python3 -B scripts/build.py --out <diretorio>` permite escolher outra saída local.

T34 consulta os arquivos do índice do Git e os arquivos novos. Exclusões locais continuam no inventário até serem registradas no índice. Em uma tarefa que proíba escrita pelo Git, informe essa dependência ao executor e mantenha o teste intacto.

A verificação do GitHub roda em Ubuntu e macOS, com Python 3.9 e 3.13, nos 2 idiomas. A execução local complementa essa matriz. O aceite com Codex real, as avaliações de acionamento e as instalações seguem as unidades e autorizações do SPEC. Registre o modelo, o esforço, a versão do Codex, o acionamento e as evidências de cada prova real.

## Critérios congelados

`aceite/`, `SPEC.md` e `.github/workflows/verificar.yml` são critérios congelados. `aceite/MANIFESTO.sha256` registra seus hashes e a tag `criterios-v<versão>` da versão atual fixa a referência (hoje `criterios-v2.1.0`; `criterios-v2.0.0` guarda os critérios da versão 2.0). Uma mudança de critério ganha uma tag nova, porque envios forçados não são permitidos. `.github/workflows/integridade.yml` também é protegido. Preserve esses arquivos durante a implementação.

Uma alteração de critério exige a autorização e o procedimento C18 do SPEC. Uma falha do teste deve permanecer visível até a correção ou a revisão autorizada do critério. Os testes adicionais em `tests/` complementam o aceite.

## Correções e publicação

Uma correção deve partir de uma reprodução sintética que falhe antes da mudança. Preserve a cópia incremental, as origens, o isolamento das conversas, as travas e a retomada por diário. A migração só apaga origens depois das 4 verificações internas do Anexo E. Preserve o modelo e o esforço do redator e a revisão nativa dos hooks.

No relato, diferencie validação estrutural, acionamento por modelo real, execução de hooks e fidelidade do conteúdo. A ocultação por padrões e a validação de referências têm limites. Conversas reais, diagnósticos, credenciais e dados de contas ficam fora do repositório.

Releases usam tags explícitas e os nomes de ZIP previstos em R43. C29 exige gerar os arquivos a partir de um worktree da tag, publicar e conferir o download contra a origem. Publicar, instalar ou mudar critérios segue as autorizações do SPEC.

As contribuições usam a [licença MIT](LICENSE). O projeto não promete prazo de resposta ou aceitação.
