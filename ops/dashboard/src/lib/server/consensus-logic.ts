import type { ConsensusAgentResult, DashboardStatus } from './types';

export function evidenceRefsFromText(text: string): string[] {
	const refs = new Set<string>();
	const citeLine = /(^|\n)-\s+([^\n#]+#chunk-\d+)/g;
	for (const m of text.matchAll(citeLine)) {
		if (m[2]) {
			refs.add(m[2].trim());
		}
	}
	const urlRe = /(https?:\/\/[^\s)]+)/g;
	for (const m of text.matchAll(urlRe)) {
		if (m[1]) {
			refs.add(m[1].trim());
		}
	}
	return [...refs].slice(0, 20);
}

export function firstMeaningfulLine(text: string): string {
	const lines = text
		.split(/\r?\n/)
		.map((line) => line.trim())
		.filter(Boolean)
		.filter(
			(line) =>
				!line.startsWith('結論:') &&
				!line.startsWith('根拠:') &&
				!line.startsWith('参照:') &&
				!line.startsWith('不確実性:')
		);
	if (lines.length === 0) {
		return '';
	}
	return lines[0].replace(/^[-*]\s*/, '').slice(0, 260);
}

export function buildConsensusText(agents: ConsensusAgentResult[]): string {
	const lines: string[] = [];
	for (const item of agents) {
		if (item.status !== 'PASS') {
			continue;
		}
		const top = firstMeaningfulLine(item.output);
		if (!top) {
			continue;
		}
		lines.push(`- [${item.agent}] ${top}`);
	}
	if (lines.length === 0) {
		return 'No consensus text generated.';
	}
	return ['Consensus summary:', ...lines].join('\n');
}

export interface ContractEvaluationInput {
	passAgents: number;
	activeAgents: number;
	evidenceCount: number;
	guardDetails: string[];
	minAgents?: number;
	requiredEvidence?: boolean;
	requiredGuards?: boolean;
}

export interface ContractEvaluationOutput {
	status: DashboardStatus;
	details: string[];
	summary: string;
	contract: {
		minAgents: number;
		requiredEvidence: boolean;
		requiredGuards: boolean;
	};
}

export function evaluateContract(input: ContractEvaluationInput): ContractEvaluationOutput {
	const contract = {
		minAgents: input.minAgents ?? 2,
		requiredEvidence: input.requiredEvidence ?? true,
		requiredGuards: input.requiredGuards ?? true
	};
	const details = [...input.guardDetails];

	if (input.passAgents < contract.minAgents) {
		details.push(
			`contract: requires >=${contract.minAgents} PASS agents, got ${input.passAgents}`
		);
	}
	if (contract.requiredEvidence && input.evidenceCount === 0) {
		details.push('contract: evidence refs are empty');
	}
	if (contract.requiredGuards && input.guardDetails.length > 0) {
		details.push('contract: one or more guards failed');
	}

	let status: DashboardStatus = 'PASS';
	if (input.passAgents === 0) {
		status = 'FAIL';
	} else if (details.length > 0) {
		status = 'WARN';
	}

	return {
		status,
		details,
		summary: `pass=${input.passAgents}/${input.activeAgents}, evidence=${input.evidenceCount}`,
		contract
	};
}
