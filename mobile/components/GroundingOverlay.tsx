import React from 'react';
import { StyleSheet, View, Text, Modal, TouchableOpacity, Image } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { API_BASE, type Chunk } from '../lib/api';

export function GroundingOverlay({
  chunk,
  docHash,
  visible,
  onClose,
}: {
  chunk: Chunk | null;
  docHash: string;
  visible: boolean;
  onClose: () => void;
}) {
  // Defensive check
  if (!visible || !chunk || !chunk.grounding || !chunk.grounding.box) {
    return null;
  }

  const box = chunk.grounding.box;
  let xmin, ymin, xmax, ymax;

  if (Array.isArray(box) && box.length === 4) {
    [xmin, ymin, xmax, ymax] = box;
  } else if (typeof box === 'object' && box !== null) {
    xmin = (box as any).left * 1000;
    ymin = (box as any).top * 1000;
    xmax = (box as any).right * 1000;
    ymax = (box as any).bottom * 1000;
  } else {
    return null;
  }

  // URL for the actual document crop image from backend
  const imageUrl = `${API_BASE}/api/extractions/${docHash}/chunks/${chunk.id}/image`;

  return (
    <Modal
      visible={visible}
      transparent={true}
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <View style={styles.modal}>
          <View style={styles.header}>
            <Ionicons name="eye-outline" size={24} color="#3B82F6" />
            <Text style={styles.title}>Visual Evidence</Text>
          </View>

          <View style={styles.infoRow}>
            <View style={styles.infoItem}>
              <Text style={styles.infoLabel}>PAGE</Text>
              <Text style={styles.infoValue}>{chunk.grounding.page}</Text>
            </View>
            <View style={styles.separator} />
            <View style={styles.infoItem}>
              <Text style={styles.infoLabel}>LOCATION</Text>
              <Text style={styles.infoValue}>X:{Math.round(xmin)} Y:{Math.round(ymin)}</Text>
            </View>
          </View>

          <View style={styles.mapContainer}>
            {/* The Actual Document Crop Image */}
            <Image 
              source={{ uri: imageUrl }} 
              style={styles.sourceImage}
              resizeMode="contain"
            />
            
            {/* Scanned Border overlay */}
            <View style={styles.scanBorder}>
                <View style={styles.cornerTL} />
                <View style={styles.cornerTR} />
                <View style={styles.cornerBL} />
                <View style={styles.cornerBR} />
            </View>
          </View>

          <Text style={styles.hint}>
            This image is a direct crop from the source PDF, proving the AI extracted this item accurately.
          </Text>

          <TouchableOpacity style={styles.closeBtn} onPress={onClose}>
            <Text style={styles.closeBtnText}>Dismiss</Text>
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
  },
  modal: {
    backgroundColor: '#1E293B',
    borderRadius: 24,
    padding: 24,
    width: '92%',
    maxWidth: 360,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#334155',
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.5,
    shadowRadius: 15,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  title: {
    color: '#F8FAFC',
    fontSize: 20,
    fontWeight: '700',
    marginLeft: 10,
  },
  infoRow: {
    flexDirection: 'row',
    width: '100%',
    justifyContent: 'space-between',
    backgroundColor: '#0F172A',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    alignItems: 'center',
  },
  infoItem: {
    alignItems: 'center',
    flex: 1,
  },
  separator: {
    width: 1,
    height: 20,
    backgroundColor: '#334155',
  },
  infoLabel: {
    color: '#64748B',
    fontSize: 10,
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
    width: '100%',
    aspectRatio: 1.2,
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#334155',
    marginBottom: 20,
    position: 'relative',
  },
  sourceImage: {
    width: '100%',
    height: '100%',
  },
  scanBorder: {
    ...StyleSheet.absoluteFillObject,
    borderWidth: 1,
    borderColor: 'rgba(59, 130, 246, 0.3)',
    borderRadius: 12,
  },
  cornerTL: {
    position: 'absolute',
    top: 10,
    left: 10,
    width: 20,
    height: 20,
    borderTopWidth: 3,
    borderLeftWidth: 3,
    borderColor: '#3B82F6',
  },
  cornerTR: {
    position: 'absolute',
    top: 10,
    right: 10,
    width: 20,
    height: 20,
    borderTopWidth: 3,
    borderRightWidth: 3,
    borderColor: '#3B82F6',
  },
  cornerBL: {
    position: 'absolute',
    bottom: 10,
    left: 10,
    width: 20,
    height: 20,
    borderBottomWidth: 3,
    borderLeftWidth: 3,
    borderColor: '#3B82F6',
  },
  cornerBR: {
    position: 'absolute',
    bottom: 10,
    right: 10,
    width: 20,
    height: 20,
    borderBottomWidth: 3,
    borderRightWidth: 3,
    borderColor: '#3B82F6',
  },
  hint: {
    color: '#94A3B8',
    fontSize: 13,
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 24,
    paddingHorizontal: 10,
  },
  closeBtn: {
    backgroundColor: '#3B82F6',
    width: '100%',
    paddingVertical: 16,
    borderRadius: 14,
    alignItems: 'center',
  },
  closeBtnText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
});
