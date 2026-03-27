export type Locale = 'ja' | 'en';

export interface LocaleState {
	value: Locale;
}

export const I18N_CONTEXT_KEY = 'dashboard.i18n';
export const LOCALE_STORAGE_KEY = 'dashboard.locale';

const DICT = {
	ja: {
		appTitle: 'Maakie Ops ダッシュボード',
		brand: 'Maakie Brainlab Ops',
		mainNavAria: 'メインナビゲーション',
		languageSwitchAria: '言語切替',
		navOverview: '概要',
		navHistory: 'エビデンス履歴',
		navPromptTrace: 'プロンプト追跡',
		navFineTune: 'ファインチューン',
		navAiLab: 'AI ラボ',
		navChatLab: 'Chat + RAG',
		navConsensus: 'コンセンサス IL',
		navMlStudio: 'ML スタジオ',
		navRagLab: 'RAG ラボ',
		navLangChainLab: 'LangChain ラボ',
		navSitemap: 'サイトマップ',
		navDocs: 'サイトドキュメント'
	},
	en: {
		appTitle: 'Maakie Ops Dashboard',
		brand: 'Maakie Brainlab Ops',
		mainNavAria: 'Main navigation',
		languageSwitchAria: 'Language switch',
		navOverview: 'Overview',
		navHistory: 'Evidence History',
		navPromptTrace: 'Prompt Trace',
		navFineTune: 'Fine-tune',
		navAiLab: 'AI Lab',
		navChatLab: 'Chat + RAG',
		navConsensus: 'Consensus IL',
		navMlStudio: 'ML Studio',
		navRagLab: 'RAG Lab',
		navLangChainLab: 'LangChain Lab',
		navSitemap: 'Site Map',
		navDocs: 'Site Docs'
	}
} as const;

export type I18nKey = keyof (typeof DICT)['ja'];

export function isLocale(value: string): value is Locale {
	return value === 'ja' || value === 'en';
}

export function t(locale: Locale, key: I18nKey): string {
	return DICT[locale][key];
}
