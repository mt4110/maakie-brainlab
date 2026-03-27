import { getOverviewPayload } from '$lib/server/dashboard-data';

export async function load() {
	const overview = await getOverviewPayload();
	return {
		overview
	};
}
