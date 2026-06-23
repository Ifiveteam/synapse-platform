import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatNodeType } from "@/lib/profiler/graph-data";
import type { GraphViewData } from "@/api/types/profiler";

interface GraphListViewProps {
  graph: GraphViewData;
}

export function GraphListView({ graph }: GraphListViewProps) {
  const topNodes = graph.nodes
    .slice()
    .sort((a, b) => b.weight - a.weight)
    .slice(0, 20);

  const topEdges = graph.edges
    .slice()
    .sort((a, b) => b.weight - a.weight)
    .slice(0, 20);

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">노드 ({graph.nodes.length})</CardTitle>
          <CardDescription>weight 상위 노드</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="max-h-96 space-y-2 overflow-y-auto text-sm">
            {topNodes.map((node) => (
              <li
                key={node.id}
                className="flex items-center justify-between gap-2 border-b pb-2 last:border-0"
              >
                <span className="min-w-0 truncate">
                  <span className="text-muted-foreground mr-2 text-xs">
                    {formatNodeType(node.type)}
                  </span>
                  {node.label}
                </span>
                <span className="font-mono text-xs">{node.weight.toFixed(0)}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">엣지 ({graph.edges.length})</CardTitle>
          <CardDescription>관계 · 가중치</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="max-h-96 space-y-2 overflow-y-auto text-xs">
            {topEdges.map((edge, idx) => (
              <li key={`${edge.source}-${edge.target}-${idx}`} className="border-b pb-2">
                <p className="text-muted-foreground">{edge.relation}</p>
                <p className="truncate font-mono">
                  {edge.source.split(":").pop()} ↔ {edge.target.split(":").pop()}
                </p>
                <p className="text-muted-foreground">weight {edge.weight.toFixed(0)}</p>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
