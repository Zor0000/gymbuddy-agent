export default async function handler(req: any, res: any) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { sessionId, question } = req.body;
  const clientId = process.env.VITE_AURA_CLIENT_ID;
  const clientSecret = process.env.VITE_AURA_CLIENT_SECRET;
  const agentUrl = process.env.VITE_AURA_AGENT_URL;

  if (!clientId || !clientSecret || !agentUrl) {
    return res.status(500).json({ error: 'Missing Neo4j Aura environment variables on Vercel' });
  }

  try {
    // 1. Get OAuth Token from Neo4j
    const credentials = Buffer.from(`${clientId}:${clientSecret}`).toString('base64');
    const tokenRes = await fetch("https://api.neo4j.io/oauth/token", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": `Basic ${credentials}`
      },
      body: "grant_type=client_credentials"
    });

    if (!tokenRes.ok) {
      throw new Error(`Failed to authenticate with Neo4j: ${await tokenRes.text()}`);
    }
    const tokenData = await tokenRes.json();
    const token = tokenData.access_token;

    // 2. Invoke Aura Agent
    const agentRes = await fetch(agentUrl, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        sessionId: sessionId || "gymbuddy-session",
        input: question
      })
    });

    if (!agentRes.ok) {
      throw new Error(`Agent returned ${agentRes.status}: ${await agentRes.text()}`);
    }
    const data = await agentRes.json();
    
    // 3. Parse Response
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

    return res.status(200).json({ answer });
  } catch (err: any) {
    console.error("Vercel Function Error:", err);
    return res.status(500).json({ error: err.message });
  }
}
