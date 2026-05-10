import { create } from 'zustand';
import type { ChecklistItem, Chunk, GeneratedChecklist } from '../lib/api';

interface ChecklistStore {
  checklist: GeneratedChecklist | null;
  setChecklist: (c: GeneratedChecklist) => void;
  displayItems: ChecklistItem[];
  setDisplayItems: (items: ChecklistItem[]) => void;
  chunks: Chunk[];
  setChunks: (chunks: Chunk[]) => void;
  activeLanguage: string;
  setActiveLanguage: (lang: string) => void;
  cacheHit: boolean;
  setCacheHit: (v: boolean) => void;
  reset: () => void;
}

export const useChecklistStore = create<ChecklistStore>((set) => ({
  checklist: null,
  setChecklist: (checklist) =>
    set({ checklist, displayItems: checklist.items, activeLanguage: 'EN' }),
  displayItems: [],
  setDisplayItems: (displayItems) => set({ displayItems }),
  chunks: [],
  setChunks: (chunks) => set({ chunks }),
  activeLanguage: 'EN',
  setActiveLanguage: (activeLanguage) => set({ activeLanguage }),
  cacheHit: false,
  setCacheHit: (cacheHit) => set({ cacheHit }),
  reset: () =>
    set({
      checklist: null,
      displayItems: [],
      chunks: [],
      activeLanguage: 'EN',
      cacheHit: false,
    }),
}));
