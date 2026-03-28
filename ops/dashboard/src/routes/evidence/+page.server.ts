import { getEvidenceHistory } from '$lib/server/dashboard-data';

export async function load() {
	const history = await getEvidenceHistory(12);
	return {
		history
	};
}
