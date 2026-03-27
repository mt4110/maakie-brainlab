import { getFineTuneHistory } from '$lib/server/lab-data';

export async function load() {
	const history = await getFineTuneHistory(40);
	return { history };
}
