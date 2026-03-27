import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		host: true,
		port: 3033,
		strictPort: true
	},
	preview: {
		host: true,
		port: 3033,
		strictPort: true
	}
});
