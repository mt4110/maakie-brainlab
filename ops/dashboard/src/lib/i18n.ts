export type Locale = 'ja' | 'en';

export interface LocaleState {
	value: Locale;
}

export const I18N_CONTEXT_KEY = 'dashboard.i18n';
export const LOCALE_STORAGE_KEY = 'dashboard.locale';

const DICT = {
	ja: {
		appTitle: 'Maakie Brainlab',
		brand: 'Maakie Brainlab',
		mainNavAria: 'メインナビゲーション',
		languageSwitchAria: '言語切替',
		navDocuments: '資料',
		navQuestions: '質問',
		navEvidence: '根拠',
		utilityOps: 'Ops'
	},
	en: {
		appTitle: 'Maakie Brainlab',
		brand: 'Maakie Brainlab',
		mainNavAria: 'Main navigation',
		languageSwitchAria: 'Language switch',
		navDocuments: 'Documents',
		navQuestions: 'Questions',
		navEvidence: 'Evidence',
		utilityOps: 'Ops'
	}
} as const;

export type I18nKey = keyof (typeof DICT)['ja'];

export function isLocale(value: string): value is Locale {
	return value === 'ja' || value === 'en';
}

export function t(locale: Locale, key: I18nKey): string {
	return DICT[locale][key];
}
