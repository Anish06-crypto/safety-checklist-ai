import { Ionicons } from '@expo/vector-icons';
import * as DocumentPicker from 'expo-document-picker';
import { router } from 'expo-router';
import React, { useState } from 'react';
import {
  ActivityIndicator,
  SafeAreaView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { generateChecklist } from '../lib/api';
import { useChecklistStore } from '../store/useChecklistStore';

export default function UploadScreen() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const setChecklist = useChecklistStore((s) => s.setChecklist);
  const reset = useChecklistStore((s) => s.reset);

  async function handlePick() {
    setError(null);
    reset();

    const result = await DocumentPicker.getDocumentAsync({
      type: 'application/pdf',
      copyToCacheDirectory: true,
    });

    if (result.canceled) return;

    const file = result.assets[0];
    setLoading(true);

    try {
      const checklist = await generateChecklist(file.uri, file.name);
      setChecklist(checklist);
      router.push('/checklist');
    } catch (e: any) {
      setError(e.message ?? 'Failed to generate checklist.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.inner}>
        <View style={styles.logoArea}>
          <View style={styles.iconCircle}>
            <Ionicons name="shield-checkmark" size={40} color="#3B82F6" />
          </View>
          <Text style={styles.title}>InteCheck AI</Text>
          <Text style={styles.subtitle}>
            DROPS Inspection Checklist Generator
          </Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Upload Procedure Document</Text>
          <Text style={styles.cardBody}>
            Select a DROPS safety procedure PDF to automatically generate a
            structured inspection checklist.
          </Text>

          {loading ? (
            <View style={styles.loadingArea}>
              <ActivityIndicator size="large" color="#3B82F6" />
              <Text style={styles.loadingText}>Analysing document…</Text>
              <Text style={styles.loadingSubtext}>
                Extracting checklist items via LLM
              </Text>
            </View>
          ) : (
            <TouchableOpacity style={styles.uploadBtn} onPress={handlePick}>
              <Ionicons name="document-attach-outline" size={20} color="#FFFFFF" />
              <Text style={styles.uploadBtnText}>Select PDF</Text>
            </TouchableOpacity>
          )}

          {error && (
            <View style={styles.errorBox}>
              <Ionicons name="warning-outline" size={16} color="#EF4444" />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}
        </View>

        <Text style={styles.footer}>
          Supports DROPS Recommended Practice documents
        </Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F172A',
  },
  inner: {
    flex: 1,
    paddingHorizontal: 24,
    justifyContent: 'center',
    gap: 32,
  },
  logoArea: {
    alignItems: 'center',
    gap: 10,
  },
  iconCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#1E3A5F',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 4,
  },
  title: {
    color: '#F8FAFC',
    fontSize: 28,
    fontWeight: '800',
    letterSpacing: -0.5,
  },
  subtitle: {
    color: '#64748B',
    fontSize: 14,
    textAlign: 'center',
  },
  card: {
    backgroundColor: '#1E293B',
    borderRadius: 16,
    padding: 24,
    gap: 14,
  },
  cardTitle: {
    color: '#F1F5F9',
    fontSize: 16,
    fontWeight: '700',
  },
  cardBody: {
    color: '#94A3B8',
    fontSize: 13,
    lineHeight: 20,
  },
  uploadBtn: {
    backgroundColor: '#2563EB',
    borderRadius: 10,
    paddingVertical: 14,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginTop: 4,
  },
  uploadBtnText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '600',
  },
  loadingArea: {
    alignItems: 'center',
    paddingVertical: 16,
    gap: 8,
  },
  loadingText: {
    color: '#94A3B8',
    fontSize: 14,
    fontWeight: '500',
    marginTop: 4,
  },
  loadingSubtext: {
    color: '#475569',
    fontSize: 12,
  },
  errorBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#2D1B1B',
    borderRadius: 8,
    padding: 12,
    gap: 8,
  },
  errorText: {
    color: '#EF4444',
    fontSize: 13,
    flex: 1,
    lineHeight: 18,
  },
  footer: {
    color: '#334155',
    fontSize: 12,
    textAlign: 'center',
  },
});
