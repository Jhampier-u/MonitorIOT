import type { StylesheetStyle } from "cytoscape";

// Colores inspirados en la notación gráfica de Monitor-IoT (RI-03):
// entidades físicas en ocre, nodos de cómputo en azul, recursos en verde.
const CAT: Record<string, { bg: string; border: string }> = {
  physical: { bg: "#f6efd2", border: "#a8892a" },
  user: { bg: "#fbe7d6", border: "#b8682d" },
  cloud: { bg: "#dcecf6", border: "#2b5d8a" },
  fog: { bg: "#dcecf6", border: "#2b5d8a" },
  gateway: { bg: "#e3eefa", border: "#3d6fa6" },
  device: { bg: "#d6e9f5", border: "#2f6f9f" },
  database: { bg: "#d8eedd", border: "#2f7a4a" },
  resource: { bg: "#d8eedd", border: "#2f7a4a" },
  service: { bg: "#ffffff", border: "#2f7a4a" },
  topic: { bg: "#ffffff", border: "#2f7a4a" },
  table: { bg: "#ffffff", border: "#2f7a4a" },
  nic: { bg: "#eef1f5", border: "#8592a3" },
  network: { bg: "#ece6f7", border: "#6b4fa0" },
};

// Se tipa de forma laxa: @types/cytoscape no incluye "padding", que sí es válido.
export const STYLE = [
  {
    selector: "node",
    style: {
      label: "data(label)",
      "font-family": "Inter, Segoe UI, system-ui, sans-serif",
      "font-size": 11,
      color: "#1c2b45",
      "text-wrap": "wrap",
      "text-valign": "center",
      "text-halign": "center",
      shape: "round-rectangle",
      width: "label",
      height: "label",
      padding: "9px",
      "border-width": 1.5,
      "background-color": "#fff",
      "border-color": "#94a3b8",
    },
  },
  ...Object.entries(CAT).map(([cat, c]) => ({
    selector: `node[cat = "${cat}"]`,
    style: { "background-color": c.bg, "border-color": c.border },
  })),
  { selector: 'node[cat = "table"]', style: { "text-justification": "left", "font-size": 10 } },
  { selector: 'node[cat = "nic"]', style: { "font-size": 9, color: "#475569", padding: "5px" } },
  { selector: 'node[cat = "network"]', style: { shape: "round-tag", "font-weight": 600 } },
  {
    selector: ":parent",
    style: {
      "text-valign": "top",
      "text-halign": "center",
      "text-margin-y": -4,
      "font-weight": 600,
      "font-size": 12,
      padding: "16px",
      "border-width": 2,
    },
  },
  {
    selector: 'edge[kind = "link"]',
    style: {
      width: 2.2,
      "line-color": "data(color)",
      "target-arrow-color": "data(color)",
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
      "arrow-scale": 1.1,
      label: "data(label)",
      "font-size": 9,
      color: "#475569",
      "text-background-color": "#fff",
      "text-background-opacity": 0.85,
      "text-background-padding": "1px",
    },
  },
  {
    selector: 'edge[kind = "network"]',
    style: { width: 1, "line-style": "dashed", "line-color": "#a594c9", "curve-style": "bezier", "target-arrow-shape": "none" },
  },
  { selector: ":selected", style: { "border-color": "#f59e0b", "border-width": 3, "line-color": "#f59e0b" } },
  { selector: ".faded", style: { opacity: 0.18 } },
  { selector: "edge.hl", style: { width: 4, "z-index": 10 } },
] as unknown as StylesheetStyle[];
