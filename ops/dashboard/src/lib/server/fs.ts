import { existsSync } from 'node:fs';
import { promises as fs } from 'node:fs';
import path from 'node:path';

export interface WalkFileOptions {
	maxDepth?: number;
	maxResults?: number;
	match: (absPath: string) => boolean;
}

const REPO_SENTINELS = ['Makefile', 'AGENTS.md', 'scripts', 'docs'];

function looksLikeRepoRoot(candidate: string): boolean {
	return REPO_SENTINELS.every((name) => existsSync(path.join(candidate, name)));
}

function ascendToRepoRoot(startDir: string): string | null {
	let cursor = path.resolve(startDir);
	while (true) {
		if (looksLikeRepoRoot(cursor)) {
			return cursor;
		}
		const parent = path.dirname(cursor);
		if (parent === cursor) {
			return null;
		}
		cursor = parent;
	}
}

export function resolveRepoRoot(): string {
	const envRoot = process.env.MAAKIE_REPO_ROOT;
	if (envRoot) {
		const abs = path.resolve(envRoot);
		if (looksLikeRepoRoot(abs)) {
			return abs;
		}
	}

	const attempts = [
		process.cwd(),
		path.resolve(process.cwd(), '..'),
		path.resolve(process.cwd(), '../..'),
		path.resolve(process.cwd(), '../../..')
	];
	for (const attempt of attempts) {
		const found = ascendToRepoRoot(attempt);
		if (found) {
			return found;
		}
	}

	throw new Error('Could not resolve repository root. Set MAAKIE_REPO_ROOT explicitly.');
}

export const REPO_ROOT = resolveRepoRoot();

export function repoJoin(...parts: string[]): string {
	return path.resolve(REPO_ROOT, ...parts);
}

export function toRepoRelative(absPath: string): string {
	return path.relative(REPO_ROOT, absPath).replaceAll(path.sep, '/');
}

export async function readJsonObject(absPath: string): Promise<Record<string, unknown> | null> {
	try {
		const raw = await fs.readFile(absPath, 'utf-8');
		const parsed = JSON.parse(raw);
		if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
			return null;
		}
		return parsed as Record<string, unknown>;
	} catch {
		return null;
	}
}

export function getByPath(root: unknown, dottedPath: string): unknown {
	let cursor: unknown = root;
	for (const segment of dottedPath.split('.')) {
		if (!cursor || typeof cursor !== 'object' || Array.isArray(cursor)) {
			return undefined;
		}
		cursor = (cursor as Record<string, unknown>)[segment];
	}
	return cursor;
}

export function asNumber(value: unknown): number | null {
	if (typeof value === 'number' && Number.isFinite(value)) {
		return value;
	}
	if (typeof value === 'string' && value.trim()) {
		const n = Number(value);
		if (Number.isFinite(n)) {
			return n;
		}
	}
	return null;
}

export function asString(value: unknown): string {
	if (typeof value === 'string') {
		return value;
	}
	if (value === null || value === undefined) {
		return '';
	}
	return String(value);
}

export function asIsoDate(value: unknown): string | null {
	const text = asString(value).trim();
	if (!text) {
		return null;
	}
	const dt = new Date(text);
	if (Number.isNaN(dt.getTime())) {
		return null;
	}
	return dt.toISOString();
}

export function normalizeStatus(value: unknown): 'PASS' | 'WARN' | 'FAIL' | 'SKIP' | 'UNKNOWN' {
	const status = asString(value).trim().toUpperCase();
	if (status === 'PASS' || status === 'WARN' || status === 'FAIL' || status === 'SKIP') {
		return status;
	}
	return 'UNKNOWN';
}

export function formatNumber(value: number | null, digits = 4): string {
	if (value === null || !Number.isFinite(value)) {
		return 'NA';
	}
	return value.toFixed(digits);
}

export function formatPercent(value: number | null): string {
	if (value === null || !Number.isFinite(value)) {
		return 'NA';
	}
	return `${(value * 100).toFixed(2)}%`;
}

export function summarizeReasons(value: unknown): string {
	if (!Array.isArray(value)) {
		return '';
	}
	const items = value
		.map((v) => asString(v).trim())
		.filter((v) => v.length > 0)
		.slice(0, 3);
	return items.join(', ');
}

export async function walkFiles(rootDir: string, options: WalkFileOptions): Promise<string[]> {
	const { maxDepth = 8, maxResults = 1000, match } = options;
	const out: string[] = [];
	const stack: Array<{ dir: string; depth: number }> = [{ dir: rootDir, depth: 0 }];

	while (stack.length > 0 && out.length < maxResults) {
		const current = stack.pop();
		if (!current) {
			continue;
		}
		let entries;
		try {
			entries = await fs.readdir(current.dir, { withFileTypes: true, encoding: 'utf8' });
		} catch {
			continue;
		}

		for (const entry of entries) {
			if (out.length >= maxResults) {
				break;
			}
			const abs = path.join(current.dir, entry.name);
			if (entry.isDirectory()) {
				if (current.depth < maxDepth) {
					stack.push({ dir: abs, depth: current.depth + 1 });
				}
				continue;
			}
			if (!entry.isFile()) {
				continue;
			}
			if (match(abs)) {
				out.push(abs);
			}
		}
	}

	return out;
}

export async function statMtimeIso(absPath: string): Promise<string> {
	const st = await fs.stat(absPath);
	return st.mtime.toISOString();
}
