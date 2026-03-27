import { getConsensusHistory } from '$lib/server/consensus-data';

export async function load() {
	const history = await getConsensusHistory(20);
	return { history };
}
