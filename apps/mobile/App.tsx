import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { StatusBar } from "expo-status-bar";
import QRCode from "react-native-qrcode-svg";

const API_BASE = process.env.EXPO_PUBLIC_API_BASE || "https://codebase.flowlab.fun";

type Auth = {
  access_token: string;
  patient_id: string;
  uhid: string;
  display_name: string;
  qr_token: string;
};

type RecordItem = {
  id: string;
  resource_type: string;
  source_org_name: string | null;
  body: {
    medicationCodeableConcept?: { text?: string };
    dosageInstruction?: { text?: string }[];
  };
  created_at: string;
};

async function api(path: string, init?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail || res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export default function App() {
  const [mode, setMode] = useState<"login" | "register">("register");
  const [email, setEmail] = useState("synthetic.mobile@example.com");
  const [password, setPassword] = useState("synthet1c-pass");
  const [displayName, setDisplayName] = useState("Synthetic Mobile Patient");
  const [session, setSession] = useState<Auth | null>(null);
  const [records, setRecords] = useState<RecordItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) return;
    (async () => {
      try {
        const page = await api("/api/v1/patients/me/records", {
          headers: { Authorization: `Bearer ${session.access_token}` },
        });
        setRecords(page.items || []);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    })();
  }, [session]);

  async function onAuth() {
    setBusy(true);
    setError(null);
    try {
      const path =
        mode === "register"
          ? "/api/v1/auth/patient/register"
          : "/api/v1/auth/patient/login";
      const body =
        mode === "register"
          ? {
              email,
              password,
              display_name: displayName,
              otp: "123456",
            }
          : { email, password, otp: "123456" };
      const auth = await api(path, { method: "POST", body: JSON.stringify(body) });
      setSession(auth);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function refreshCard() {
    if (!session) return;
    setBusy(true);
    try {
      const card = await api("/api/v1/patients/me/card", {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      setSession({ ...session, qr_token: card.qr_token, uhid: card.uhid });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (!session) {
    return (
      <SafeAreaView style={styles.safe}>
        <StatusBar style="light" />
        <ScrollView contentContainerStyle={styles.pad}>
          <Text style={styles.kicker}>UNIVERSAL HEALTH QR</Text>
          <Text style={styles.title}>Patient app</Text>
          <Text style={styles.muted}>Synthetic only · OTP 123456 · {API_BASE}</Text>
          <View style={styles.tabs}>
            <Pressable
              style={[styles.tab, mode === "login" && styles.tabOn]}
              onPress={() => setMode("login")}
            >
              <Text style={styles.tabText}>Login</Text>
            </Pressable>
            <Pressable
              style={[styles.tab, mode === "register" && styles.tabOn]}
              onPress={() => setMode("register")}
            >
              <Text style={styles.tabText}>Register</Text>
            </Pressable>
          </View>
          {mode === "register" && (
            <TextInput
              style={styles.input}
              placeholder="Display name"
              value={displayName}
              onChangeText={setDisplayName}
            />
          )}
          <TextInput
            style={styles.input}
            autoCapitalize="none"
            keyboardType="email-address"
            placeholder="Email"
            value={email}
            onChangeText={setEmail}
          />
          <TextInput
            style={styles.input}
            secureTextEntry
            placeholder="Password"
            value={password}
            onChangeText={setPassword}
          />
          <Pressable style={styles.btn} onPress={onAuth} disabled={busy}>
            {busy ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.btnText}>
                {mode === "register" ? "Create account" : "Sign in"}
              </Text>
            )}
          </Pressable>
          {error && <Text style={styles.error}>{error}</Text>}
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="light" />
      <ScrollView contentContainerStyle={styles.pad}>
        <Text style={styles.kicker}>DIGITAL CARD</Text>
        <Text style={styles.title}>{session.display_name}</Text>
        <Text style={styles.mono}>{session.uhid}</Text>
        <View style={styles.qrBox}>
          <QRCode value={session.qr_token} size={200} />
        </View>
        <Text style={styles.muted}>Show this QR at participating demo hospitals.</Text>
        <Pressable style={styles.btn} onPress={refreshCard} disabled={busy}>
          <Text style={styles.btnText}>Rotate QR</Text>
        </Pressable>
        <Pressable
          style={[styles.btn, styles.btnGhost]}
          onPress={() => {
            setSession(null);
            setRecords([]);
          }}
        >
          <Text style={styles.btnGhostText}>Log out</Text>
        </Pressable>

        <Text style={[styles.title, { fontSize: 22, marginTop: 28 }]}>History</Text>
        {records.length === 0 ? (
          <Text style={styles.muted}>No synced prescriptions yet.</Text>
        ) : (
          records.map((r) => (
            <View key={r.id} style={styles.rx}>
              <Text style={styles.muted}>
                {r.source_org_name || "source?"} ·{" "}
                {new Date(r.created_at).toLocaleString()}
              </Text>
              <Text style={styles.rxTitle}>
                {r.body.medicationCodeableConcept?.text || r.resource_type}
              </Text>
              <Text style={styles.muted}>
                {r.body.dosageInstruction?.[0]?.text || "—"}
              </Text>
            </View>
          ))
        )}
        {error && <Text style={styles.error}>{error}</Text>}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#0f6b5c" },
  pad: { padding: 20, paddingBottom: 48 },
  kicker: {
    color: "#b7e4da",
    letterSpacing: 1.2,
    fontSize: 12,
    fontWeight: "700",
  },
  title: { color: "#fff", fontSize: 28, fontWeight: "700", marginTop: 6 },
  muted: { color: "#d5ebe6", marginTop: 8, lineHeight: 20 },
  mono: { color: "#fff", fontFamily: "monospace", marginTop: 6 },
  tabs: { flexDirection: "row", gap: 8, marginTop: 18, marginBottom: 8 },
  tab: {
    flex: 1,
    padding: 12,
    borderRadius: 12,
    backgroundColor: "rgba(255,255,255,0.12)",
    alignItems: "center",
  },
  tabOn: { backgroundColor: "#fff" },
  tabText: { color: "#0a4f44", fontWeight: "700" },
  input: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 14,
    marginTop: 10,
  },
  btn: {
    marginTop: 14,
    backgroundColor: "#0a4f44",
    borderRadius: 14,
    padding: 14,
    alignItems: "center",
  },
  btnText: { color: "#fff", fontWeight: "700" },
  btnGhost: {
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.35)",
  },
  btnGhostText: { color: "#fff", fontWeight: "600" },
  qrBox: {
    marginTop: 18,
    alignSelf: "center",
    backgroundColor: "#fff",
    padding: 16,
    borderRadius: 16,
  },
  rx: {
    marginTop: 12,
    padding: 12,
    borderRadius: 12,
    backgroundColor: "rgba(255,255,255,0.1)",
  },
  rxTitle: { color: "#fff", fontWeight: "700", marginTop: 4, fontSize: 16 },
  error: { color: "#ffd0d0", marginTop: 12 },
});
