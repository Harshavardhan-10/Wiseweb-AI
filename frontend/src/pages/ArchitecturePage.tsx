import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PageLoader } from "@/components/ui/spinner";
import { apiClient } from "@/lib/api";
import { errMessage } from "@/lib/utils";
import type { ArchitectureNode } from "@/lib/types";

const NODE_COLORS: Record<string, string> = {
  page: "#334155",
  domain: "#0f172a",
  technology: "#7c3aed",
  platform: "#0284c7",
  cms: "#0284c7",
  framework: "#0d9488",
  library: "#0891b2",
  hosting: "#d97706",
  server: "#b45309",
  resource: "#059669",
  script: "#e11d48",
  stylesheet: "#db2777",
  external: "#64748b",
};

function nodeColor(nodeType: string): string {
  return NODE_COLORS[nodeType.toLowerCase()] ?? "#64748b";
}

interface Layered {
  id: number;
  layer: number;
  index: number;
}

function computeLayout(nodes: ArchitectureNode[], edges: { source_node_id: number; target_node_id: number }[]) {
  const layerBy = new Map<number, number>();
  const out = new Map<number, number[]>();
  for (const n of nodes) layerBy.set(n.id, 0);
  for (const e of edges) {
    if (!out.has(e.source_node_id)) out.set(e.source_node_id, []);
    out.get(e.source_node_id)!.push(e.target_node_id);
  }
  let changed = true;
  let guard = 0;
  while (changed && guard < 50) {
    changed = false;
    guard++;
    for (const e of edges) {
      const cur = layerBy.get(e.target_node_id) ?? 0;
      const next = (layerBy.get(e.source_node_id) ?? 0) + 1;
      if (next > cur) {
        layerBy.set(e.target_node_id, next);
        changed = true;
      }
    }
  }
  const byLayer = new Map<number, ArchitectureNode[]>();
  for (const n of nodes) {
    const l = layerBy.get(n.id) ?? 0;
    if (!byLayer.has(l)) byLayer.set(l, []);
    byLayer.get(l)!.push(n);
  }
  const result: Layered[] = [];
  for (const [layer, layerNodes] of byLayer) {
    layerNodes.forEach((n, index) => result.push({ id: n.id, layer, index }));
  }
  return result;
}

export function ArchitecturePage() {
  const { scanId } = useParams();
  const id = Number(scanId);

  const arch = useQuery({
    queryKey: ["architecture", id],
    queryFn: (ctx) => apiClient.architecture(id, ctx.signal),
    enabled: Number.isFinite(id),
  });

  const { nodes, edges } = useMemo(() => {
    if (!arch.data) return { nodes: [] as Node[], edges: [] as Edge[] };
    const layout = computeLayout(arch.data.nodes, arch.data.edges);
    const byId = new Map(arch.data.nodes.map((n) => [n.id, n]));
    const flowNodes: Node[] = layout.map(({ id: nodeId, layer, index }) => {
      const n = byId.get(nodeId)!;
      const color = nodeColor(n.node_type);
      return {
        id: String(nodeId),
        position: { x: layer * 260 + 20, y: index * 96 },
        data: {
          label: (
            <div className="flex flex-col items-center gap-1 px-2 py-1">
              <span className="text-sm font-semibold text-slate-800">{n.name}</span>
              {n.label && <span className="text-[10px] text-slate-500">{n.label}</span>}
            </div>
          ),
        },
        style: {
          border: `1.5px solid ${color}`,
          borderRadius: 8,
          backgroundColor: `${color}12`,
          color,
        },
      };
    });
    const flowEdges: Edge[] = arch.data.edges.map((e) => ({
      id: String(e.id),
      source: String(e.source_node_id),
      target: String(e.target_node_id),
      label: e.relationship,
      animated: true,
      style: { stroke: "#94a3b8", strokeWidth: 1.5 },
      labelStyle: { fill: "#64748b", fontSize: 10 },
    }));
    return { nodes: flowNodes, edges: flowEdges };
  }, [arch.data]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Architecture</h1>
          <p className="mt-1 text-sm text-slate-500">
            Detected technologies, resources, and how they relate.
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline" size="sm">
            <Link to={`/scans/${id}/overview`}>Overview</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to={`/scans/${id}/findings`}>Findings</Link>
          </Button>
        </div>
      </div>

      {arch.isLoading && <PageLoader label="Mapping architecture…" />}

      {arch.isError && (
        <Alert variant="error" title="Failed to load architecture">
          {errMessage(arch.error)}
        </Alert>
      )}

      {arch.data && arch.data.nodes.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-sm text-slate-500">
            No architecture nodes were detected in this scan.
          </CardContent>
        </Card>
      )}

      {arch.data && arch.data.nodes.length > 0 && (
        <Card>
          <CardContent className="h-[560px] p-0">
            <ReactFlow nodes={nodes} edges={edges} fitView minZoom={0.2}>
              <Background color="#e2e8f0" gap={20} />
              <Controls />
              <MiniMap pannable zoomable className="bg-white!" />
            </ReactFlow>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
