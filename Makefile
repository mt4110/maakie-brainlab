.PHONY: server-start server-stop server-status log ingest ask run-eval

PY=.venv/bin/python
PYENV=PYTHONPATH=.

server-start:
	bash ./infra/llama-server.start.sh

server-stop:
	bash ./infra/llama-server.stop.sh

server-status:
	bash ./infra/llama-server.status.sh

log:
	tail -n 200 -f logs/llama-server.log

ingest:
	bash scripts/ingest.sh

ask:
	$(PYENV) $(PY) src/ask.py "$(Q)"

run-eval:
	$(PYENV) $(PY) eval/run_eval.py

test:
	$(PYENV) $(PY) -m unittest discover -v -s tests -p "test_*.py"

ci: test
	$(PYENV) $(PY) -m compileall src eval

# S4 Satellite Pipeline (Placeholder)
sat-collect:
	$(PYENV) $(PY) src/satellite/collect.py $(SOURCE)

bootstrap:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e .

# S4 Satellite Pipeline (Placeholder)
sat-collect:
	$(PYENV) $(PY) src/satellite/collect.py $(SOURCE)

sat-normalize:
	@echo "[WARN] sat-normalize: Not implemented"
	@exit 0

sat-gate:
	@echo "[WARN] sat-gate: Not implemented"
	@exit 0

sat-store:
	@echo "[WARN] sat-store: Not implemented"
	@exit 0

sat-digest:
	@echo "[WARN] sat-digest: Not implemented"
	@exit 0

sat-index:
	@echo "[WARN] sat-index: Not implemented"
	@exit 0

sat-run: sat-collect sat-normalize sat-gate sat-store sat-digest sat-index
	@echo "[WARN] sat-run: Pipeline finish (not implemented real steps yet)"
	@exit 0
