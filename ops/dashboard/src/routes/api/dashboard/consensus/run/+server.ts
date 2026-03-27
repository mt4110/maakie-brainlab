import { json } from '@sveltejs/kit';

import { runConsensus } from '$lib/server/consensus-data';
import type { ConsensusRunRequest } from '$lib/server/types';

export async function POST({ request }: { request: Request }) {
	let body: ConsensusRunRequest;
	try {
		body = (await request.json()) as ConsensusRunRequest;
	} catch {
		return json({ error: 'Invalid JSON body.' }, { status: 400 });
	}

	try {
		const payload = await runConsensus(body);
		return json(payload);
	} catch (error) {
		return json(
			{
				error: error instanceof Error ? error.message : 'Consensus run failed.'
			},
			{ status: 500 }
		);
	}
}
