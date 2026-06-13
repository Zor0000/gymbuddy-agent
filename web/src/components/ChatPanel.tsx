import { useEffect, useRef, useState } from "react";

export interface Message {
  role: "user" | "agent";
  text: string;
  latency?: number;
}

const EXAMPLES = [
  "Bench is taken — alternative with dumbbells?",
  "Build me a beginner push day at home with dumbbells",
  "What can I train with kettlebells for my legs?",
  "Give me an easier version of pistol squats",
  "Something like a plank but harder",
];

export default function ChatPanel({
  messages,
  loading,
  onAsk,
}: {
  messages: Message[];
  loading: boolean;
  onAsk: (q: string) => void;
}) {
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const submit = (q: string) => {
    const text = q.trim();
    if (!text || loading) return;
    onAsk(text);
    setInput("");
  };

  return (
    <div className="chat">
      <div className="messages">
        {messages.length === 0 && (
          <div className="examples">
            <p>Try one:</p>
            {EXAMPLES.map((e) => (
              <button key={e} className="chip" onClick={() => submit(e)}>
                {e}
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div className="bubble" style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
            {m.latency && (
              <div className="trace">
                ⚡ Response in {m.latency} ms
              </div>
            )}
          </div>
        ))}
        {loading && <div className="msg agent"><div className="bubble typing">GymBuddy is reasoning…</div></div>}
        <div ref={endRef} />
      </div>

      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          submit(input);
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about exercises, swaps, routines…"
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Ask
        </button>
      </form>
    </div>
  );
}
