import React from 'react';
import { StyleSheet, View, Text, Modal, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import type { Chunk } from '../lib/api';

export function GroundingOverlay({
  chunk,
  visible,
  onClose,
}: {
  chunk: Chunk | null;
  visible: boolean;
  onClose: () => void;
}) {
  if (!chunk) return null;

  const [xmin, ymin, xmax, ymax] = chunk.grounding.box;

  // Visual constants for the mini-map
  const MAP_WIDTH = 260;
  const MAP_HEIGHT = 360;
  const SCALE_X = MAP_WIDTH / 1000;
  const SCALE_Y = MAP_HEIGHT / 1000;

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <View style={styles.modal}>
          <View style={styles.header}>
            <Ionicons name="scan-outline" size={20} color="#3B82F6" />
            <Text style={styles.title}>Visual Evidence</Text>
          </View>

          <View style={styles.infoRow}>
            <View style={styles.infoItem}>
              <Text style={styles.infoLabel}>PAGE</Text>
              <Text style={styles.infoValue}>{chunk.grounding.page}</Text>
            </View>
            <View style={styles.infoItem}>
              <Text style={styles.infoLabel}>CHUNK ID</Text>
              <Text style={styles.infoValue} numberOfLines={1}>
                {chunk.id.split('-')[0]}...
              </Text>
            </View>
          </View>

          <View style={[styles.mapContainer, { width: MAP_WIDTH, height: MAP_HEIGHT }]}>
            {/* The "Page" placeholder */}
            <View style={styles.pageBase}>
                <View style={styles.skeletonLine} />
                <View style={[styles.skeletonLine, { width: '80%' }]} />
                <View style={[styles.skeletonLine, { width: '90%' }]} />
                <View style={styles.skeletonLine} />
            </View>

            {/* The Bounding Box Highlight */}
            <View
              style={[
                styles.highlight,
                {
                  left: xmin * SCALE_X,
                  top: ymin * SCALE_Y,
                  width: Math.max((xmax - xmin) * SCALE_X, 10),
                  height: Math.max((ymax - ymin) * SCALE_Y, 10),
                },
              ]}
            >
                <View style={styles.cornerTL} />
                <View style={styles.cornerTR} />
                <View style={styles.cornerBL} />
                <View style={styles.cornerBR} />
            </View>
          </View>

          <Text style={styles.hint}>
            The highlighted area shows the exact location of this requirement in the source document.
          </Text>

          <TouchableOpacity style={styles.closeBtn} onPress={onClose}>
            <Text style={styles.closeBtnText}>Done</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  modal: {
    backgroundColor: '#1E293B',
    borderRadius: 20,
    padding: 24,
    width: '100%',
    maxWidth: 340,
    alignItems: 'center',
    gap: 20,
    borderWidth: 1,
    borderColor: '#334155',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  title: {
    color: '#F8FAFC',
    fontSize: 18,
    fontWeight: '700',
  },
  infoRow: {
    flexDirection: 'row',
    width: '100%',
    justifyContent: 'space-between',
    backgroundColor: '#0F172A',
    borderRadius: 12,
    padding: 12,
  },
  infoItem: {
    alignItems: 'center',
    flex: 1,
  },
  infoLabel: {
    color: '#64748B',
    fontSize: 9,
    fontWeight: '800',
    letterSpacing: 1,
    marginBottom: 4,
  },
  infoValue: {
    color: '#3B82F6',
    fontSize: 14,
    fontWeight: '700',
  },
  mapContainer: {
    backgroundColor: '#FFFFFF10',
    borderRadius: 8,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#334155',
  },
  pageBase: {
    flex: 1,
    padding: 20,
    gap: 12,
    opacity: 0.3,
  },
  skeletonLine: {
    height: 8,
    backgroundColor: '#94A3B8',
    borderRadius: 4,
    width: '100%',
  },
  highlight: {
    position: 'absolute',
    backgroundColor: '#3B82F630',
    borderWidth: 2,
    borderColor: '#3B82F6',
    borderRadius: 2,
  },
  cornerTL: {
    position: 'absolute',
    top: -4,
    left: -4,
    width: 8,
    height: 8,
    borderTopWidth: 2,
    borderLeftWidth: 2,
    borderColor: '#FFFFFF',
  },
  cornerTR: {
    position: 'absolute',
    top: -4,
    right: -4,
    width: 8,
    height: 8,
    borderTopWidth: 2,
    borderRightWidth: 2,
    borderColor: '#FFFFFF',
  },
  cornerBL: {
    position: 'absolute',
    bottom: -4,
    left: -4,
    width: 8,
    height: 8,
    borderBottomWidth: 2,
    borderLeftWidth: 2,
    borderColor: '#FFFFFF',
  },
  cornerBR: {
    position: 'absolute',
    bottom: -4,
    right: -4,
    width: 8,
    height: 8,
    borderBottomWidth: 2,
    borderRightWidth: 2,
    borderColor: '#FFFFFF',
  },
  hint: {
    color: '#64748B',
    fontSize: 12,
    textAlign: 'center',
    lineHeight: 18,
  },
  closeBtn: {
    backgroundColor: '#3B82F6',
    width: '100%',
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
  },
  closeBtnText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '700',
  },
});
