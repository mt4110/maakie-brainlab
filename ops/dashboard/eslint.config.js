import js from '@eslint/js';
import globals from 'globals';
import svelte from 'eslint-plugin-svelte';
import tseslint from 'typescript-eslint';
import svelteConfig from './svelte.config.js';

export default tseslint.config(
	{
		ignores: ['build/**', '.svelte-kit/**', 'node_modules/**']
	},
	js.configs.recommended,
	...tseslint.configs.recommended,
	...svelte.configs['flat/recommended'],
	{
		files: ['**/*.{js,ts,svelte}'],
		languageOptions: {
			globals: {
				...globals.browser,
				...globals.node
			}
		}
	},
	{
		files: ['**/*.svelte', '**/*.svelte.ts', '**/*.svelte.js'],
		languageOptions: {
			parserOptions: {
				parser: tseslint.parser,
				svelteConfig
			}
		}
	},
	{
		files: ['cypress/**/*.ts'],
		languageOptions: {
			globals: {
				...globals.mocha,
				...globals.chai,
				cy: 'readonly',
				Cypress: 'readonly'
			}
		}
	},
	{
		rules: {
			'@typescript-eslint/no-explicit-any': 'off',
			'@typescript-eslint/no-unused-vars': [
				'warn',
				{
					argsIgnorePattern: '^_',
					varsIgnorePattern: '^_'
				}
			],
			'svelte/require-each-key': 'off',
			'svelte/no-navigation-without-resolve': 'off',
			'svelte/prefer-writable-derived': 'off'
		}
	}
);
