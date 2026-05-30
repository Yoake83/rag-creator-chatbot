import React, { useState } from "react";
import IngestionForm from "./components/IngestionForm";
import VideoCard from "./components/VideoCard";
import ChatPanel from "./components/ChatPanel";
import "./App.css";

export default function App() {
  const [session, setSession] = useState(null);

  function handleIngested(data) {
    setSession(data);
  }

  function handleReset() {
    setSession(null);
  }

  if (!session) {
    return (
      <main className="app app-center">
        <IngestionForm onIngested={handleIngested} />
      </main>
    );
  }

  return (
    <main className="app app-workspace">
      <header className="workspace-header">
        <div className="header-left">
          <span className="app-logo">Creator Insight</span>
          <span className="header-meta">
            {session.chunks_stored} chunks indexed · session{" "}
            <code>{session.session_id.slice(0, 8)}</code>
          </span>
        </div>
        <button className="reset-btn" onClick={handleReset}>
          ← New Analysis
        </button>
      </header>

      <div className="workspace-body">
        {/* Left: video cards stacked */}
        <aside className="video-sidebar">
          <VideoCard video={session.video_a} label="A" />
          <VideoCard video={session.video_b} label="B" />
        </aside>

        {/* Right: chat */}
        <section className="chat-section">
          <ChatPanel sessionId={session.session_id} />
        </section>
      </div>
    </main>
  );
}
