PY ?= python3

.PHONY: help build-rules validate scan scan-secure showcase test backends clean

help:
	@echo "hello-spec — learn CodeGuard + Foundry by running them"
	@echo ""
	@echo "  make build-rules   author rules -> CodeGuard validate + convert to IDE bundles"
	@echo "  make scan          run the Foundry mini-engine on the vulnerable target (stub backend)"
	@echo "  make scan-secure   run the engine on the secure target (expect 0 true-positives)"
	@echo "  make showcase      serve the showcase at http://127.0.0.1:8000"
	@echo "  make backends      show how to switch LLM backends (stub / cli / api)"
	@echo "  make test          run the test suite (principles, evidence gate, idempotency)"
	@echo "  make clean         remove build artifacts"

build-rules:
	bash scripts/build_rules.sh

scan:
	$(PY) -m hello_spec.foundry.engine --config config/evaluation.yaml

scan-secure:
	$(PY) -m hello_spec.foundry.engine --config config/evaluation.yaml --target target/secure

showcase:
	$(PY) scripts/showcase_server.py

backends:
	@echo "stub (default, offline):   make scan"
	@echo "claude -p CLI:             FOUNDRY_LLM_BACKEND=cli make scan"
	@echo "Anthropic API:             FOUNDRY_LLM_BACKEND=api ANTHROPIC_API_KEY=... make scan"

test:
	$(PY) -m pytest -q

clean:
	rm -rf build .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
