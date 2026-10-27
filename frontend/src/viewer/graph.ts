import type { ElementDefinition } from "cytoscape";
import type { ModelNode } from "../api";

/** Extremos de cada enlace en el sentido en que viaja el dato. El atributo `type`
 * (Push/Pull, Select/Insert) invierte el sentido cuando el dato se lee. */
const LINK_ENDS: Record<string, [string, string, (n: ModelNode) => boolean]> = {
  LinkAPIToIoTDevice: ["linksIoTDevice", "linksAPI", () => false],
  LinkAppToAPI: ["linksAPI", "linksApp", () => false],
  LinkAppToService: ["linksApp", "linksService", () => false],
  LinkAppToTopic: ["linksApplication", "linksTopic", (n) => n.attrs.type === "Pull"],
  LinkServiceToTopic: ["linksService", "linksTopic", (n) => n.attrs.type === "Pull"],
  LinkServiceToDataTable: ["linkService", "linksDataTable", (n) => n.attrs.type === "Select"],
  LinkServiceToService: ["linksSourceService", "linksDestinationService", () => false],
  LinkServiceToAPI: ["linksAPI", "linksService", () => false],
};

export const FLOW_COLORS = ["#2f6fb3", "#c2410c", "#7c3aed", "#0f766e", "#be185d", "#a16207", "#4d7c0f"];

export const isA = (n: ModelNode, cls: string) => n.cls === cls || n.supertypes.includes(cls);

/** Categoría visual de cada elemento (inspirada en la notación de Monitor-IoT, RI-03). */
export function category(n: ModelNode): string | null {
  if (isA(n, "PhysicalEntity")) return isA(n, "IoTUser") ? "user" : "physical";
  if (n.cls === "CloudNode") return "cloud";
  if (n.cls === "FogNode") return "fog";
  if (n.cls === "IoTGateway") return "gateway";
  if (isA(n, "IoTDevice")) return "device";
  if (n.cls === "NetworkInterface") return "nic";
  if (n.cls === "DataBase") return "database";
  if (isA(n, "Resource")) return "resource";
  if (n.cls === "DataTable") return "table";
  if (n.cls === "Service") return "service";
  if (n.cls === "Topic") return "topic";
  if (n.cls === "Network") return "network";
  return null;
}

export interface Flow {
  id: string;
  name: string;
  color: string;
  links: string[];
}

export interface Graph {
  elements: ElementDefinition[];
  flows: Flow[];
  byId: Map<string, ModelNode>;
}

/** Las redes y las interfaces de red se muestran en la vista "Redes" (avance 3);
 * en la arquitectura solo estorban, como en el boceto de la ERS. */
const HIDDEN_IN_ARCHITECTURE = new Set(["network", "nic"]);

export function buildGraph(nodes: ModelNode[]): Graph {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const drawn = new Set(
    nodes.filter((n) => category(n) && !HIDDEN_IN_ARCHITECTURE.has(category(n)!)).map((n) => n.id),
  );
  const elements: ElementDefinition[] = [];

  const drawnParent = (n: ModelNode): string | undefined => {
    let p = n.parent ? byId.get(n.parent) : undefined;
    while (p && !drawn.has(p.id)) p = p.parent ? byId.get(p.parent) : undefined;
    return p?.id;
  };

  for (const n of nodes) {
    const cat = category(n);
    if (!cat || !drawn.has(n.id)) continue;
    let label = `${n.name || "(sin nombre)"} : ${n.cls}`;
    if (n.cls === "DataTable") {
      const cols = nodes.filter((c) => c.parent === n.id && c.cls === "DataColumn").map((c) => `▫ ${c.name}`);
      label = [label, ...cols].join("\n");
    }
    elements.push({ group: "nodes", data: { id: n.id, label, parent: drawnParent(n), cat } });
  }

  const flowNodes = nodes.filter((n) => n.cls === "DataFlow");
  const flows: Flow[] = flowNodes.map((f, i) => ({
    id: f.id,
    name: String(f.attrs.description || `Flujo ${i + 1}`),
    color: FLOW_COLORS[i % FLOW_COLORS.length],
    links: f.refs.isSupported ?? [],
  }));
  const flowOf = new Map<string, Flow>();
  flows.forEach((f) => f.links.forEach((l) => flowOf.set(l, f)));

  for (const n of nodes) {
    const ends = LINK_ENDS[n.cls];
    if (ends) {
      const [a, b, reversed] = ends;
      let src = n.refs[a]?.[0];
      let dst = n.refs[b]?.[0];
      if (!src || !dst || !drawn.has(src) || !drawn.has(dst)) continue;
      if (reversed(n)) [src, dst] = [dst, src];
      const flow = flowOf.get(n.id);
      elements.push({
        group: "edges",
        data: {
          id: n.id,
          source: src,
          target: dst,
          kind: "link",
          cls: n.cls,
          flow: flow?.id,
          color: flow?.color ?? "#64748b",
          label: typeof n.attrs.type === "string" ? n.attrs.type : "",
        },
      });
    }
    if (n.cls === "NetworkInterface") {
      for (const net of n.refs.connects ?? []) {
        if (drawn.has(net)) {
          elements.push({ group: "edges", data: { id: `${n.id}->${net}`, source: n.id, target: net, kind: "network" } });
        }
      }
    }
  }
  return { elements, flows, byId };
}
