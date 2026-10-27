import { useState } from "react";
import { api, type SessionData, type VersionData } from "../api";

interface Props {
  session: SessionData | null;
  selectedVersion: number | null;
  onSelectVersion: (n: number) => void;
  current: VersionData | null;
}

export default function TopBar({ session, selectedVersion, onSelectVersion, current }: Props) {
  const [ext, setExt] = useState<"MonitorIoT" | "xmi">("MonitorIoT");
  const versions = session?.versions ?? [];
  const meta = versions.find((v) => v.number === selectedVersion);

  const download = () => {
    if (!session || !meta) return;
    // RF-25: advertir antes de descargar un modelo que no pasó la validación
    if (!meta.valid) {
      const ok = window.confirm(
        `La versión ${meta.number} NO pasó la validación (${meta.errors} errores).\n` +
          "Puede que no se abra correctamente en Obeo Designer. ¿Descargarla de todos modos?",
      );
      if (!ok) return;
    }
    window.location.href = api.downloadUrl(session.id, meta.number, ext);
  };

  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-mark" aria-hidden />
        Asistente Monitor-IoT
      </div>
      <div className="case-name" title={session?.caseName}>
        Caso: {current?.summary?.name ? String(current.summary.name) : session?.caseName ?? "…"}
      </div>
      <div className="topbar-actions">
        {meta && (
          <span className={`badge ${meta.valid ? "ok" : "bad"}`} title="Resultado de la validación contra el metamodelo">
            {meta.valid ? "✓ Válido" : `✕ ${meta.errors} errores`}
          </span>
        )}
        <label className="sr-only" htmlFor="version-select">
          Versión del modelo
        </label>
        <select
          id="version-select"
          className="select"
          disabled={!versions.length}
          value={selectedVersion ?? ""}
          onChange={(e) => onSelectVersion(Number(e.target.value))}
        >
          {!versions.length && <option value="">Sin versiones</option>}
          {versions.map((v) => (
            <option key={v.number} value={v.number}>
              Versión {v.number} · {v.label}
            </option>
          ))}
        </select>
        <div className="download">
          <select
            className="select ext"
            aria-label="Extensión del archivo"
            value={ext}
            onChange={(e) => setExt(e.target.value as "MonitorIoT" | "xmi")}
          >
            <option value="MonitorIoT">.MonitorIoT</option>
            <option value="xmi">.xmi</option>
          </select>
          <button className="primary" disabled={!meta} onClick={download}>
            Descargar XMI
          </button>
        </div>
      </div>
    </header>
  );
}
