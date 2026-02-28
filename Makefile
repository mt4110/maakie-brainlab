.PHONY: test ci bootstrap run-eval gate1 s5 s5-verify s6-verify check-doc-links verify-pack seed-eval evidence-pack-demo evidence-verify-demo evidence-gc smoke
.PHONY: sat-collect sat-normalize sat-manifest sat-verify sat-gate sat-store sat-digest sat-index sat-run
.PHONY: server-start server-stop server-status log ingest ask
.PHONY: ai-smoke ai-verify
.PHONY: s22-16-ship phase-ship ops-now s25-baseline-freeze s25-obs-summary s25-regression-safety s25-acceptance-wall s25-ml-experiment s25-rag-tuning s25-langchain-poc s26-provider-canary s26-medium-eval-wall s26-rollback-artifact s26-orchestration-core s26-regression-safety s26-acceptance-wall s26-reliability-report s26-evidence-index s26-release-readiness s26-closeout s27-provider-canary-ops s27-medium-eval-wall-v2 s27-release-readiness-schedule s27-incident-triage-pack s27-policy-drift-guard s27-reliability-soak s27-acceptance-wall-v2 s27-evidence-trend-index s27-slo-readiness s27-closeout s28-provider-canary-recovery s28-taxonomy-feedback-loop s28-readiness-notify s28-incident-triage-pack-v2 s28-policy-drift-guard-v2 s28-reliability-soak-v2 s28-acceptance-wall-v3 s28-evidence-trend-index-v3 s28-slo-readiness-v2 s28-closeout s29-canary-recovery-success-rate-slo s29-taxonomy-pipeline-integration s29-readiness-notify-multichannel s29-incident-triage-pack-v3 s29-policy-drift-guard-v3 s29-reliability-soak-v3 s29-acceptance-wall-v4 s29-evidence-trend-index-v4 s29-slo-readiness-v3 s29-closeout s30-task-reclassify s30-task-reclassify-apply s30-task-reclassify-apply-all s30-quality-burndown bench-il-compile tune-il-compile-prompt il-thread-smoke il-thread-replay-check verify-il-thread-v2 il-init-workspace il-fmt-check il-fmt-write il-lint il-doctor ilctl il-thread-merge bench-il-compile-diff s31-acceptance-wall-v5 s31-regression-safety-v2 s31-reliability-soak-v2 s31-policy-drift-guard s31-evidence-trend-index-v6 s31-closeout s31-handoff-pack s32-retrieval-eval-wall s32-operator-dashboard s32-latency-slo-guard s32-acceptance-wall-v6 s32-policy-drift-guard-v2 s32-reliability-soak-v3 s32-evidence-trend-index-v7 s32-opcode-catalog

PY=.venv/bin/python
PYENV=PYTHONPATH=./src:.
SAT_DATE=$(if $(DATE),$(DATE),$(shell date -u +%F))

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

il-init-workspace:
	@test -n "$(OUT)" || (echo "ERROR: OUT is required. usage: make il-init-workspace OUT=<dir> [FORCE=1]" && exit 2)
	@if [ "$(FORCE)" = "1" ]; then \
		if [ -n "$(TEMPLATE)" ]; then \
			$(PYENV) $(PY) scripts/il_workspace_init.py --out "$(OUT)" --template "$(TEMPLATE)" --force; \
		else \
			$(PYENV) $(PY) scripts/il_workspace_init.py --out "$(OUT)" --force; \
		fi; \
	else \
		if [ -n "$(TEMPLATE)" ]; then \
			$(PYENV) $(PY) scripts/il_workspace_init.py --out "$(OUT)" --template "$(TEMPLATE)"; \
		else \
			$(PYENV) $(PY) scripts/il_workspace_init.py --out "$(OUT)"; \
		fi; \
	fi

il-fmt-check:
	@test -n "$(FILES)" || (echo "ERROR: FILES is required. usage: make il-fmt-check FILES='<paths or globs>'" && exit 2)
	$(PYENV) $(PY) scripts/il_fmt.py --check $(FILES)

il-fmt-write:
	@test -n "$(FILES)" || (echo "ERROR: FILES is required. usage: make il-fmt-write FILES='<paths or globs>'" && exit 2)
	$(PYENV) $(PY) scripts/il_fmt.py --write $(FILES)

il-lint:
	@test -n "$(IL)" || (echo "ERROR: IL is required. usage: make il-lint IL=<il.json> [OUT=<report.json>]" && exit 2)
	@if [ -n "$(OUT)" ]; then \
		$(PYENV) $(PY) scripts/il_lint.py --il "$(IL)" --out "$(OUT)"; \
	else \
		$(PYENV) $(PY) scripts/il_lint.py --il "$(IL)"; \
	fi

il-doctor:
	@if [ -n "$(OUT)" ]; then \
		$(PYENV) $(PY) scripts/il_doctor.py --out "$(OUT)"; \
	else \
		$(PYENV) $(PY) scripts/il_doctor.py; \
	fi

