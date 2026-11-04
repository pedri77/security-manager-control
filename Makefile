# Contrato PLAYBOOK-F2P-001: el CI solo llama a estos targets.
# Sin e2e ni evals: SMC es una CLI sin LLM, y esos jobs se omiten solos.
.PHONY: lint test

lint:
	uv run smc validate

test:
	uv run --extra dev pytest -q
