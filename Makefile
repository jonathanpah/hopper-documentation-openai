PYTHON ?= python3

.PHONY: build test check
build:
	$(PYTHON) scripts/build.py

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests -v

check: build test
