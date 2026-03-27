import { promises as fs } from 'node:fs';
import path from 'node:path';

import {
	REPO_ROOT,
	asIsoDate,
	asNumber,
	asString,
	formatNumber,
	formatPercent,
	getByPath,
	normalizeStatus,
	readJsonObject,
	repoJoin,
	summarizeReasons,
	toRepoRelative,
	walkFiles
} from './fs';
import type {
	DashboardStatus,
	EvidenceHistoryItem,
	MetricCell,
	OverviewPayload,
	PipelineKey,
	PipelineSnapshot,
	PromptTraceItem
} from './types';

interface ArtifactSpec {
	key: PipelineKey;
	title: string;
	artifactPath: string;
	schemaPath: string;
	statusPath: string;
	summaryPath: string;
	capturedAtPath: string;
	metrics: (payload: Record<string, unknown>) => MetricCell[];
}

const ARTIFACTS: ArtifactSpec[] = [
	{
		key: 'rag',
		title: 'RAG Tuning',
		artifactPath: 'docs/evidence/s25-08/rag_tuning_latest.json',
		schemaPath: 'schema_version',
		statusPath: 'summary.status',
		summaryPath: 'summary.errors',
		capturedAtPath: 'captured_at_utc',
		metrics: (payload) => [
			{
				label: 'Baseline Hit',
				value: formatPercent(
					asNumber(getByPath(payload, 'profiles.baseline.metrics.hit_rate'))
				)
			},
			{
				label: 'Candidate Hit',
				value: formatPercent(
					asNumber(getByPath(payload, 'profiles.candidate.metrics.hit_rate'))
				)
			},
			{
				label: 'Latency Delta (ms)',
				value: formatNumber(asNumber(getByPath(payload, 'comparison.delta_latency_ms')), 3)
			}
		]
	},
	{
		key: 'langchain',
		title: 'LangChain PoC',
		artifactPath: 'docs/evidence/s25-09/langchain_poc_latest.json',
		schemaPath: 'schema_version',
		statusPath: 'summary.status',
		summaryPath: 'summary.warnings',
		capturedAtPath: 'captured_at_utc',
		metrics: (payload) => [
			{
				label: 'Retrieved Rows',
				value: asString(getByPath(payload, 'retrieval.rows')) || '0'
			},
			{
				label: 'PoC Backend',
				value: asString(getByPath(payload, 'smoke.poc.backend')) || 'NA'
			},
			{
				label: 'Expected Source Match',
				value: asString(getByPath(payload, 'smoke.poc.matched_expected_source')) || 'NA'
			}
		]
	},
	{
		key: 'ml',
		title: 'ML Benchmark',
		artifactPath: 'docs/evidence/s25-07/ml_experiment_latest.json',
		schemaPath: 'schema_version',
		statusPath: 'summary.status',
		summaryPath: 'summary.errors',
		capturedAtPath: 'captured_at_utc',
		metrics: (payload) => [
			{
				label: 'Objective Score',
				value: formatNumber(
					asNumber(getByPath(payload, 'bench_summary.objective_score')),
					3
				)
			},
			{
				label: 'Reproducible Rate',
				value: formatPercent(
					asNumber(getByPath(payload, 'bench_summary.reproducible_rate'))
				)
			},
			{
				label: 'IL Validity Rate',
				value: formatPercent(asNumber(getByPath(payload, 'bench_summary.il_validity_rate')))
			}
		]
	},
	{
		key: 'quality',
		title: 'Quality Burndown',
		artifactPath: 'docs/evidence/s30-02/quality_burndown_latest.json',
		schemaPath: 'schema_version',
		statusPath: 'summary.status',
		summaryPath: 'summary.status',
		capturedAtPath: 'captured_at_utc',
		metrics: (payload) => [
			{
				label: 'Done Checks',
				value: asString(getByPath(payload, 'summary.done_checks')) || '0'
			},
			{
				label: 'Remaining Checks',
				value: asString(getByPath(payload, 'summary.remaining_checks')) || '0'
			},
			{
				label: 'Risk Remaining',
				value: asString(getByPath(payload, 'summary.risk_remaining')) || '0'
			}
		]
	},
	{
		key: 'operator',
		title: 'Operator Dashboard',
		artifactPath: 'docs/evidence/s32-15/operator_dashboard_latest.json',
		schemaPath: 'schema',
		statusPath: 'status',
		summaryPath: 'reasons',
		capturedAtPath: 'captured_at_utc',
		metrics: (payload) => [
			{
				label: 'Success Rate',
				value: formatPercent(asNumber(getByPath(payload, 'metrics.success_rate')))
			},
			{
				label: 'Retry Rate',
				value: formatPercent(asNumber(getByPath(payload, 'metrics.retry_rate')))
			},
			{
				label: 'P95 Latency (ms)',
				value: formatNumber(asNumber(getByPath(payload, 'metrics.p95_latency_ms')), 2)
			},
			{
				label: 'Throughput (case/s)',
				value: formatNumber(
					asNumber(getByPath(payload, 'metrics.throughput_cases_per_sec')),
					2
				)
			}
		]
	}
];

