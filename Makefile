# Shortcuts for macOS and Linux. Every task lives in tasks.py, which also runs on Windows:
# there, `py tasks.py setup` does what `make setup` does here. Run `make` to list the tasks.

PYTHON ?= python3
QUERY ?=
ARGS ?=

.DEFAULT_GOAL := help
.PHONY: help setup install env index check-key run offline app test docker clean

help setup install env index check-key app docker clean:
	@$(PYTHON) tasks.py $@

run offline:  # make run QUERY="..." ARGS="--out results/my_run"
	@$(PYTHON) tasks.py $@ $(if $(QUERY),"$(QUERY)") $(ARGS)

test:  # make test ARGS="-k mitigation"
	@$(PYTHON) tasks.py test $(ARGS)
