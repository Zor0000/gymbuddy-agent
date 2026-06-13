import { useEffect, useState } from "react";
import ChatPanel, { Message } from "./components/ChatPanel";
import { ask, health } from "./api";

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string>("connecting...");

  useEffect(() => {
    health().then((h) => {
      setStatus(h.status === "ok" ? "Aura Agent Connected" : "Missing API Keys");
    });
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
        { role: "agent", text: res.answer, latency: res.latency_ms },
      ]);
    } catch (e: any) {
      setMessages((m) => [...m, { role: "agent", text: `⚠️ ${e.message || "request failed"}` }]);
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
            <p>Powered by Neo4j Aura Agent</p>
          </div>
        </div>
        <div className="status">
          {status === "Aura Agent Connected" ? <span className="ok">● {status}</span> : <span className="off">● {status}</span>}
        </div>
      </header>
      <main className="single-column">
        <ChatPanel messages={messages} loading={loading} onAsk={handleAsk} />
      </main>
    </div>
  );
}
