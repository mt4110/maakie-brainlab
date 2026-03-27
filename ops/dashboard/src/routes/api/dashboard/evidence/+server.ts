import { json } from '@sveltejs/kit';

import { getEvidenceArtifactByPath } from '$lib/server/dashboard-data';

export async function GET({ url }: { url: URL }) {
	const artifactPath = (url.searchParams.get('path') || '').trim();
	if (!artifactPath) {
		return json({ error: 'path query is required' }, { status: 400 });
	}

	const artifact = await getEvidenceArtifactByPath(artifactPath);
	if (!artifact) {
		return json({ error: 'artifact not found' }, { status: 404 });
	}
	return json({ item: artifact });
}
