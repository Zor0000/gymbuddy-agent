const API_URL = import.meta.env.VITE_AURA_AGENT_URL as string;
const API_TOKEN = import.meta.env.VITE_AURA_AGENT_TOKEN as string;

export interface Turn {
  role: "user" | "assistant";
  content: string;
}

export interface AskResponse {
  answer: string;
  latency_ms: number;
}

export async function ask(question: string, history: Turn[] = []): Promise<AskResponse> {
  if (!API_URL || !API_TOKEN) {
    throw new Error("Missing VITE_AURA_AGENT_URL or VITE_AURA_AGENT_TOKEN in environment.");
  }

  const start = Date.now();
  
  const messages = [
    ...history,
    { role: "user", content: question }
  ];

  const res = await fetch(API_URL, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      "Authorization": `Bearer ${API_TOKEN}`
    },
    body: JSON.stringify({
      messages: messages,
      stream: false
    }),
  });

  if (!res.ok) {
    throw new Error(`Aura Agent API error: ${res.status}`);
  }

  const data = await res.json();
  const answer = data.choices?.[0]?.message?.content || "No response received.";

  return {
    answer,
    latency_ms: Date.now() - start
  };
}

export async function health(): Promise<{ status: string }> {
  // Since we are no longer running a custom backend, health check always returns ok if configured
  if (API_URL && API_TOKEN) {
    return { status: "ok" };
  }
  return { status: "error" };
}
