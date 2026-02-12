.PHONY: test ci bootstrap run-eval gate1 s5 s5-verify s6-verify check-doc-links verify-pack seed-eval evidence-pack-demo evidence-verify-demo evidence-gc smoke
.PHONY: sat-collect sat-normalize sat-gate sat-store sat-digest sat-index sat-run
.PHONY: server-start server-stop server-status log ingest ask

PY?=.venv/bin/python
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
	@echo "+ go test ./..."
	go test ./...
	$(PYENV) $(PY) -m unittest discover -v -s tests -p "test_*.py"

ci-test:
	@echo "+ go test -count=1 -mod=readonly ./... (Strict CI mode)"
	go test -count=1 -mod=readonly ./...
	$(PYENV) $(PY) -m unittest discover -v -s tests -p "test_*.py"

ci: ci-test
	$(PYENV) $(PY) -m compileall src eval

bootstrap:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e .

# S4 Satellite Pipeline
sat-collect:
	$(PYENV) $(PY) src/satellite/collect.py $(SOURCE)

sat-normalize:
	$(PYENV) $(PY) src/satellite/normalize.py $(SOURCE)

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


