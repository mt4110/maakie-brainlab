import { json } from '@sveltejs/kit';

import { getAiLabHistory } from '$lib/server/lab-data';

export async function GET({ url }: { url: URL }) {
	const limitRaw = Number(url.searchParams.get('limit') ?? '60');
	const limit = Number.isFinite(limitRaw) ? Math.max(1, Math.min(500, Math.trunc(limitRaw))) : 60;
	const items = await getAiLabHistory(limit);
	return json({ items });
}
