import { promises as fs } from 'node:fs';

import { getOverviewPayload } from '$lib/server/dashboard-data';
import { repoJoin } from '$lib/server/fs';

export async function load() {
	const overview = await getOverviewPayload();
	const runbookPath = repoJoin('docs/ops/S25-09_LANGCHAIN_POC.md');
	const runbook = await fs.readFile(runbookPath, 'utf-8').catch(() => '');
	return {
		langchain: overview.pipelines.find((row) => row.key === 'langchain') || null,
		runbookPreview: runbook.split(/\r?\n/).slice(0, 90).join('\n')
	};
}
