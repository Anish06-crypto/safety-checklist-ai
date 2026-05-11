import { Ionicons } from '@expo/vector-icons';
import React, { useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ChecklistCard } from '../components/ChecklistCard';
import { GroundingOverlay } from '../components/GroundingOverlay';
import { LANGUAGES } from '../constants/languages';
import { getTranslatedItems, getChunkGrounding, type Chunk } from '../lib/api';
import { useChecklistStore } from '../store/useChecklistStore';

export default function TranslateScreen() {
  const checklist = useChecklistStore((s) => s.checklist);
  const displayItems = useChecklistStore((s) => s.displayItems);
  const activeLanguage = useChecklistStore((s) => s.activeLanguage);
  const setActiveLanguage = useChecklistStore((s) => s.setActiveLanguage);
  const setDisplayItems = useChecklistStore((s) => s.setDisplayItems);
  const setCacheHit = useChecklistStore((s) => s.setCacheHit);
  const cacheHit = useChecklistStore((s) => s.cacheHit);
  const chunks = useChecklistStore((s) => s.chunks);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedChunk, setSelectedChunk] = useState<Chunk | null>(null);

  const docHash = checklist?.source_document_hash;

  const handleViewEvidence = async (chunkId?: string) => {
    if (!chunkId || !docHash) return;

    // Step 1: check the local chunks array (UUID-level chunks)
    const localChunk = chunks.find((c) => c.id === chunkId);
    if (localChunk) {
      setSelectedChunk(localChunk);
      return;
    }

    // Step 2: cell-level ID (e.g. "1-9") — fetch grounding from backend
    try {
      const remote = await getChunkGrounding(docHash, chunkId);
      if (remote) {
        setSelectedChunk(remote);
      } else {
        console.warn('No grounding found for ID:', chunkId);
      }
    } catch (err) {
      console.error('Failed to fetch grounding for', chunkId, err);
    }
  };

  async function handleLanguageSelect(code: string) {
    if (!checklist) return;
    setError(null);
    setActiveLanguage(code);

    if (code === 'EN') {
      setDisplayItems(checklist.items);
      setCacheHit(true);
      return;
    }

    setLoading(true);
    try {
      const res = await getTranslatedItems(checklist.id, code);
      setDisplayItems(res.items);
      setCacheHit(res.cache_hit);
    } catch (e: any) {
      setError(e.message ?? 'Translation failed.');
    } finally {
      setLoading(false);
    }
  }

  if (!checklist) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.empty}>
          <Text style={styles.emptyText}>No checklist loaded.</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.langBar}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.langScroll}>
          {LANGUAGES.map((lang) => {
            const active = lang.code === activeLanguage;
            return (
              <TouchableOpacity
                key={lang.code}
                style={[styles.langChip, active && styles.langChipActive]}
                onPress={() => handleLanguageSelect(lang.code)}
              >
                <Text style={[styles.langChipText, active && styles.langChipTextActive]}>
                  {lang.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </View>

      {loading ? (
        <View style={styles.loadingArea}>
          <ActivityIndicator size="large" color="#3B82F6" />
          <Text style={styles.loadingText}>Translating…</Text>
        </View>
      ) : (
        <FlatList
          data={displayItems}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.list}
          ListHeaderComponent={
            <View style={styles.statusRow}>
              {cacheHit ? (
                <View style={styles.cacheTag}>
                  <Ionicons name="flash" size={12} color="#3B82F6" />
                  <Text style={styles.cacheTagText}>Cached</Text>
                </View>
              ) : (
                <View style={[styles.cacheTag, styles.liveTag]}>
                  <Ionicons name="cloud-outline" size={12} color="#8B5CF6" />
                  <Text style={[styles.cacheTagText, styles.liveTagText]}>Live via DeepL</Text>
                </View>
              )}
              {error && (
                <View style={styles.errorBox}>
                  <Ionicons name="warning-outline" size={14} color="#EF4444" />
                  <Text style={styles.errorText}>{error}</Text>
                </View>
              )}
            </View>
          }
          renderItem={({ item, index }) => (
            <ChecklistCard 
              item={item} 
              index={index} 
              language={activeLanguage} 
              onViewEvidence={() => handleViewEvidence(item.chunk_id)}
            />
          )}
        />
      )}
      <GroundingOverlay
        visible={!!selectedChunk}
        chunk={selectedChunk}
        docHash={checklist?.source_document_hash || ''}
        onClose={() => setSelectedChunk(null)}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F172A',
  },
  langBar: {
    backgroundColor: '#1E293B',
    paddingVertical: 10,
  },
  langScroll: {
    paddingHorizontal: 16,
    gap: 8,
  },
  langChip: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 20,
    backgroundColor: '#334155',
  },
  langChipActive: {
    backgroundColor: '#2563EB',
  },
  langChipText: {
    color: '#94A3B8',
    fontSize: 13,
    fontWeight: '500',
  },
  langChipTextActive: {
    color: '#FFFFFF',
  },
  list: {
    padding: 16,
    paddingBottom: 40,
  },
  statusRow: {
    marginBottom: 12,
    gap: 8,
  },
  cacheTag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#1E3A5F',
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  liveTag: {
    backgroundColor: '#2D1F4E',
  },
  cacheTagText: {
    color: '#3B82F6',
    fontSize: 11,
    fontWeight: '600',
  },
  liveTagText: {
    color: '#8B5CF6',
  },
  loadingArea: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  loadingText: {
    color: '#94A3B8',
    fontSize: 14,
  },
  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyText: {
    color: '#64748B',
    fontSize: 14,
  },
  errorBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#2D1B1B',
    borderRadius: 8,
    padding: 10,
    gap: 6,
  },
  errorText: {
    color: '#EF4444',
    fontSize: 12,
    flex: 1,
  },
});
