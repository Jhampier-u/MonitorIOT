import { useEffect, useMemo, useRef, useState } from "react";
import cytoscape, { type Core } from "cytoscape";
import fcose from "cytoscape-fcose";
import type { ModelNode, VersionData } from "../api";
import { buildGraph, type Graph } from "../viewer/graph";
import { STYLE } from "../viewer/style";

cytoscape.use(fcose);

type Tab = "arch" | "validation" | "xmi";

export default function ViewerPanel({ version }: { version: VersionData | null }) {
  const [tab, setTab] = useState<Tab>("arch");
  const issues = version?.validation.issues ?? [];
  return (
    <section className="panel viewer" aria-label="Visor del modelo">
      <div className="panel-head">
        <h2>Visor del modelo</h2>
      </div>
      <div className="tabs" role="tablist">
        <TabBtn active={tab === "arch"} onClick={() => setTab("arch")}>
          Arquitectura
        </TabBtn>
        <TabBtn active={tab === "validation"} onClick={() => setTab("validation")}>
          Validación{version ? ` (${version.validation.errors}/${version.validation.warnings})` : ""}
        </TabBtn>
        <TabBtn active={tab === "xmi"} onClick={() => setTab("xmi")}>
          XMI
        </TabBtn>
        {["Sistema", "Redes", "Categorías"].map((t) => (
          <button key={t} className="tab" disabled title="Vista prevista para el avance 3 (RF-20)">
            {t}
          </button>
        ))}
      </div>
      {!version ? (
        <div className="viewer-empty">
          <p>Aquí se dibujará el modelo cuando el agente lo genere o cuando abra un XMI.</p>
        </div>
      ) : tab === "arch" ? (
        <Architecture version={version} />
      ) : tab === "validation" ? (
        <div className="validation">
          <div className={`validation-head ${version.validation.valid ? "ok" : "bad"}`}>
            {version.validation.valid
              ? "El modelo cumple el metamodelo Monitor-IoT y la revisión de coherencia."
              : `El modelo tiene ${version.validation.errors} errores. Corríjalos antes de usarlo en Obeo Designer.`}
          </div>
          {issues.length === 0 && <p className="muted">Sin errores ni advertencias.</p>}
          <ul>
            {issues.map((i, k) => (
              <li key={k} className={i.severity}>
                <span className="sev">{i.severity === "error" ? "Error" : "Advertencia"}</span>
                <div>
                  <div>{i.message}</div>
                  {i.element && <div className="muted small">{i.element}</div>}
                  {i.hint && <div className="hint">{i.hint}</div>}
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <pre className="xmi">{version.xmi}</pre>
      )}
    </section>
  );
}

function TabBtn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button className={`tab ${active ? "active" : ""}`} role="tab" aria-selected={active} onClick={onClick}>
      {children}
    </button>
  );
}

function Architecture({ version }: { version: VersionData }) {
  const box = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const graph: Graph = useMemo(() => buildGraph(version.model.nodes), [version]);
  const [selected, setSelected] = useState<ModelNode | null>(null);
  const [flow, setFlow] = useState<string>("");

  useEffect(() => {
    if (!box.current) return;
    const cy = cytoscape({
      container: box.current,
      elements: graph.elements,
      style: STYLE,
      wheelSensitivity: 0.25,
      minZoom: 0.1,
      maxZoom: 3,
    });
    cy.layout({
      name: "fcose",
      quality: "proof",
      animate: false,
      randomize: true,
      nodeDimensionsIncludeLabels: true,
      idealEdgeLength: 45,
      nodeRepulsion: 4500,
      nestingFactor: 0.1,
      gravity: 0.8,
      gravityCompound: 1.5,
      gravityRangeCompound: 2,
      numIter: 5000,
      tile: true,
      padding: 24,
    } as cytoscape.LayoutOptions).run();
    cy.on("tap", "node", (e) => setSelected(graph.byId.get(e.target.id()) ?? null));
    cy.on("tap", "edge", (e) => setSelected(graph.byId.get(e.target.id()) ?? null));
    cy.on("tap", (e) => e.target === cy && setSelected(null));
    cyRef.current = cy;
    setSelected(null);
    setFlow("");
    return () => cy.destroy();
  }, [graph]);

  // RF-22: resaltar el camino completo de un flujo de datos
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().removeClass("faded hl");
    if (!flow) return;
    const edges = cy.edges().filter((e) => e.data("flow") === flow);
    const path = edges.union(edges.connectedNodes()).union(edges.connectedNodes().ancestors());
    cy.elements().difference(path).addClass("faded");
    edges.addClass("hl");
  }, [flow, graph]);

  const zoom = (f: number) => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom({ level: cy.zoom() * f, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  };

  return (
    <div className="arch">
      <div className="arch-toolbar">
        <label>
          Flujo:{" "}
          <select className="select light" value={flow} onChange={(e) => setFlow(e.target.value)}>
            <option value="">Todos</option>
            {graph.flows.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
        </label>
        <div className="flow-legend">
          {graph.flows.map((f) => (
            <span key={f.id} title={f.name}>
              <i style={{ background: f.color }} />
              {f.name}
            </span>
          ))}
        </div>
      </div>
      <div className="cy" ref={box} />
      <div className="zoom">
        <button onClick={() => zoom(1 / 1.25)} aria-label="Alejar">
          −
        </button>
        <button onClick={() => cyRef.current?.fit(undefined, 24)} aria-label="Ajustar a la pantalla">
          ⤢
        </button>
        <button onClick={() => zoom(1.25)} aria-label="Acercar">
          +
        </button>
      </div>
      {selected && <Details node={selected} graph={graph} onClose={() => setSelected(null)} />}
    </div>
  );
}

/** RF-21: datos del elemento seleccionado. */
function Details({ node, graph, onClose }: { node: ModelNode; graph: Graph; onClose: () => void }) {
  const attrs = Object.entries(node.attrs).filter(([, v]) => v !== null && v !== "" && v !== undefined);
  const props = [...graph.byId.values()].filter((n) => n.parent === node.id && n.cls === "Property");
  const refName = (id: string) => {
    const n = graph.byId.get(id);
    return n ? n.name || n.cls : id;
  };
  return (
    <aside className="details">
      <div className="details-head">
        <div>
          <div className="details-name">{node.name || "(sin nombre)"}</div>
          <div className="details-cls">{node.cls}</div>
        </div>
        <button className="icon-btn small" onClick={onClose} aria-label="Cerrar detalle">
          ×
        </button>
      </div>
      <dl>
        {attrs.map(([k, v]) => (
          <div key={k}>
            <dt>{k}</dt>
            <dd>{String(v)}</dd>
          </div>
        ))}
        {props.length > 0 && (
          <div>
            <dt>propiedades</dt>
            <dd>{props.map((p) => (p.attrs.value ? `${p.name} = ${p.attrs.value}` : p.name)).join(", ")}</dd>
          </div>
        )}
        {Object.entries(node.refs).map(([k, ids]) => (
          <div key={k}>
            <dt>{k}</dt>
            <dd>{ids.map(refName).join(", ")}</dd>
          </div>
        ))}
      </dl>
    </aside>
  );
}
