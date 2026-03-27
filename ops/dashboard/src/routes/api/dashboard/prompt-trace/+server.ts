import { json } from '@sveltejs/kit';

import { getPromptTrace } from '$lib/server/dashboard-data';

export async function GET({ url }: { url: URL }) {
	const limitRaw = Number(url.searchParams.get('limit') ?? '40');
	const limit = Number.isFinite(limitRaw) ? Math.max(1, Math.min(200, Math.trunc(limitRaw))) : 40;
	const payload = await getPromptTrace(limit);
	return json({ items: payload });
}
