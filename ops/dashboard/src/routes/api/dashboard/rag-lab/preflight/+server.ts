import { json } from '@sveltejs/kit';

import { getRagLabGuidePayload } from '$lib/server/rag-lab-data';

export async function GET() {
	try {
		const payload = await getRagLabGuidePayload();
		return json(payload);
	} catch (error) {
		return json(
			{
				error: error instanceof Error ? error.message : 'Failed to load preflight checks.'
			},
			{ status: 500 }
		);
	}
}
