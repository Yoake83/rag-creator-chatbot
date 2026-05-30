import axios from "axios";

const BASE = import.meta.env.VITE_API_URL || "";

const api = axios.create({
  baseURL: BASE,
 timeout: 600_000,   // 10 minutes for Whisper,   // ingestion + Whisper can take a while
});

export async function ingestVideos(youtubeUrl, instagramUrl) {
  const { data } = await api.post("/api/ingest", {
    youtube_url: youtubeUrl,
    instagram_url: instagramUrl,
  });
  return data;
}

/**
 * Stream a chat response via SSE.
 * Calls onToken(token) for each streamed token,
 * onSources(sources) when the sources block arrives,
 * onDone() when the stream ends.
 */
export function streamChat(sessionId, message, { onToken, onSources, onDone, onError }) {
  // Use fetch for SSE — axios doesn't handle streams cleanly in the browser
  fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  })
    .then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        onError(err.detail || "Request failed");
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop(); // keep incomplete line in buffer

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6);

          if (payload === "__DONE__") {
            onDone();
            return;
          }

          if (payload.startsWith("__ERROR__")) {
            onError(payload.slice(9));
            return;
          }

          if (payload.startsWith("__SOURCES__")) {
            try {
              const sources = JSON.parse(payload.slice(11));
              onSources(sources);
            } catch {
              // ignore parse errors
            }
            continue;
          }

          // Normal token — unescape newlines
          onToken(payload.replace(/\\n/g, "\n"));
        }
      }
      onDone();
    })
    .catch((err) => onError(err.message));
}
