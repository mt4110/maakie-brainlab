export type DashboardStatus = 'PASS' | 'WARN' | 'FAIL' | 'SKIP' | 'UNKNOWN' | 'MISSING';

export type PipelineKey = 'rag' | 'langchain' | 'ml' | 'quality' | 'operator';
export type AiLabChannel =
	| 'local-model'
	| 'mcp'
	| 'ai-cli'
	| 'fine-tune'
	| 'rag-tuning'
	| 'langchain';

export interface MetricCell {
	label: string;
	value: string;
}

export interface PipelineSnapshot {
	key: PipelineKey;
	title: string;
	artifactPath: string;
	schema: string;
	status: DashboardStatus;
	capturedAt: string | null;
	summary: string;
	metrics: MetricCell[];
}

export interface OverviewPayload {
	generatedAt: string;
	repoRoot: string;
	health: {
		pass: number;
		warn: number;
		fail: number;
		missing: number;
	};
	pipelines: PipelineSnapshot[];
}

export interface EvidenceHistoryItem {
	id: string;
	artifactPath: string;
	schema: string;
	status: DashboardStatus;
	capturedAt: string | null;
	modifiedAt: string;
	summary: string;
}

export interface PromptTraceItem {
	id: string;
	promptPath: string;
	responsePath: string | null;
	reportPath: string | null;
	requestText: string;
	promptPreview: string;
	responsePreview: string;
	status: DashboardStatus;
	compileLatencyMs: number | null;
	provider: string;
	model: string;
	promptTemplateId: string;
	capturedAt: string;
}

export interface PipelineRunRequest {
	pipeline: PipelineKey | 'all';
	runDir?: string;
}

export interface CommandRunResult {
	pipeline: PipelineKey;
	command: string[];
	status: DashboardStatus;
	exitCode: number;
	startedAt: string;
	endedAt: string;
	durationMs: number;
	runDir: string | null;
	stdout: string;
	stderr: string;
}

export interface PipelineRunResponse {
	status: DashboardStatus;
	results: CommandRunResult[];
}

export interface AiLabRunRequest {
	channel: AiLabChannel;
	prompt?: string;
	model?: string;
	commandTemplate?: string;
	profiles?: string;
	seed?: number;
}

export interface AiLabRunRecord {
	id: string;
	channel: AiLabChannel;
	createdAt: string;
	prompt: string;
	command: string;
	status: DashboardStatus;
	exitCode: number;
	durationMs: number;
	artifactPath: string | null;
	stdout: string;
	stderr: string;
}

export interface AiLabRunResponse {
	status: DashboardStatus;
	record: AiLabRunRecord;
	inspector?: RunInspectorRecord;
}

export interface FineTuneHistoryItem {
	id: string;
	capturedAt: string;
	reportPath: string;
	model: string;
	bestProfile: string;
	fallbackCount: number | null;
	objectiveScore: number | null;
	status: DashboardStatus;
}

export interface ConsensusRunRequest {
	prompt: string;
	cliCommandTemplate?: string;
	apiBase?: string;
	apiModel?: string;
	apiKey?: string;
}

export interface ConsensusAgentResult {
	agent: 'local' | 'cli' | 'api';
	status: DashboardStatus;
	durationMs: number;
	command: string;
	output: string;
	error: string;
	evidenceRefs: string[];
	guardPassed: boolean;
}

export interface ConsensusRecord {
	id: string;
	createdAt: string;
	prompt: string;
	contract: {
		minAgents: number;
		requiredEvidence: boolean;
		requiredGuards: boolean;
	};
	guard: {
		passed: boolean;
		details: string[];
	};
	evidence: {
		refs: string[];
	};
	result: {
		status: DashboardStatus;
		summary: string;
		consensusText: string;
	};
	timeline: {
		totalMs: number;
		localMs: number | null;
		cliMs: number | null;
		apiMs: number | null;
	};
	agents: ConsensusAgentResult[];
}

export interface ConsensusRunResponse {
	status: DashboardStatus;
	record: ConsensusRecord;
}

export interface RagSourceItem {
	id: string;
	name: string;
	description: string;
	path: string;
	tags: string[];
	enabled: boolean;
	createdAt: string;
	updatedAt: string;
}

export interface RagSourceCreateRequest {
	name: string;
	description?: string;
	path?: string;
	tags?: string[] | string;
	enabled?: boolean;
}

export interface RagSourceUpdateRequest {
	name?: string;
	description?: string;
	path?: string;
	tags?: string[] | string;
	enabled?: boolean;
}

export interface RagSuggestion {
	id: string;
	name: string;
	path: string;
	tags: string[];
	score: number;
	reason: string;
}

export interface ChatTurn {
	role: 'system' | 'user' | 'assistant';
	content: string;
}

export interface ChatRunRequest {
	message: string;
	messages?: ChatTurn[];
	selectedRagIds?: string[];
}

export interface ChatRunResponse {
	status: DashboardStatus;
	assistantMessage: string;
	ragSuggestions: RagSuggestion[];
	model: string;
	apiBase: string;
	runId?: string;
	inspector?: RunInspectorRecord;
}

export type RunInspectorScope = 'ai-lab' | 'chat-lab';

export interface RunInspectorMessage {
	seq: number;
	role: 'system' | 'user' | 'assistant' | 'tool' | 'meta';
	content: string;
}

export interface RunInspectorRetrieval {
	seq: number;
	sourceId: string;
	sourcePath: string;
	chunkText: string;
	score: number | null;
	reason: string;
}

export interface RunInspectorVote {
	voter: string;
	verdict: string;
	score: number | null;
	rationale: string;
}

export interface RunInspectorRecord {
	id: string;
	scope: RunInspectorScope;
	source: string;
	status: DashboardStatus;
	createdAt: string;
	prompt: string;
	outputText: string;
	command: string;
	model: string;
	apiBase: string;
	durationMs: number;
	errorReason: string;
	metadata: Record<string, unknown>;
	messages: RunInspectorMessage[];
	retrievals: RunInspectorRetrieval[];
	votes: RunInspectorVote[];
}

export interface RunInspectorHistoryItem {
	id: string;
	scope: RunInspectorScope;
	source: string;
	status: DashboardStatus;
	createdAt: string;
	model: string;
	apiBase: string;
	prompt: string;
	summary: string;
	retrievalCount: number;
	errorReason: string;
}
