import { getEvidenceHistory } from '$lib/server/dashboard-data';
import { listRunInspectorHistory } from '$lib/server/run-inspector-data';

export async function load() {
	const [history, runHistory] = await Promise.all([
		getEvidenceHistory(300),
		listRunInspectorHistory(300, 'all')
	]);
	return {
		history,
		runHistory
	};
}
