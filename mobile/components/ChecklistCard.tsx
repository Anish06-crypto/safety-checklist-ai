import React, { useState } from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { ChecklistItem } from '../lib/api';
import { SeverityBadge } from './SeverityBadge';

const isRTL = (lang: string) => lang === 'AR';

export function ChecklistCard({
  item,
  index,
  language = 'EN',
}: {
  item: ChecklistItem;
  index: number;
  language?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const rtl = isRTL(language);
  const textStyle = rtl ? styles.rtlText : undefined;

  return (
    <TouchableOpacity
      style={styles.card}
      onPress={() => setExpanded((v) => !v)}
      activeOpacity={0.85}
    >
      <View style={styles.header}>
        <View style={styles.indexBadge}>
          <Text style={styles.indexText}>{index + 1}</Text>
        </View>
        <SeverityBadge severity={item.severity} />
      </View>

      <Text style={[styles.action, textStyle]}>{item.action}</Text>

      <View style={styles.meta}>
        <Text style={styles.metaText}>{item.source_section}</Text>
        <Text style={styles.metaDot}>·</Text>
        <Text style={styles.metaText}>{item.examination_frequency}</Text>
      </View>

      {expanded && (
        <View style={styles.details}>
          <View style={styles.criteriaBlock}>
            <Text style={styles.criteriaLabel}>PASS</Text>
            <Text style={[styles.criteriaText, textStyle]}>{item.acceptance_criteria}</Text>
          </View>
          <View style={[styles.criteriaBlock, styles.failBlock]}>
            <Text style={[styles.criteriaLabel, styles.failLabel]}>FAIL / ESCALATE</Text>
            <Text style={[styles.criteriaText, textStyle]}>{item.failure_criteria}</Text>
          </View>
        </View>
      )}

      <Text style={styles.expandHint}>{expanded ? '▲ collapse' : '▼ details'}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#1E293B',
    borderRadius: 10,
    padding: 14,
    marginBottom: 10,
    borderLeftWidth: 0,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  indexBadge: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: '#334155',
    alignItems: 'center',
    justifyContent: 'center',
  },
  indexText: {
    color: '#94A3B8',
    fontSize: 11,
    fontWeight: '600',
  },
  action: {
    color: '#F1F5F9',
    fontSize: 14,
    fontWeight: '500',
    lineHeight: 20,
    marginBottom: 6,
  },
  meta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  metaText: {
    color: '#64748B',
    fontSize: 11,
  },
  metaDot: {
    color: '#475569',
    fontSize: 11,
  },
  details: {
    marginTop: 10,
    gap: 8,
  },
  criteriaBlock: {
    backgroundColor: '#0F172A',
    borderRadius: 6,
    padding: 10,
    borderLeftWidth: 3,
    borderLeftColor: '#16A34A',
  },
  failBlock: {
    borderLeftColor: '#DC2626',
  },
  criteriaLabel: {
    color: '#16A34A',
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 1,
    marginBottom: 4,
  },
  failLabel: {
    color: '#EF4444',
  },
  criteriaText: {
    color: '#CBD5E1',
    fontSize: 12,
    lineHeight: 18,
  },
  expandHint: {
    color: '#475569',
    fontSize: 10,
    marginTop: 8,
    textAlign: 'right',
  },
  rtlText: {
    textAlign: 'right',
    writingDirection: 'rtl',
  },
});
