import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

export default function RootLayout() {
  return (
    <>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: '#0F172A' },
          headerTintColor: '#F8FAFC',
          headerTitleStyle: { fontWeight: '700' },
          contentStyle: { backgroundColor: '#0F172A' },
        }}
      >
        <Stack.Screen name="index" options={{ title: 'InteCheck AI', headerShown: false }} />
        <Stack.Screen name="checklist" options={{ title: 'Inspection Checklist' }} />
        <Stack.Screen name="translate" options={{ title: 'Translate Checklist' }} />
      </Stack>
    </>
  );
}
