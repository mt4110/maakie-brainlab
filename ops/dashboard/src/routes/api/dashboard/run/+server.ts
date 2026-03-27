import { json } from '@sveltejs/kit';

import { runAllPipelines, runSinglePipeline } from '$lib/server/pipeline-run';
import type { PipelineKey, PipelineRunRequest } from '$lib/server/types';

const VALID: Array<PipelineKey | 'all'> = ['rag', 'langchain', 'ml', 'quality', 'operator', 'all'];

function isPipeline(value: string): value is PipelineKey | 'all' {
	return VALID.includes(value as PipelineKey | 'all');
}

export async function POST({ request }: { request: Request }) {
	let body: PipelineRunRequest;
	try {
		body = (await request.json()) as PipelineRunRequest;
	} catch {
		return json({ error: 'Invalid JSON body.' }, { status: 400 });
	}

	const pipeline = String(body.pipeline || '').trim();
	if (!isPipeline(pipeline)) {
		return json(
			{
				error: "pipeline must be one of 'rag' | 'langchain' | 'ml' | 'quality' | 'operator' | 'all'"
			},
			{ status: 400 }
		);
	}

	try {
		if (pipeline === 'all') {
			const payload = await runAllPipelines(body.runDir);
			return json(payload);
		}
		const payload = await runSinglePipeline(pipeline, body.runDir);
		return json(payload);
	} catch (error) {
		return json(
			{
				error: error instanceof Error ? error.message : 'Pipeline execution failed.'
			},
			{ status: 500 }
		);
	}
}
