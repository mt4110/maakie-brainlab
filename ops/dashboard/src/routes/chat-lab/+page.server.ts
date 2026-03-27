import { queryRagSources } from '$lib/server/chat-rag-data';
import { getLatestRunInspector } from '$lib/server/run-inspector-data';

export async function load({ url }: { url: URL }) {
	const [sources, latestInspector] = await Promise.all([
		queryRagSources({ page: 1, pageSize: 12 }),
		getLatestRunInspector('chat-lab')
	]);
	const prefillMessage = (url.searchParams.get('prefill') || '').trim();
	return { sources, latestInspector, prefillMessage };
}
