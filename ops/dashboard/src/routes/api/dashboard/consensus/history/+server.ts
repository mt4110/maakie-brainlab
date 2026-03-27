import { json } from '@sveltejs/kit';

import { getConsensusHistory } from '$lib/server/consensus-data';

export async function GET({ url }: { url: URL }) {
	const limitRaw = Number(url.searchParams.get('limit') ?? '30');
	const limit = Number.isFinite(limitRaw) ? Math.max(1, Math.min(200, Math.trunc(limitRaw))) : 30;
	const items = await getConsensusHistory(limit);
	return json({ items });
}
