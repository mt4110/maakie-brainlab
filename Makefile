.PHONY: test ci bootstrap run-eval gate1 s5 s5-verify s6-verify check-doc-links verify-pack seed-eval evidence-pack-demo evidence-verify-demo evidence-gc smoke
.PHONY: sat-collect sat-normalize sat-gate sat-store sat-digest sat-index sat-run
.PHONY: server-start server-stop server-status log ingest ask
.PHONY: ai-smoke ai-verify

PY=.venv/bin/python
PYENV=PYTHONPATH=./src:.

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
	@echo "+ go test -v -count=1 ./..."
	go test -v -count=1 ./...
	$(PYENV) $(PY) -m unittest discover -v -s tests -p "test_*.py"
	@echo "RUN: verify-il (always-on)"
	$(MAKE) verify-il

ci-test:
	@echo "+ go test -count=1 -mod=readonly ./... (Strict CI mode)"
	go test -count=1 -mod=readonly ./...
	$(PYENV) $(PY) -m unittest discover -v -s tests -p "test_*.py"

ci: ci-test
	$(PYENV) $(PY) -m compileall src eval
	@echo "+ make verify-il"
	$(MAKE) verify-il

verify-il:
	$(PYENV) $(PY) scripts/il_check.py

bootstrap:
	# S20-08: Canonical bootstrap via uv (using system python only to install uv)
	python3 -m pip install uv
	python3 -m uv sync

py-env-report: bootstrap
	$(PYENV) $(PY) scripts/py_env_report.py

# S4 Satellite Pipeline
sat-collect:
	@echo "Not implemented yet (placeholder)."

sat-normalize:
	@echo "Not implemented yet (placeholder)."

sat-manifest:
	@echo "Not implemented yet (placeholder)."

sat-gate:
	@echo "Not implemented yet (placeholder)."

sat-store:
	@echo "Not implemented yet (placeholder)."

sat-run:
	@echo "Not implemented yet (placeholder)."

gate1:
	bash ops/gate1.sh

# S5-02 Review Pack
s5:
	bash ops/s5_pack.sh


s5-verify:
	bash ops/s5_verify_pack.sh "$(PACK)"

# S6 v1 Verify (Git-Free)
s6-verify:
	bash ops/s6_verify_pack.sh "$(PACK)"


check-doc-links:
	@bash ops/check_no_file_url.sh


# C10 Unified Verification
verify-pack:
	bash ops/verify_pack.sh "$(PACK)"

# S7 / Local Eval Seed
seed-eval:
	bash ops/seed_eval_results.sh


# S6 Evidence Pipeline (v1)
evidence-pack-demo:
	go run ./cmd/evidencepack pack --kind demo --store .local/evidence_store cmd/evidencepack/main.go

evidence-verify-demo:
	@echo "Verifying latest demo pack..."
	@LATEST=$$(ls -t .local/evidence_store/packs/demo/*.tar.gz | head -n1); \
	go run ./cmd/evidencepack verify --pack "$$LATEST"

evidence-gc:
	go run ./cmd/evidencepack gc --store .local/evidence_store

smoke:
	bash ops/smoke_evidencepack.sh

ai-smoke:
	$(PYENV) $(PY) eval/run_eval.py --mode record --provider mock

ai-verify:
	$(PYENV) $(PY) eval/run_eval.py --mode verify-only --provider mock