function sortByDateDesc<T>(items: T[], picker: (item: T) => string | null): T[] {
	return [...items].sort((a, b) => {
		const da = picker(a);
		const db = picker(b);
		const ta = da ? new Date(da).getTime() : 0;
		const tb = db ? new Date(db).getTime() : 0;
		return tb - ta;
	});
}

function statusFromPayload(payload: Record<string, unknown>, statusPath: string): DashboardStatus {
	const status = normalizeStatus(getByPath(payload, statusPath));
	return status;
}

function summaryFromPayload(payload: Record<string, unknown>, spec: ArtifactSpec): string {
	const value = getByPath(payload, spec.summaryPath);
	if (Array.isArray(value)) {
		const summary = summarizeReasons(value);
		return summary || 'No warnings';
	}
	const text = asString(value).trim();
	if (text) {
		return text;
	}
	const fallback = summarizeReasons(getByPath(payload, 'reasons'));
	return fallback || 'No details';
}

async function readArtifact(spec: ArtifactSpec): Promise<PipelineSnapshot> {
	const absPath = repoJoin(spec.artifactPath);
	const payload = await readJsonObject(absPath);
	if (!payload) {
		return {
			key: spec.key,
			title: spec.title,
			artifactPath: spec.artifactPath,
			schema: 'MISSING',
			status: 'MISSING',
			capturedAt: null,
			summary: 'Artifact not found yet. Run pipeline to generate evidence.',
			metrics: spec.metrics({})
		};
	}

	return {
		key: spec.key,
		title: spec.title,
		artifactPath: spec.artifactPath,
		schema: asString(getByPath(payload, spec.schemaPath)) || 'UNKNOWN',
		status: statusFromPayload(payload, spec.statusPath),
		capturedAt: asIsoDate(getByPath(payload, spec.capturedAtPath)),
		summary: summaryFromPayload(payload, spec),
		metrics: spec.metrics(payload)
	};
}

export async function getOverviewPayload(): Promise<OverviewPayload> {
	const pipelines = await Promise.all(ARTIFACTS.map((spec) => readArtifact(spec)));
	const health = {
		pass: pipelines.filter((row) => row.status === 'PASS').length,
		warn: pipelines.filter((row) => row.status === 'WARN').length,
		fail: pipelines.filter((row) => row.status === 'FAIL').length,
		missing: pipelines.filter((row) => row.status === 'MISSING').length
	};

	return {
		generatedAt: new Date().toISOString(),
		repoRoot: REPO_ROOT,
		health,
		pipelines: sortByDateDesc(pipelines, (row) => row.capturedAt)
	};
}

function compactSummary(payload: Record<string, unknown>): string {
	const summaryStatus = asString(getByPath(payload, 'summary.status'));
	if (summaryStatus) {
		const errors = getByPath(payload, 'summary.errors');
		if (Array.isArray(errors) && errors.length > 0) {
			return `${summaryStatus}: ${summarizeReasons(errors)}`;
		}
		return summaryStatus;
	}
	const reasons = summarizeReasons(getByPath(payload, 'reasons'));
	if (reasons) {
		return reasons;
	}
	const status = asString(getByPath(payload, 'status'));
	return status || 'No summary';
}

function statusFromHistoryPayload(payload: Record<string, unknown>): DashboardStatus {
	if (getByPath(payload, 'summary.status') !== undefined) {
		return normalizeStatus(getByPath(payload, 'summary.status'));
	}
	if (getByPath(payload, 'status') !== undefined) {
		return normalizeStatus(getByPath(payload, 'status'));
	}
	return 'UNKNOWN';
}

