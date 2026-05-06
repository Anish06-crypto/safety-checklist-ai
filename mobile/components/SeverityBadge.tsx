import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

const SEVERITY_CONFIG = {
  CRITICAL: { bg: '#DC2626', label: 'CRITICAL' },
  MAJOR: { bg: '#D97706', label: 'MAJOR' },
  MINOR: { bg: '#16A34A', label: 'MINOR' },
} as const;

type Severity = keyof typeof SEVERITY_CONFIG;

export function SeverityBadge({ severity }: { severity: Severity }) {
  const { bg, label } = SEVERITY_CONFIG[severity] ?? SEVERITY_CONFIG.MINOR;
  return (
    <View style={[styles.badge, { backgroundColor: bg }]}>
      <Text style={styles.text}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 4,
    alignSelf: 'flex-start',
  },
  text: {
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
});
