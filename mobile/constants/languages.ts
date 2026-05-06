export const LANGUAGES = [
  { code: 'EN', label: 'English' },
  { code: 'NB', label: 'Norwegian' },
  { code: 'FR', label: 'French' },
  { code: 'AR', label: 'Arabic' },
  { code: 'PL', label: 'Polish' },
  { code: 'ID', label: 'Indonesian' },
  { code: 'ES', label: 'Spanish' },
  { code: 'PT-BR', label: 'Portuguese' },
  { code: 'NL', label: 'Dutch' },
  { code: 'RO', label: 'Romanian' },
] as const;

export type LanguageCode = typeof LANGUAGES[number]['code'];
