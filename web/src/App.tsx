import { useEffect, useState } from "react";
import ChatPanel, { Message } from "./components/ChatPanel";
import GraphPanel from "./components/GraphPanel";
import { ask, health, Graph } from "./api";

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [graph, setGraph] = useState<Graph | null>(null);
  const [loading, setLoading] = useState(false);
  const [nodes, setNodes] = useState<number | null>(null);

  useEffect(() => {
    health().then((h) => setNodes(h.nodes ?? null));
  }, []);

  const handleAsk = async (q: string) => {
    // Build conversation history from prior turns (before adding the new one).
    const history = messages.map((m) => ({
      role: (m.role === "agent" ? "assistant" : "user") as "user" | "assistant",
      content: m.text,
    }));
    setMessages((m) => [...m, { role: "user", text: q }]);
    setLoading(true);
    try {
      const res = await ask(q, history);
      setMessages((m) => [
        ...m,
        { role: "agent", text: res.answer, exercises: res.exercises, tools: res.tools_used, latency: res.latency_ms },
      ]);
      setGraph(res.graph);
    } catch (e: any) {
      setMessages((m) => [...m, { role: "agent", text: `⚠️ ${e.message || "request failed"} — is the backend running on :8000?` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">🏋️</span>
          <div>
            <h1>GymBuddy</h1>
            <p>Graph-powered workout agent · Neo4j Aura + Groq</p>
          </div>
        </div>
        <div className="status">
          {nodes != null ? <span className="ok">● {nodes} nodes live</span> : <span className="off">● offline</span>}
        </div>
      </header>
      <main className="split">
        <section className="left"><ChatPanel messages={messages} loading={loading} onAsk={handleAsk} /></section>
        <section className="right"><GraphPanel graph={graph} /></section>
      </main>
    </div>
  );
}
