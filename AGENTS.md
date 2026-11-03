# Project map

- `hopper-documentation-openai-pt-br/` and `hopper-documentation-openai-en/`:
  installable plugins; Python code is identical between languages.
- `scripts/build.py`: local validation and reproducible package generation.
- `tests/test_documentation.py`: synthetic regression tests using the standard library.
- `Makefile`: `make build`, `make test`, `make check`.
- `build/`: generated local packages and checksums, ignored by Git.
- `.agents/` and each package's `.codex-plugin/`: native marketplace and plugin manifests.
- `.github/`: contribution templates.

Private histories, diagnostics and real evaluations stay outside this repository.
