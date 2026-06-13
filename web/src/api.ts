const AGENT_URL = import.meta.env.VITE_AURA_AGENT_URL as string;
const CLIENT_ID = import.meta.env.VITE_AURA_CLIENT_ID as string;
const CLIENT_SECRET = import.meta.env.VITE_AURA_CLIENT_SECRET as string;

export interface Turn {
  role: "user" | "assistant";
  content: string;
}

export interface AskResponse {
  answer: string;
  latency_ms: number;
}

let cachedToken: string | null = null;
let tokenExpiresAt = 0;

async function getAccessToken(): Promise<string> {
  if (cachedToken && Date.now() < tokenExpiresAt) {
    return cachedToken;
  }

  const credentials = btoa(`${CLIENT_ID}:${CLIENT_SECRET}`);
  const res = await fetch("https://api.neo4j.io/oauth/token", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "Authorization": `Basic ${credentials}`
    },
    body: "grant_type=client_credentials"
  });

  if (!res.ok) {
    throw new Error(`Failed to get access token: ${res.statusText}`);
  }

  const data = await res.json();
  cachedToken = data.access_token;
  // Usually expires in 3600 seconds, pad by 60s
  tokenExpiresAt = Date.now() + ((data.expires_in || 3600) - 60) * 1000;
  
  return cachedToken!;
}

export async function ask(question: string, history: Turn[] = []): Promise<AskResponse> {
  if (!AGENT_URL || !CLIENT_ID || !CLIENT_SECRET) {
    throw new Error("Missing VITE_AURA variables in environment.");
  }

  const start = Date.now();
  
  // Note: Neo4j Aura /invoke currently takes the message directly in the payload
  // If the agent supports history, it would be added here based on documentation
  // For now, we pass the current question
  
  const token = await getAccessToken();

  const res = await fetch(AGENT_URL, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify({
      sessionId: "gymbuddy-session", // In a real app, generate a unique ID per user
      input: question
    }),
  });

  if (!res.ok) {
    throw new Error(`Aura Agent API error: ${res.status}`);
  }

  const data = await res.json();
  
  // Parse the Neo4j Aura Agent response structure
  let answer = "No text response received.";
  if (data.content && Array.isArray(data.content)) {
    const textBlock = data.content.find((c: any) => c.type === "text");
    if (textBlock && textBlock.text) {
      answer = textBlock.text;
    }
  } else if (data.answer || data.message || data.text) {
    answer = data.answer || data.message || data.text;
  } else {
    answer = JSON.stringify(data);
  }

  return {
    answer,
    latency_ms: Date.now() - start
  };
}

export async function health(): Promise<{ status: string }> {
  if (AGENT_URL && CLIENT_ID && CLIENT_SECRET) {
    return { status: "ok" };
  }
  return { status: "error" };
}
