import { getPromptTrace } from '$lib/server/dashboard-data';

export async function load() {
	const prompts = await getPromptTrace(80);
	return {
		prompts
	};
}
