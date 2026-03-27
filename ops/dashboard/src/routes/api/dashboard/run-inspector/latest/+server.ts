import { json } from '@sveltejs/kit';

import { getLatestRunInspector } from '$lib/server/run-inspector-data';
import type { RunInspectorScope } from '$lib/server/types';

function toScope(value: string): RunInspectorScope | null {
	const scope = value.trim().toLowerCase();
	if (scope === 'ai-lab' || scope === 'chat-lab') {
		return scope;
	}
	return null;
}

export async function GET({ url }: { url: URL }) {
	const rawScope = url.searchParams.get('scope') || '';
	const scope = toScope(rawScope);
	if (!scope) {
		return json(
			{
				error: 'scope must be one of: ai-lab, chat-lab'
			},
			{ status: 400 }
		);
	}

	const item = await getLatestRunInspector(scope);
	return json({ item });
}