ilctl:
	@test -n "$(CMD)" || (echo "ERROR: CMD is required. usage: make ilctl CMD='<subcommand args...>'" && exit 2)
	$(PYENV) $(PY) scripts/ilctl.py $(CMD)

il-thread-merge:
	@test -n "$(INPUTS)" || (echo "ERROR: INPUTS is required. usage: make il-thread-merge INPUTS='<dir1> <dir2>' OUT=<out_dir>" && exit 2)
	@test -n "$(OUT)" || (echo "ERROR: OUT is required. usage: make il-thread-merge INPUTS='<dir1> <dir2>' OUT=<out_dir>" && exit 2)
	$(PYENV) $(PY) scripts/il_thread_runner_v2_merge.py --inputs $(INPUTS) --out "$(OUT)"

bench-il-compile-diff:
	@test -n "$(BASELINE)" || (echo "ERROR: BASELINE is required. usage: make bench-il-compile-diff BASELINE=<file> CANDIDATE=<file> [OUT=<file>]" && exit 2)
	@test -n "$(CANDIDATE)" || (echo "ERROR: CANDIDATE is required. usage: make bench-il-compile-diff BASELINE=<file> CANDIDATE=<file> [OUT=<file>]" && exit 2)
	@if [ -n "$(OUT)" ]; then \
		$(PYENV) $(PY) scripts/il_compile_bench_diff.py --baseline "$(BASELINE)" --candidate "$(CANDIDATE)" --out "$(OUT)"; \
	else \
		$(PYENV) $(PY) scripts/il_compile_bench_diff.py --baseline "$(BASELINE)" --candidate "$(CANDIDATE)"; \
	fi

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

s28-provider-canary-recovery:
	$(PYENV) $(PY) scripts/ops/s28_provider_canary_recovery.py

s28-taxonomy-feedback-loop:
	$(PYENV) $(PY) scripts/ops/s28_taxonomy_feedback_loop.py

s28-readiness-notify:
	$(PYENV) $(PY) scripts/ops/s28_readiness_notify.py

s28-incident-triage-pack-v2:
	$(PYENV) $(PY) scripts/ops/s28_incident_triage_pack_v2.py

s28-policy-drift-guard-v2:
	$(PYENV) $(PY) scripts/ops/s28_policy_drift_guard_v2.py

s28-reliability-soak-v2:
	$(PYENV) $(PY) scripts/ops/s28_reliability_soak_v2.py

s28-acceptance-wall-v3:
	$(PYENV) $(PY) scripts/ops/s28_acceptance_wall_v3.py

s28-evidence-trend-index-v3:
	$(PYENV) $(PY) scripts/ops/s28_evidence_trend_index_v3.py

s28-slo-readiness-v2:
	$(PYENV) $(PY) scripts/ops/s28_slo_readiness_v2.py

s28-closeout:
	$(PYENV) $(PY) scripts/ops/s28_closeout.py

s29-canary-recovery-success-rate-slo:
	$(PYENV) $(PY) scripts/ops/s29_canary_recovery_success_rate_slo.py

s29-taxonomy-pipeline-integration:
	$(PYENV) $(PY) scripts/ops/s29_taxonomy_pipeline_integration.py

s29-readiness-notify-multichannel:
	$(PYENV) $(PY) scripts/ops/s29_readiness_notify_multichannel.py --send

s29-incident-triage-pack-v3:
	$(PYENV) $(PY) scripts/ops/s29_incident_triage_pack_v3.py

s29-policy-drift-guard-v3:
	$(PYENV) $(PY) scripts/ops/s29_policy_drift_guard_v3.py

s29-reliability-soak-v3:
	$(PYENV) $(PY) scripts/ops/s29_reliability_soak_v3.py

s29-acceptance-wall-v4:
	$(PYENV) $(PY) scripts/ops/s29_acceptance_wall_v4.py

s29-evidence-trend-index-v4:
	$(PYENV) $(PY) scripts/ops/s29_evidence_trend_index_v4.py

s29-slo-readiness-v3:
	$(PYENV) $(PY) scripts/ops/s29_slo_readiness_v3.py

s29-closeout:
	$(PYENV) $(PY) scripts/ops/s29_closeout.py

s30-task-reclassify:
	$(PYENV) $(PY) scripts/ops/s30_task_reclassify.py

s30-task-reclassify-apply:
	$(PYENV) $(PY) scripts/ops/s30_task_reclassify.py --apply-batch

s30-task-reclassify-apply-all:
	$(PYENV) $(PY) scripts/ops/s30_task_reclassify.py --apply-all

s30-quality-burndown:
	$(PYENV) $(PY) scripts/ops/s30_quality_burndown.py

s31-acceptance-wall-v5:
	$(PYENV) $(PY) scripts/ops/s31_acceptance_wall_v5.py

s31-regression-safety-v2:
	$(PYENV) $(PY) scripts/ops/s31_regression_safety_v2.py

s31-reliability-soak-v2:
	$(PYENV) $(PY) scripts/ops/s31_reliability_soak_v2.py

