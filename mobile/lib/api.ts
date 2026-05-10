export const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

export interface ChecklistItem {
  id: string;
  action: string;
  acceptance_criteria: string;
  failure_criteria: string;
  severity: 'CRITICAL' | 'MAJOR' | 'MINOR';
  source_section: string;
  examination_frequency: string;
  chunk_id?: string;
}

export interface Chunk {
  id: string;
  type: string;
  grounding: {
    page: number;
    box: { left: number; top: number; right: number; bottom: number } | number[];
  };
}

export interface GeneratedChecklist {
  id: string;
  document_name: string;
  generated_at: string;
  source_document_hash: string;
  status: string;
  items: ChecklistItem[];
  item_count: number;
}

export interface TranslateResponse {
  checklist_id: string;
  language: string;
  cache_hit: boolean;
  items: ChecklistItem[];
}

export async function generateChecklist(
  fileUri: string, 
  fileName: string, 
  force: boolean = false
): Promise<GeneratedChecklist> {
  const formData = new FormData();
  formData.append('file', { uri: fileUri, name: fileName, type: 'application/pdf' } as any);

  const url = new URL(`${API_BASE}/api/checklists/generate`);
  if (force) url.searchParams.append('force', 'true');

  const res = await fetch(url.toString(), {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail ?? `Server error ${res.status}`);
  }

  return res.json();
}

export async function getTranslatedItems(checklistId: string, lang: string): Promise<TranslateResponse> {
  const res = await fetch(`${API_BASE}/api/checklists/${checklistId}/items?lang=${lang}`);

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail ?? `Server error ${res.status}`);
  }

  return res.json();
}

export async function getChunks(docHash: string): Promise<Chunk[]> {
  const res = await fetch(`${API_BASE}/api/extractions/${docHash}/chunks`);

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail ?? `Server error ${res.status}`);
  }

  return res.json();
}
