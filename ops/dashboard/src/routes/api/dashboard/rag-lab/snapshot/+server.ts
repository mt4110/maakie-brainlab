import { json } from '@sveltejs/kit';

import { getRagReadonlySnapshotPayload } from '$lib/server/rag-lab-data';

export async function GET() {
	try {
		const payload = await getRagReadonlySnapshotPayload();
		return json(payload);
	} catch (error) {
		return json(
			{
				error:
					error instanceof Error
						? error.message
						: 'Failed to load read-only RAG snapshot.'
			},
			{ status: 500 }
		);
	}
}
