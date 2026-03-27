import { getAiLabHistory } from '$lib/server/lab-data';
import { getLatestRunInspector } from '$lib/server/run-inspector-data';

export async function load() {
	const [history, latestInspector] = await Promise.all([
		getAiLabHistory(40),
		getLatestRunInspector('ai-lab')
	]);
	return { history, latestInspector };
}
