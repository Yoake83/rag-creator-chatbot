import React, { useState, useRef, useEffect } from "react";
import { streamChat } from "../lib/api";
import "./ChatPanel.css";

const SUGGESTED = [
  "Why did Video A get more engagement than Video B?",
  "What's the engagement rate of each video?",
  "Compare the hooks in the first 5 seconds.",
  "Who's the creator of Video B and what's their follower count?",
  "Suggest improvements for B based on what worked in A.",
];

export default function ChatPanel({ sessionId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function sendMessage(text) {
    if (!text.trim() || streaming) return;

    const userMsg = { role: "user", content: text };
    const assistantMsg = { role: "assistant", content: "", sources: [], streaming: true };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
    setStreaming(true);

    let fullContent = "";

    streamChat(sessionId, text, {
      onToken: (token) => {
        fullContent += token;
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            content: fullContent,
          };
          return updated;
        });
      },
      onSources: (sources) => {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            sources,
          };
          return updated;
        });
      },
      onDone: () => {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            streaming: false,
          };
          return updated;
        });
        setStreaming(false);
        inputRef.current?.focus();
      },
      onError: (err) => {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            content: `Error: ${err}`,
            streaming: false,
            error: true,
          };
          return updated;
        });
        setStreaming(false);
      },
    });
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <span className="chat-title">Chat</span>
        <span className="chat-badge">{messages.filter((m) => m.role === "user").length} turns</span>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>Ask anything about your videos.</p>
            <div className="suggestions">
              {SUGGESTED.map((s) => (
                <button
                  key={s}
                  className="suggestion-btn"
                  onClick={() => sendMessage(s)}
                  disabled={streaming}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <Message key={i} msg={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-row">
        <textarea
          ref={inputRef}
          className="chat-input"
          rows={2}
          placeholder="Ask about engagement, hooks, improvements…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={streaming}
        />
        <button
          className="send-btn"
          onClick={() => sendMessage(input)}
          disabled={streaming || !input.trim()}
        >
          {streaming ? <Spinner /> : "→"}
        </button>
      </div>
    </div>
  );
}

function Message({ msg }) {
  const isUser = msg.role === "user";

  return (
    <div className={`message ${isUser ? "message-user" : "message-assistant"} ${msg.error ? "message-error" : ""}`}>
      <div className="message-role">{isUser ? "You" : "AI"}</div>
      <div className="message-content">
        {msg.content}
        {msg.streaming && <span className="cursor-blink">▋</span>}
      </div>
      {msg.sources?.length > 0 && <Sources sources={msg.sources} />}
    </div>
  );
}

function Sources({ sources }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="sources-block">
      <button className="sources-toggle" onClick={() => setOpen((v) => !v)}>
        {open ? "▾" : "▸"} {sources.length} source{sources.length !== 1 ? "s" : ""}
      </button>
      {open && (
        <div className="sources-list">
          {sources.map((s, i) => (
            <div key={i} className="source-item">
              <span className={`source-vid vid-${s.video_id.toLowerCase()}`}>
                Video {s.video_id} · Chunk {s.chunk_index}
              </span>
              <span className="source-preview">{s.content_preview}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Spinner() {
  return <span className="send-spinner" />;
}
