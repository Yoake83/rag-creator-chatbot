import React, { useState } from "react";
import { ingestVideos } from "../lib/api";
import "./IngestionForm.css";

export default function IngestionForm({ onIngested }) {
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [instagramUrl, setInstagramUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [step, setStep] = useState("");

  const STEPS = [
    "Fetching transcripts…",
    "Extracting metadata…",
    "Chunking + embedding…",
    "Almost ready…",
  ];

  async function handleSubmit(e) {
    e.preventDefault();
    if (!youtubeUrl.trim() || !instagramUrl.trim()) return;

    setLoading(true);
    setError(null);

    let stepIdx = 0;
    setStep(STEPS[stepIdx]);
    const ticker = setInterval(() => {
      stepIdx = Math.min(stepIdx + 1, STEPS.length - 1);
      setStep(STEPS[stepIdx]);
    }, 3500);

    try {
      const data = await ingestVideos(youtubeUrl.trim(), instagramUrl.trim());
      clearInterval(ticker);
      onIngested(data);
    } catch (err) {
      clearInterval(ticker);
      setError(err.response?.data?.detail || err.message || "Ingestion failed.");
    } finally {
      setLoading(false);
      setStep("");
    }
  }

  return (
    <div className="ingest-wrapper">
      <div className="ingest-header">
        <span className="ingest-badge">RAG</span>
        <h1>Creator Insight</h1>
        <p className="ingest-sub">
          Drop two video URLs. We'll do the rest.
        </p>
      </div>

      <form className="ingest-form" onSubmit={handleSubmit}>
        <div className="field-group">
          <label>
            <span className="vid-tag tag-a">A</span>
            YouTube URL
          </label>
          <input
            type="url"
            placeholder="https://www.youtube.com/watch?v=..."
            value={youtubeUrl}
            onChange={(e) => setYoutubeUrl(e.target.value)}
            required
            disabled={loading}
          />
        </div>

        <div className="field-group">
          <label>
            <span className="vid-tag tag-b">B</span>
            Instagram Reel URL
          </label>
          <input
            type="url"
            placeholder="https://www.instagram.com/reel/..."
            value={instagramUrl}
            onChange={(e) => setInstagramUrl(e.target.value)}
            required
            disabled={loading}
          />
        </div>

        {error && <div className="ingest-error">{error}</div>}

        <button type="submit" className="ingest-btn" disabled={loading}>
          {loading ? (
            <span className="btn-loading">
              <span className="spinner" />
              {step}
            </span>
          ) : (
            "Analyse Videos →"
          )}
        </button>
      </form>

      <p className="ingest-note">
        Transcripts are fetched live. Instagram requires a public reel.
      </p>
    </div>
  );
}
