import { listRagSourcesReadOnly } from '$lib/server/chat-rag-data';

export async function load() {
	const sourceState = await listRagSourcesReadOnly();
	return {
		sources: sourceState.items,
		sourcesDegraded: sourceState.degraded,
		sourcesMessageJa: sourceState.messageJa,
		sourcesMessageEn: sourceState.messageEn
	};
}
