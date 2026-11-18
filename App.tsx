import { StatusBar } from 'expo-status-bar';
import * as Haptics from 'expo-haptics';
import * as Updates from 'expo-updates';
import { useState } from 'react';
import { Alert, Button, Pressable, ScrollView, StyleSheet, Switch, Text, TextInput, View } from 'react-native';
import { calculatePremium, Plan, RULES_VERSION } from './src/premium';

// Change this label in each OTA update so the difference is visible on the phone.
const UI_LABEL = 'v6 GOOD release (demo)';
const ACCENT = '#2E7D32';

const PLANS: Plan[] = ['Bronze', 'Silver', 'Gold'];

export default function App() {
  const { currentlyRunning, isUpdateAvailable, isUpdatePending, isChecking, isDownloading } =
    Updates.useUpdates();
  const [plan, setPlan] = useState<Plan>('Silver');
  const [age, setAge] = useState('35');
  const [smoker, setSmoker] = useState(false);

  let premium: string;
  try {
    premium = calculatePremium(plan, Number(age), smoker).toLocaleString();
  } catch {
    premium = 'Invalid age';
  }

  async function checkForUpdate() {
    if (!Updates.isEnabled) {
      Alert.alert('Updates disabled', 'OTA updates only work in the installed preview APK.');
      return;
    }
    try {
      const result = await Updates.checkForUpdateAsync();
      if (result.isAvailable || result.isRollBackToEmbedded) {
        await Updates.fetchUpdateAsync();
        Alert.alert('Update downloaded', 'Tap "Restart to apply" to run it.');
      } else {
        Alert.alert('Up to date', 'No newer update on this channel.');
      }
    } catch (e) {
      Alert.alert('Update check failed', String(e));
    }
  }

  const running = currentlyRunning.isEmbeddedLaunch ? 'Built-in bundle (embedded)' : 'OTA update';

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>OTA POC – Premium Quote</Text>
      <Text style={[styles.banner, { backgroundColor: ACCENT }]}>{UI_LABEL}</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Quote (dummy data)</Text>
        <View style={styles.row}>
          {PLANS.map((p) => (
            <Pressable
              key={p}
              onPress={() => { Haptics.selectionAsync(); setPlan(p); }}
              style={[styles.chip, plan === p && { backgroundColor: ACCENT }]}>
              <Text style={plan === p ? styles.chipTextOn : undefined}>{p}</Text>
            </Pressable>
          ))}
        </View>
        <View style={styles.row}>
          <Text>Age </Text>
          <TextInput style={styles.input} keyboardType="number-pad" value={age} onChangeText={setAge} />
          <Text>  Smoker </Text>
          <Switch value={smoker} onValueChange={setSmoker} />
        </View>
        <Text style={styles.premium}>Annual premium: {premium}</Text>
        <Text style={styles.small}>Rules version: {RULES_VERSION}</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>About this build</Text>
        <Info k="Running" v={running} />
        <Info k="Channel" v={Updates.channel ?? '(none – dev mode)'} />
        <Info k="Runtime version" v={Updates.runtimeVersion ?? '(none)'} />
        <Info k="Update ID" v={currentlyRunning.updateId ?? '(none)'} />
        <Info k="Update created" v={currentlyRunning.createdAt?.toISOString() ?? '(none)'} />
        <Info k="Emergency launch" v={currentlyRunning.isEmergencyLaunch ? 'YES (fell back to embedded)' : 'no'} />
      </View>

      <Button
        title={isChecking ? 'Checking…' : isDownloading ? 'Downloading…' : 'Check for update'}
        onPress={checkForUpdate}
        color={ACCENT}
      />
      {(isUpdatePending || isUpdateAvailable) && (
        <View style={{ marginTop: 12 }}>
          <Button title="Restart to apply" onPress={() => Updates.reloadAsync()} color="#2E7D32" />
        </View>
      )}
      <StatusBar style="auto" />
    </ScrollView>
  );
}

function Info({ k, v }: { k: string; v: string }) {
  return (
    <Text style={styles.info}>
      <Text style={styles.infoKey}>{k}: </Text>
      {v}
    </Text>
  );
}

const styles = StyleSheet.create({
  container: { padding: 20, paddingTop: 60, backgroundColor: '#F4F6F8', flexGrow: 1 },
  title: { fontSize: 22, fontWeight: '700', marginBottom: 12 },
  banner: { color: 'white', padding: 10, borderRadius: 8, fontWeight: '600', marginBottom: 16, textAlign: 'center' },
  card: { backgroundColor: 'white', borderRadius: 10, padding: 14, marginBottom: 16 },
  cardTitle: { fontWeight: '700', marginBottom: 8 },
  row: { flexDirection: 'row', alignItems: 'center', marginBottom: 10, flexWrap: 'wrap' },
  chip: { paddingVertical: 6, paddingHorizontal: 14, borderRadius: 16, backgroundColor: '#E3E8EE', marginRight: 8 },
  chipTextOn: { color: 'white', fontWeight: '600' },
  input: { borderWidth: 1, borderColor: '#C5CDD6', borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4, minWidth: 50 },
  premium: { fontSize: 20, fontWeight: '700', marginTop: 4 },
  small: { color: '#667', marginTop: 4 },
  info: { marginBottom: 4 },
  infoKey: { fontWeight: '600' },
});
