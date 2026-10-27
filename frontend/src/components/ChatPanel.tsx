import { useEffect, useRef, useState, type ReactNode } from "react";
import type { Health, Message } from "../api";

interface Props {
  messages: Message[];
  busy: boolean;
  health: Health | null;
  onSend: (text: string) => void;
  onExample: () => void;
  onOpenXmi: (file: File) => void;
}

export default function ChatPanel({ messages, busy, health, onSend, onExample, onOpenXmi }: Props) {
  const [text, setText] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, busy]);

  const submit = () => {
    const t = text.trim();
    if (!t || busy) return;
    onSend(t);
    setText("");
  };

  return (
    <section className="panel chat" aria-label="Chat">
      <div className="panel-head">
        <h2>Chat</h2>
        {health && (
          <span className={`mode ${health.agentMode}`} title="Modelo de lenguaje del agente">
            {health.agentMode === "glm" ? `Agente: ${health.llm}` : "Modo demostración"}
          </span>
        )}
      </div>

      <div className="messages">
        {messages.length === 0 && (
          <div className="empty">
            <p className="empty-title">Describa su sistema IoT</p>
            <p>
              Cuéntele al agente qué quiere monitorear, con qué dispositivos y dónde se guardan los datos. El
              resultado es un modelo Monitor-IoT en formato XMI.
            </p>
            <div className="quick">
              <button onClick={onExample} disabled={busy}>
                Cargar caso de ejemplo
              </button>
              <button onClick={() => fileRef.current?.click()} disabled={busy}>
                Abrir un XMI existente
              </button>
            </div>
          </div>
        )}
        {messages.map((m, i) =>
          m.role === "system" ? (
            <div key={i} className="msg-system">
              {m.content}
            </div>
          ) : (
            <div key={i} className={`msg ${m.role}`}>
              {m.kind === "example" && <div className="msg-tag">Caso de ejemplo</div>}
              <Markdown text={m.content} />
            </div>
          ),
        )}
        {busy && messages.length > 0 && (
          <div className="msg assistant typing" aria-live="polite">
            <span />
            <span />
            <span />
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <button
          type="button"
          className="icon-btn"
          title="Abrir un XMI de Monitor-IoT (.MonitorIoT o .xmi)"
          aria-label="Adjuntar archivo"
          onClick={() => fileRef.current?.click()}
          disabled={busy}
        >
          +
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".MonitorIoT,.monitoriot,.xmi,.xml"
          hidden
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onOpenXmi(f);
            e.target.value = "";
          }}
        />
        <textarea
          value={text}
          placeholder="Escribe un mensaje…"
          rows={1}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
        />
        <button type="submit" className="send" disabled={busy || !text.trim()} aria-label="Enviar">
          ➤
        </button>
      </form>
    </section>
  );
}

/** Markdown mínimo: negritas, código en línea y listas con guion. */
function Markdown({ text }: { text: string }) {
  const out: ReactNode[] = [];
  let list: { depth: number; text: string }[] = [];
  const flush = () => {
    if (!list.length) return;
    out.push(
      <ul key={out.length}>
        {list.map((li, i) => (
          <li key={i} style={{ marginLeft: li.depth * 14 }}>
            {inline(li.text)}
          </li>
        ))}
      </ul>,
    );
    list = [];
  };
  for (const line of text.split("\n")) {
    const m = line.match(/^(\s*)[-*] (.*)$/);
    if (m) {
      list.push({ depth: Math.floor(m[1].length / 2), text: m[2] });
      continue;
    }
    flush();
    if (line.trim()) out.push(<p key={out.length}>{inline(line)}</p>);
  }
  flush();
  return <>{out}</>;
}

function inline(s: string): ReactNode[] {
  return s.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`")) return <code key={i}>{part.slice(1, -1)}</code>;
    return part;
  });
}
