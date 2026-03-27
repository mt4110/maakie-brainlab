<script lang="ts">
	import {
		I18N_CONTEXT_KEY,
		LOCALE_STORAGE_KEY,
		isLocale,
		t,
		type I18nKey,
		type Locale,
		type LocaleState
	} from '$lib/i18n';
	import { page } from '$app/state';
	import { onMount, setContext } from 'svelte';
	import '../app.css';

	let { children } = $props();
	const localeState = $state<LocaleState>({ value: 'ja' });
	setContext(I18N_CONTEXT_KEY, localeState);

	const navItems: Array<{ href: string; key: I18nKey }> = [
		{ href: '/', key: 'navOverview' },
		{ href: '/history', key: 'navHistory' },
		{ href: '/prompt-trace', key: 'navPromptTrace' },
		{ href: '/fine-tune', key: 'navFineTune' },
		{ href: '/ai-lab', key: 'navAiLab' },
		{ href: '/chat-lab', key: 'navChatLab' },
		{ href: '/consensus-il', key: 'navConsensus' },
		{ href: '/ml-studio', key: 'navMlStudio' },
		{ href: '/rag-lab', key: 'navRagLab' },
		{ href: '/langchain-lab', key: 'navLangChainLab' },
		{ href: '/sitemap', key: 'navSitemap' },
		{ href: '/site-docs', key: 'navDocs' }
	];

	function isActive(href: string): boolean {
		const current = page.url.pathname;
		if (href === '/') {
			return current === '/';
		}
		return current === href || current.startsWith(`${href}/`);
	}

	function setLocale(next: Locale) {
		localeState.value = next;
	}

	onMount(() => {
		const saved = window.localStorage.getItem(LOCALE_STORAGE_KEY);
		if (saved && isLocale(saved)) {
			localeState.value = saved;
		}
	});

	$effect(() => {
		if (typeof document !== 'undefined') {
			document.documentElement.lang = localeState.value;
		}
		if (typeof window !== 'undefined') {
			window.localStorage.setItem(LOCALE_STORAGE_KEY, localeState.value);
		}
	});
</script>

<svelte:head>
	<title>{t(localeState.value, 'appTitle')}</title>
	<link rel="icon" href="data:," />
</svelte:head>

<div class="app-shell">
	<header class="topbar">
		<div class="topbar-inner">
			<div class="brand">
				<span>{t(localeState.value, 'brand')}</span>
			</div>
			<div class="topbar-controls">
				<div
					class="locale-switch"
					role="group"
					aria-label={t(localeState.value, 'languageSwitchAria')}
				>
					<button
						type="button"
						class={`locale-btn ${localeState.value === 'ja' ? 'locale-btn-active' : ''}`}
						onclick={() => setLocale('ja')}>JA</button
					>
					<button
						type="button"
						class={`locale-btn ${localeState.value === 'en' ? 'locale-btn-active' : ''}`}
						onclick={() => setLocale('en')}>EN</button
					>
				</div>
				<nav class="nav" aria-label={t(localeState.value, 'mainNavAria')}>
					{#each navItems as item}
						<a
							class={`nav-link ${isActive(item.href) ? 'nav-link-active' : ''}`}
							href={item.href}>{t(localeState.value, item.key)}</a
						>
					{/each}
				</nav>
			</div>
		</div>
	</header>
	<main class="page-wrap">{@render children()}</main>
</div>
