import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import React, { useState } from 'react';
import {
  FlatList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ChecklistCard } from '../components/ChecklistCard';
import { GroundingOverlay } from '../components/GroundingOverlay';
import { useChecklistStore } from '../store/useChecklistStore';
import { getChunkGrounding, type Chunk } from '../lib/api';

const SEVERITY_ORDER = { CRITICAL: 0, MAJOR: 1, MINOR: 2 } as const;

export default function ChecklistScreen() {
  const checklist = useChecklistStore((s) => s.checklist);
  const displayItems = useChecklistStore((s) => s.displayItems);
  const chunks = useChecklistStore((s) => s.chunks);

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

  if (!checklist) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.empty}>
          <Text style={styles.emptyText}>No checklist loaded. Upload a PDF first.</Text>
          <TouchableOpacity style={styles.backBtn} onPress={() => router.replace('/')}>
            <Text style={styles.backBtnText}>Go back</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  const sorted = [...displayItems].sort(
    (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]
  );

  const counts = {
    CRITICAL: sorted.filter((i) => i.severity === 'CRITICAL').length,
    MAJOR: sorted.filter((i) => i.severity === 'MAJOR').length,
    MINOR: sorted.filter((i) => i.severity === 'MINOR').length,
  };

  return (
    <SafeAreaView style={styles.container}>
      <FlatList
        data={sorted}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          <View style={styles.header}>
            <Text style={styles.docName} numberOfLines={1}>
              {checklist.document_name}
            </Text>
            <View style={styles.statsRow}>
              <StatPill count={counts.CRITICAL} color="#DC2626" label="Critical" />
              <StatPill count={counts.MAJOR} color="#D97706" label="Major" />
              <StatPill count={counts.MINOR} color="#16A34A" label="Minor" />
            </View>
            <TouchableOpacity
              style={styles.translateBtn}
              onPress={() => router.push('/translate')}
            >
              <Ionicons name="language-outline" size={16} color="#FFFFFF" />
              <Text style={styles.translateBtnText}>Translate Checklist</Text>
            </TouchableOpacity>
          </View>
        }
        renderItem={({ item, index }) => (
          <ChecklistCard
            item={item}
            index={index}
            language="EN"
            onViewEvidence={() => handleViewEvidence(item.chunk_id)}
          />
        )}
      />
      <GroundingOverlay
        visible={!!selectedChunk}
        chunk={selectedChunk}
        docHash={checklist.source_document_hash}
        onClose={() => setSelectedChunk(null)}
      />
    </SafeAreaView>
  );
}

function StatPill({
  count,
  color,
  label,
}: {
  count: number;
  color: string;
  label: string;
}) {
  return (
    <View style={[styles.pill, { borderColor: color }]}>
      <Text style={[styles.pillCount, { color }]}>{count}</Text>
      <Text style={styles.pillLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F172A',
  },
  list: {
    padding: 16,
    paddingBottom: 40,
  },
  header: {
    marginBottom: 16,
    gap: 12,
  },
  docName: {
    color: '#94A3B8',
    fontSize: 12,
    fontWeight: '500',
  },
  statsRow: {
    flexDirection: 'row',
    gap: 8,
  },
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    borderWidth: 1,
    borderRadius: 20,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  pillCount: {
    fontSize: 14,
    fontWeight: '700',
  },
  pillLabel: {
    color: '#94A3B8',
    fontSize: 12,
  },
  translateBtn: {
    backgroundColor: '#1E3A5F',
    borderRadius: 8,
    paddingVertical: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
  },
  translateBtnText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 16,
    padding: 24,
  },
  emptyText: {
    color: '#64748B',
    fontSize: 14,
    textAlign: 'center',
  },
  backBtn: {
    backgroundColor: '#1E293B',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
  },
  backBtnText: {
    color: '#94A3B8',
    fontSize: 14,
  },
});
