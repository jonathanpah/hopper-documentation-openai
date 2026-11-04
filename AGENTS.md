# Mapa do projeto

- `hopper-documentation-openai-pt-br/` e `hopper-documentation-openai-en/` contêm os plugins completos. Os programas Python diferem somente na linha `LANGUAGE`.
- Cada pacote contém `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`, `hooks/hooks.json` e `skills/hopper-documentation-openai/`.
- A skill contém `SKILL.md`, licença, `agents/openai.yaml`, regras de escrita, modelos e `scripts/hopper_documentation_openai.py`.
- `.agents/plugins/marketplace.json` na raiz seleciona o pacote em português.
- `scripts/build.py` valida e gera ZIPs reproduzíveis e `SHA256SUMS`. `build/` guarda saídas locais ignoradas pelo Git.
- `tests/test_documentation.py` verifica o empacotamento. Os outros `tests/test_documentation*_v2.py` cobrem o programa da versão 2 com dados sintéticos.
- `Makefile` oferece `make build`, `make test`, `make test-acceptance` e `make check`, com seleção de interpretador por `PYTHON`.
- `SPEC.md` define os requisitos e o inventário. `aceite/` contém os testes congelados, o conferidor, os casos, as avaliações, o roteiro e o manifesto de integridade.
- `.github/` contém modelos de contribuição e verificações. Preserve os critérios congelados e os workflows protegidos.
- `README.md` apresenta uso e instalação; `index.md` reúne a documentação técnica.

O programa e o build usam Python 3.9 ou mais novo e somente a biblioteca padrão. Históricos privados, diagnósticos e avaliações reais ficam fora do repositório.
