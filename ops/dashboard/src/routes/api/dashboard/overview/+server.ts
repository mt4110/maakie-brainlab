import { json } from '@sveltejs/kit';

import { getOverviewPayload } from '$lib/server/dashboard-data';

export async function GET() {
	const payload = await getOverviewPayload();
	return json(payload);
}
