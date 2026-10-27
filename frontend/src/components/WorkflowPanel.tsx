import { useState } from "react";
import type { Step, StepStatus } from "../api";

const STATUS_LABEL: Record<StepStatus, string> = {
  pending: "Pendiente",
  running: "En curso",
  completed: "Completado",
  error: "Con error",
};

export default function WorkflowPanel({ steps }: { steps: Step[] }) {
  return (
    <section className="panel workflow" aria-label="Workflow del agente">
      <div className="panel-head">
        <h2>Workflow</h2>
      </div>
      <ol className="steps">
        {steps.map((s) => (
          <StepItem key={s.id} step={s} />
        ))}
      </ol>
      <p className="legend">
        <span className="legend-swatch" /> Actividades del proceso de diseño de Monitor-IoT
      </p>
    </section>
  );
}

function StepItem({ step }: { step: Step }) {
  const [open, setOpen] = useState(false);
  const d = step.detail;
  const hasItems = !!d?.items && Object.keys(d.items).length > 0;
  return (
    <li className={`step ${step.status} ${step.activity ? "activity" : ""}`}>
      <StatusIcon status={step.status} />
      <div className="step-body">
        <div className="step-title">
          {step.id}. {step.title}
          {step.activity && <span className="activity-tag">Actividad {step.activity}</span>}
        </div>
        <div className="step-status">{STATUS_LABEL[step.status]}</div>
        {step.status === "pending" && <div className="step-desc">{step.description}</div>}
        {step.error && <div className="step-error">{step.error}</div>}
        {d && (d.headline || d.text) && (
          <div className="step-detail">
            <div>{d.headline ?? d.text}</div>
            {hasItems && (
              <button className="link" onClick={() => setOpen(!open)} aria-expanded={open}>
                {open ? "Ocultar detalle ▴" : "Ver detalle ▾"}
              </button>
            )}
            {open && hasItems && (
              <dl>
                {Object.entries(d.items!).map(([k, v]) => (
                  <div key={k}>
                    <dt>{k}</dt>
                    <dd>{v.length ? v.join(", ") : "—"}</dd>
                  </div>
                ))}
              </dl>
            )}
          </div>
        )}
      </div>
    </li>
  );
}

function StatusIcon({ status }: { status: StepStatus }) {
  return (
    <span className={`status-icon ${status}`} aria-hidden>
      {status === "completed" ? "✓" : status === "error" ? "!" : status === "running" ? "" : ""}
    </span>
  );
}
