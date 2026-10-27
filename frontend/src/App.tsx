import { useCallback, useEffect, useState } from "react";
import { api, streamEvents, type AgentEvent, type Health, type SessionData, type VersionData } from "./api";
import ChatPanel from "./components/ChatPanel";
import WorkflowPanel from "./components/WorkflowPanel";
import ViewerPanel from "./components/ViewerPanel";
import TopBar from "./components/TopBar";

export default function App() {
  const [session, setSession] = useState<SessionData | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastPrompt, setLastPrompt] = useState<string | null>(null);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [version, setVersion] = useState<VersionData | null>(null);

  useEffect(() => {
    api.createSession().then(setSession).catch((e) => setError(`No se pudo iniciar la sesión: ${e.message}`));
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  useEffect(() => {
    if (!session || selectedVersion === null) return;
    api.getVersion(session.id, selectedVersion).then(setVersion).catch((e) => setError(e.message));
  }, [session?.id, selectedVersion]); // eslint-disable-line react-hooks/exhaustive-deps

  const onEvent = useCallback((ev: AgentEvent) => {
    setSession((s) => {
      if (!s) return s;
      switch (ev.type) {
        case "step":
          return {
            ...s,
            steps: s.steps.map((st) =>
              st.id === ev.id ? { ...st, status: ev.status, detail: ev.detail, error: ev.error } : st,
            ),
          };
        case "message":
          return { ...s, messages: [...s.messages, { role: ev.role, content: ev.content, kind: ev.kind }] };
        default:
          return s;
      }
    });
    if (ev.type === "error") setError(ev.message);
  }, []);

  const refresh = useCallback(async (sid: string, select?: number) => {
    const fresh = await api.getSession(sid);
    setSession(fresh);
    const n = select ?? fresh.versions.at(-1)?.number;
    if (n) setSelectedVersion(n);
  }, []);

  const run = useCallback(
    async (url: string, body?: unknown, optimistic?: string) => {
      if (!session) return;
      setBusy(true);
      setError(null);
      if (optimistic) {
        setSession((s) => s && { ...s, messages: [...s.messages, { role: "user", content: optimistic }] });
      }
      let newVersion: number | undefined;
      try {
        await streamEvents(url, body, (ev) => {
          if (ev.type === "version") newVersion = ev.version.number;
          onEvent(ev);
        });
        await refresh(session.id, newVersion);
      } catch (e) {
        setError((e as Error).message);
        await refresh(session.id).catch(() => undefined);
      } finally {
        setBusy(false);
      }
    },
    [session, onEvent, refresh],
  );

  const send = (text: string) => {
    if (!session) return;
    setLastPrompt(text);
    run(`/api/sessions/${session.id}/chat`, { message: text }, text);
  };

  const loadExample = () => session && run(`/api/sessions/${session.id}/example`);

  const openXmi = async (file: File) => {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.uploadXmi(session.id, file);
      setSession(res.session);
      setSelectedVersion(res.version.number);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="app">
      <TopBar
        session={session}
        selectedVersion={selectedVersion}
        onSelectVersion={setSelectedVersion}
        current={version}
      />
      {error && (
        <div className="banner" role="alert">
          <span>{error}</span>
          <div className="banner-actions">
            {lastPrompt && !busy && (
              <button className="link" onClick={() => send(lastPrompt)}>
                Reintentar
              </button>
            )}
            <button className="link" onClick={() => setError(null)} aria-label="Cerrar aviso">
              Cerrar
            </button>
          </div>
        </div>
      )}
      <main className="panels">
        <ChatPanel
          messages={session?.messages ?? []}
          busy={busy || !session}
          health={health}
          onSend={send}
          onExample={loadExample}
          onOpenXmi={openXmi}
        />
        <WorkflowPanel steps={session?.steps ?? []} />
        <ViewerPanel version={version} />
      </main>
    </div>
  );
}
