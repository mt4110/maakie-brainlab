import { promises as fs } from 'node:fs';

import { getOverviewPayload } from '$lib/server/dashboard-data';
import { getFineTuneHistory } from '$lib/server/lab-data';
import { repoJoin } from '$lib/server/fs';

export async function load() {
	const [overview, fineTuneHistory] = await Promise.all([
		getOverviewPayload(),
		getFineTuneHistory(10)
	]);
	const templatePath = repoJoin('docs/ops/S25-07_ML_EXPERIMENT_TEMPLATE.json');
	const template = await fs.readFile(templatePath, 'utf-8').catch(() => '');
	return {
		ml: overview.pipelines.find((row) => row.key === 'ml') || null,
		fineTuneHistory,
		templatePreview: template.split(/\r?\n/).slice(0, 120).join('\n')
	};
}
