.PHONY: test ci bootstrap run-eval gate1 s5 s5-verify s6-verify check-doc-links verify-pack seed-eval evidence-pack-demo evidence-verify-demo evidence-gc smoke
.PHONY: sat-collect sat-normalize sat-gate sat-store sat-digest sat-index sat-run
.PHONY: server-start server-stop server-status log ingest ask
.PHONY: ai-smoke ai-verify
.PHONY: s22-16-ship phase-ship ops-now s25-baseline-freeze s25-obs-summary s25-regression-safety s25-acceptance-wall s25-ml-experiment s25-rag-tuning s25-langchain-poc s26-provider-canary s26-medium-eval-wall s26-rollback-artifact s26-orchestration-core s26-regression-safety s26-acceptance-wall s26-reliability-report s26-evidence-index s26-release-readiness s26-closeout s27-provider-canary-ops s27-medium-eval-wall-v2 s27-release-readiness-schedule s27-incident-triage-pack s27-policy-drift-guard s27-reliability-soak s27-acceptance-wall-v2 s27-evidence-trend-index s27-slo-readiness s27-closeout bench-il-compile tune-il-compile-prompt il-thread-smoke il-thread-replay-check verify-il-thread-v2

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
	$(PYENV) $(PY) ops/il_entrypoint_guard.py
	$(PYENV) $(PY) scripts/il_compile_entry_smoke.py
	$(PYENV) $(PY) scripts/il_thread_runner_v2_smoke.py
	$(MAKE) verify-il-thread-v2
	$(PYENV) $(PY) scripts/il_entry_smoke.py
	$(PYENV) $(PY) scripts/il_exec_selftest.py

il-thread-smoke:
	$(PYENV) $(PY) scripts/il_thread_runner_v2_smoke.py

il-thread-replay-check:
	$(PYENV) $(PY) scripts/il_thread_runner_v2_replay_check.py

verify-il-thread-v2:
	$(PYENV) $(PY) scripts/il_thread_runner_v2_suite.py

bench-il-compile:
	$(PYENV) $(PY) scripts/il_compile_bench.py

tune-il-compile-prompt:
	$(PYENV) $(PY) scripts/il_compile_prompt_loop.py

s22-16-ship:
	$(PYENV) $(PY) ops/s22_16_ship.py

phase-ship:
	DRY_RUN="$(DRY_RUN)" \
	SKIP_COMMIT="$(SKIP_COMMIT)" \
	SKIP_PR="$(SKIP_PR)" \
	WITH_REVIEWPACK="$(WITH_REVIEWPACK)" \
	BASE_BRANCH="$(BASE_BRANCH)" \
	COMMIT_MESSAGE="$(COMMIT_MESSAGE)" \
	INCLUDE_UNTRACKED="$(INCLUDE_UNTRACKED)" \
	$(PYENV) $(PY) ops/phase_ship.py --phase "$(PHASE)"

ops-now:
	$(PYENV) $(PY) scripts/ops/current_point.py

s25-baseline-freeze:
	$(PYENV) $(PY) scripts/ops/s25_baseline_freeze.py

s25-obs-summary:
	$(PYENV) $(PY) scripts/ops/s25_obs_pr_summary.py

s25-regression-safety:
	$(PYENV) $(PY) scripts/ops/s25_regression_safety.py

s25-acceptance-wall:
	$(PYENV) $(PY) scripts/ops/s25_acceptance_wall.py

s25-ml-experiment:
	$(PYENV) $(PY) scripts/ops/s25_ml_experiment.py

s25-rag-tuning:
	$(PYENV) $(PY) scripts/ops/s25_rag_tuning_loop.py

s25-langchain-poc:
	$(PYENV) $(PY) scripts/ops/s25_langchain_poc.py

s26-provider-canary:
	$(PYENV) $(PY) scripts/ops/s26_provider_canary.py

s26-medium-eval-wall:
	$(PYENV) $(PY) scripts/ops/s26_medium_eval_wall.py

s26-rollback-artifact:
	$(PYENV) $(PY) scripts/ops/s26_rollback_artifact.py

s26-orchestration-core:
	$(PYENV) $(PY) scripts/ops/s26_orchestration_core.py

s26-regression-safety:
	$(PYENV) $(PY) scripts/ops/s26_regression_safety.py

s26-acceptance-wall:
	$(PYENV) $(PY) scripts/ops/s26_acceptance_wall.py

s26-reliability-report:
	$(PYENV) $(PY) scripts/ops/s26_reliability_report.py

s26-evidence-index:
	$(PYENV) $(PY) scripts/ops/s26_evidence_index.py

s26-release-readiness:
	$(PYENV) $(PY) scripts/ops/s26_release_readiness.py

s26-closeout:
	$(PYENV) $(PY) scripts/ops/s26_closeout.py

s27-provider-canary-ops:
	$(PYENV) $(PY) scripts/ops/s27_provider_canary_ops.py

s27-medium-eval-wall-v2:
	$(PYENV) $(PY) scripts/ops/s27_medium_eval_wall_v2.py

s27-release-readiness-schedule:
	$(PYENV) $(PY) scripts/ops/s27_release_readiness_schedule.py

s27-incident-triage-pack:
	$(PYENV) $(PY) scripts/ops/s27_incident_triage_pack.py

s27-policy-drift-guard:
	$(PYENV) $(PY) scripts/ops/s27_policy_drift_guard.py

s27-reliability-soak:
	$(PYENV) $(PY) scripts/ops/s27_reliability_soak.py

s27-acceptance-wall-v2:
	$(PYENV) $(PY) scripts/ops/s27_acceptance_wall_v2.py

s27-evidence-trend-index:
	$(PYENV) $(PY) scripts/ops/s27_evidence_trend_index.py

s27-slo-readiness:
	$(PYENV) $(PY) scripts/ops/s27_slo_readiness.py

s27-closeout:
	$(PYENV) $(PY) scripts/ops/s27_closeout.py

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