export async function getEvidenceHistory(limit = 200): Promise<EvidenceHistoryItem[]> {
	const evidenceRoot = repoJoin('docs/evidence');
	const jsonPaths = await walkFiles(evidenceRoot, {
		maxDepth: 6,
		maxResults: 2000,
		match: (absPath) => {
			if (absPath.endsWith('_latest.json')) {
				return true;
			}
			const rel = toRepoRelative(absPath);
			return (
				rel.startsWith('docs/evidence/dashboard/consensus_contract/') &&
				rel.endsWith('.json')
			);
		}
	});

	const rows: EvidenceHistoryItem[] = [];
	for (const absPath of jsonPaths) {
		const payload = await readJsonObject(absPath);
		if (!payload) {
			continue;
		}
		const stat = await fs.stat(absPath);
		rows.push({
			id: toRepoRelative(absPath),
			artifactPath: toRepoRelative(absPath),
			schema:
				asString(getByPath(payload, 'schema_version')) ||
				asString(getByPath(payload, 'schema')) ||
				'UNKNOWN',
			status: statusFromHistoryPayload(payload),
			capturedAt: asIsoDate(getByPath(payload, 'captured_at_utc')),
			modifiedAt: stat.mtime.toISOString(),
			summary: compactSummary(payload)
		});
	}

	const sorted = rows.sort((a, b) => {
		const ta = new Date(a.capturedAt || a.modifiedAt).getTime();
		const tb = new Date(b.capturedAt || b.modifiedAt).getTime();
		return tb - ta;
	});
	return sorted.slice(0, Math.max(1, limit));
}

export async function getEvidenceArtifactByPath(
	artifactPath: string
): Promise<Record<string, unknown> | null> {
	const normalized = artifactPath.trim().replaceAll('\\', '/').replace(/^\/+/, '');
	if (!normalized.startsWith('docs/evidence/')) {
		return null;
	}

	const evidenceRoot = repoJoin('docs/evidence');
	const abs = path.resolve(REPO_ROOT, normalized);
	const relative = path.relative(evidenceRoot, abs);
	if (relative.startsWith('..') || path.isAbsolute(relative)) {
		return null;
	}
	return await readJsonObject(abs);
}

function snippet(text: string, max = 520): string {
	const clean = text.replace(/\s+/g, ' ').trim();
	if (clean.length <= max) {
		return clean;
	}
	return `${clean.slice(0, max)}...`;
}

function requestFromPrompt(prompt: string): string {
	const matched = prompt.match(/^REQUEST_TEXT:\s*(.*)$/m);
	if (matched && matched[1]) {
		return matched[1].trim();
	}
	return '';
}

export async function getPromptTrace(limit = 40): Promise<PromptTraceItem[]> {
	const roots = [repoJoin('.local/obs'), repoJoin('docs/evidence')];
	const gathered: string[] = [];

	for (const root of roots) {
		const files = await walkFiles(root, {
			maxDepth: 10,
			maxResults: 1000,
			match: (absPath) => absPath.endsWith('il.compile.prompt.txt')
		});
		gathered.push(...files);
	}

	const uniquePaths = [...new Set(gathered)];
	const withTimes: Array<{ path: string; mtime: number }> = [];
	for (const absPath of uniquePaths) {
		try {
			const stat = await fs.stat(absPath);
			withTimes.push({ path: absPath, mtime: stat.mtimeMs });
		} catch {
			continue;
		}
	}

	withTimes.sort((a, b) => b.mtime - a.mtime);
	const selected = withTimes.slice(0, Math.max(limit * 2, limit));

	const out: PromptTraceItem[] = [];
	for (const item of selected) {
		const promptPath = item.path;
		const compileDir = promptPath.slice(0, -'il.compile.prompt.txt'.length);
		const responsePath = `${compileDir}il.compile.raw_response.txt`;
		const reportPath = `${compileDir}il.compile.report.json`;

		const prompt = await fs.readFile(promptPath, 'utf-8').catch(() => '');
		if (!prompt) {
			continue;
		}
		const response = await fs.readFile(responsePath, 'utf-8').catch(() => '');
		const report = await readJsonObject(reportPath);
		const stat = await fs.stat(promptPath);

		out.push({
			id: `${toRepoRelative(promptPath)}:${stat.mtimeMs}`,
			promptPath: toRepoRelative(promptPath),
			responsePath: response ? toRepoRelative(responsePath) : null,
			reportPath: report ? toRepoRelative(reportPath) : null,
			requestText: requestFromPrompt(prompt),
			promptPreview: snippet(prompt),
			responsePreview: snippet(response),
			status: report ? normalizeStatus(getByPath(report, 'status')) : 'UNKNOWN',
			compileLatencyMs: asNumber(report ? getByPath(report, 'compile_latency_ms') : null),
			provider: asString(report ? getByPath(report, 'provider_selected') : ''),
			model: asString(report ? getByPath(report, 'model') : ''),
			promptTemplateId: asString(report ? getByPath(report, 'prompt_template_id') : ''),
			capturedAt: stat.mtime.toISOString()
		});
	}

	const sorted = out.sort(
		(a, b) => new Date(b.capturedAt).getTime() - new Date(a.capturedAt).getTime()
	);
	return sorted.slice(0, Math.max(1, limit));
}
