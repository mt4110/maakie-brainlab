.PHONY: server-start server-stop server-status log ingest ask run-eval

PY=python3
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
	$(PYENV) $(PY) src/build_index.py --raw-dir data/raw --index-dir index

ask:
	$(PYENV) $(PY) src/ask.py "$(Q)"

run-eval:
	$(PYENV) $(PY) eval/run_eval.py