s31-policy-drift-guard:
	$(PYENV) $(PY) scripts/ops/s31_policy_drift_guard.py

s31-evidence-trend-index-v6:
	$(PYENV) $(PY) scripts/ops/s31_evidence_trend_index_v6.py

s31-closeout:
	$(PYENV) $(PY) scripts/ops/s31_closeout.py

s31-handoff-pack:
	$(PYENV) $(PY) scripts/ops/s31_handoff_pack.py

s32-retrieval-eval-wall:
	$(PYENV) $(PY) scripts/ops/s32_retrieval_eval_wall.py

s32-operator-dashboard:
	@test -n "$(RUN_DIR)" || (echo "ERROR: RUN_DIR is required. usage: make s32-operator-dashboard RUN_DIR=<runner_out_dir>" && exit 2)
	$(PYENV) $(PY) scripts/ops/s32_operator_dashboard_export.py --run-dir "$(RUN_DIR)"

s32-latency-slo-guard:
	@test -n "$(RUN_DIR)" || (echo "ERROR: RUN_DIR is required. usage: make s32-latency-slo-guard RUN_DIR=<runner_out_dir>" && exit 2)
	$(PYENV) $(PY) scripts/ops/s32_latency_slo_guard.py --run-dir "$(RUN_DIR)"

s32-acceptance-wall-v6:
	$(PYENV) $(PY) scripts/ops/s32_acceptance_wall_v6.py

s32-policy-drift-guard-v2:
	$(PYENV) $(PY) scripts/ops/s32_policy_drift_guard_v2.py

s32-reliability-soak-v3:
	$(PYENV) $(PY) scripts/ops/s32_reliability_soak_v3.py

s32-evidence-trend-index-v7:
	$(PYENV) $(PY) scripts/ops/s32_evidence_trend_index_v7.py

s32-opcode-catalog:
	$(PYENV) $(PY) scripts/ops/s32_opcode_catalog_generator.py

bootstrap:
	# S20-08: Canonical bootstrap via uv (using system python only to install uv)
	python3 -m pip install uv
	python3 -m uv sync

py-env-report: bootstrap
	$(PYENV) $(PY) scripts/py_env_report.py

# S4 Satellite Pipeline
sat-collect:
	@test -n "$(SOURCE)" || (echo "ERROR: SOURCE is required. usage: make sat-collect SOURCE=<source_id> [DATE=YYYY-MM-DD]" && exit 2)
	$(PYENV) $(PY) -m satellite.collect "$(SOURCE)" --date "$(SAT_DATE)"

sat-normalize:
	@test -n "$(SOURCE)" || (echo "ERROR: SOURCE is required. usage: make sat-normalize SOURCE=<source_id> [DATE=YYYY-MM-DD]" && exit 2)
	$(PYENV) $(PY) -m satellite.normalize "$(SOURCE)" --date "$(SAT_DATE)"

sat-verify-manifest:
	@test -n "$(SOURCE)" || (echo "ERROR: SOURCE is required. usage: make sat-verify-manifest SOURCE=<source_id> [DATE=YYYY-MM-DD]" && exit 2)
	$(PYENV) $(PY) -m satellite.manifest_verify "$(SOURCE)" --date "$(SAT_DATE)"

sat-manifest: sat-verify-manifest

sat-verify: sat-verify-manifest

sat-gate:
	@test -n "$(SOURCE)" || (echo "ERROR: SOURCE is required. usage: make sat-gate SOURCE=<source_id> [DATE=YYYY-MM-DD]" && exit 2)
	$(PYENV) $(PY) -m satellite.gate "$(SOURCE)" --date "$(SAT_DATE)"

sat-store:
	@test -n "$(SOURCE)" || (echo "ERROR: SOURCE is required. usage: make sat-store SOURCE=<source_id> [DATE=YYYY-MM-DD]" && exit 2)
	$(PYENV) $(PY) -m satellite.store "$(SOURCE)" --date "$(SAT_DATE)"

sat-digest:
	@test -n "$(SOURCE)" || (echo "ERROR: SOURCE is required. usage: make sat-digest SOURCE=<source_id> [DATE=YYYY-MM-DD]" && exit 2)
	$(PYENV) $(PY) -m satellite.digest "$(SOURCE)" --date "$(SAT_DATE)"

sat-index:
	@test -n "$(SOURCE)" || (echo "ERROR: SOURCE is required. usage: make sat-index SOURCE=<source_id> [DATE=YYYY-MM-DD]" && exit 2)
	$(PYENV) $(PY) -m satellite.index "$(SOURCE)" --date "$(SAT_DATE)"

sat-run:
	@test -n "$(SOURCE)" || (echo "ERROR: SOURCE is required. usage: make sat-run SOURCE=<source_id> [DATE=YYYY-MM-DD]" && exit 2)
	$(PYENV) $(PY) -m satellite.run "$(SOURCE)" --date "$(SAT_DATE)"

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
