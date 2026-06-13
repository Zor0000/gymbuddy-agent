import { useEffect, useRef } from "react";
import cytoscape from "cytoscape";
import type { Graph } from "../api";

const COLORS: Record<string, string> = {
  exercise: "#00B388",
  muscle: "#018BFF",
  equipment: "#E2A23C",
};

export default function GraphPanel({ graph }: { graph: Graph | null }) {
  const ref = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const elements = graph
      ? [...graph.nodes, ...graph.edges].map((e) => ({ ...e }))
      : [];

    const cy = cytoscape({
      container: ref.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            "background-color": (n: any) => COLORS[n.data("type")] || "#888",
            label: "data(label)",
            color: "#dfe7f1",
            "font-size": 9,
            "text-wrap": "wrap",
            "text-max-width": "90px",
            "text-valign": "bottom",
            "text-margin-y": 4,
            width: (n: any) => (n.data("type") === "exercise" ? 26 : 34),
            height: (n: any) => (n.data("type") === "exercise" ? 26 : 34),
            "border-width": 2,
            "border-color": "#0f1b2d",
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "#33415c",
            "target-arrow-color": "#33415c",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": 7,
            color: "#6b7a90",
            "text-rotation": "autorotate",
          },
        },
      ],
      layout: {
        name: "concentric",
        // muscles/regions in the centre, equipment mid-ring, exercises on the outside
        concentric: (n: any) =>
          n.data("type") === "muscle" ? 3 : n.data("type") === "equipment" ? 2 : 1,
        levelWidth: () => 1,
        minNodeSpacing: 40,
        padding: 40,
        fit: true,
        animate: true,
      } as any,
    });
    cyRef.current = cy;
    // Ensure the graph is centred/zoomed to fit once layout settles.
    cy.one("layoutstop", () => cy.fit(undefined, 40));
    const onResize = () => cy.fit(undefined, 40);
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      cy.destroy();
    };
  }, [graph]);

  return (
    <div className="graph-wrap">
      <div className="graph-legend">
        <span><i style={{ background: COLORS.exercise }} /> Exercise</span>
        <span><i style={{ background: COLORS.muscle }} /> Muscle</span>
        <span><i style={{ background: COLORS.equipment }} /> Equipment</span>
      </div>
      <div ref={ref} className="graph-canvas" />
      {!graph && <div className="graph-empty">Ask a question to see the reasoning graph →</div>}
    </div>
  );
}
