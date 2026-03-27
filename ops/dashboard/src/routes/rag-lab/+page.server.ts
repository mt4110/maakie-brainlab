import { promises as fs } from 'node:fs';

import { getOverviewPayload } from '$lib/server/dashboard-data';
import {
	getRagLabGuidePayload,
	getRagModelListPayload,
	getRagReadonlySnapshotPayload
} from '$lib/server/rag-lab-data';
import { repoJoin } from '$lib/server/fs';

export async function load() {
	const overview = await getOverviewPayload();
	const guide = await getRagLabGuidePayload();
	const snapshot = await getRagReadonlySnapshotPayload();
	const models = await getRagModelListPayload();
	const ragConfigPath = repoJoin('docs/ops/S25-08_RAG_TUNING.toml');
	const ragConfig = await fs.readFile(ragConfigPath, 'utf-8').catch(() => '');
	return {
		rag: overview.pipelines.find((row) => row.key === 'rag') || null,
		guide,
		snapshot,
		models,
		ragConfigPreview: ragConfig.split(/\r?\n/).slice(0, 80).join('\n')
	};
}
