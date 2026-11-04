PYTHON ?= python3

.PHONY: build test test-acceptance check
build:
	$(PYTHON) -B scripts/build.py

test:
	@set -e; for language in pt-br en; do \
		TZ=UTC HOPPER_DOCUMENTATION_OPENAI_PACOTE=hopper-documentation-openai-$$language \
		$(PYTHON) -B -m unittest discover -s tests -v; \
	done

test-acceptance:
	@set -e; for language in pt-br en; do \
		TZ=UTC HOPPER_DOCUMENTATION_OPENAI_PACOTE=hopper-documentation-openai-$$language \
		$(PYTHON) -B -m unittest discover -s aceite/testes -v; \
	done

check: build test test-acceptance
