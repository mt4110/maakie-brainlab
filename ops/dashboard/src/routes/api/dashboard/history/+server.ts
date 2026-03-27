import { json } from '@sveltejs/kit';

import { getEvidenceHistory } from '$lib/server/dashboard-data';

export async function GET({ url }: { url: URL }) {
	const limitRaw = Number(url.searchParams.get('limit') ?? '200');
	const limit = Number.isFinite(limitRaw)
		? Math.max(1, Math.min(1000, Math.trunc(limitRaw)))
		: 200;
	const payload = await getEvidenceHistory(limit);
	return json({ items: payload });
}
