const API = (import.meta.env.VITE_API_URL as string) || "http://127.0.0.1:8000";

export interface ExerciseCard {
  id: string;
  name: string;
  equipment: string | null;
  level: string | null;
  primary_muscles: string[];
  image_url: string | null;
}

export interface GraphNode {
  data: { id: string; label: string; type: string; equipment?: string; level?: string; image_url?: string };
}
export interface GraphEdge {
  data: { id: string; source: string; target: string; label: string };
}
export interface Graph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface AskResponse {
  answer: string;
  exercises: ExerciseCard[];
  graph: Graph;
  reasoning_path: any[];
  tools_used: string[];
  latency_ms: number;
}

export interface Turn {
  role: "user" | "assistant";
  content: string;
}

export async function ask(question: string, history: Turn[] = []): Promise<AskResponse> {
  const res = await fetch(`${API}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history }),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export async function health(): Promise<{ status: string; nodes?: number }> {
  try {
    const res = await fetch(`${API}/health`);
    return res.json();
  } catch {
    return { status: "error" };
  }
}
