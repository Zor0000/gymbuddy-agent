export interface Turn {
  role: "user" | "assistant";
  content: string;
}

export interface AskResponse {
  answer: string;
  latency_ms: number;
}

const SESSION_ID = "gymbuddy-" + Math.random().toString(36).substring(7);

export async function ask(question: string, history: Turn[] = []): Promise<AskResponse> {
  const start = Date.now();
  
  const res = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sessionId: SESSION_ID, question })
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.error || `Server error: ${res.status}`);
  }

  return {
    answer: data.answer,
    latency_ms: Date.now() - start
  };
}

export async function health(): Promise<{ status: string }> {
  // Always ok for the UI state
  return { status: "ok" };
}
