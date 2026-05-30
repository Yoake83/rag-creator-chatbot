import React from "react";
import "./VideoCard.css";

function fmt(n) {
  if (n == null) return "—";
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return String(n);
}

export default function VideoCard({ video, label }) {
  const tagClass = label === "A" ? "tag-a" : "tag-b";

  return (
    <div className="video-card">
      {video.thumbnail_url && (
        <div className="card-thumb">
          <img src={video.thumbnail_url} alt={video.title || "thumbnail"} />
          <span className={`card-badge ${tagClass}`}>{label}</span>
          <span className="card-platform">{video.platform}</span>
        </div>
      )}

      <div className="card-body">
        <p className="card-title">{video.title || "Untitled"}</p>
        <p className="card-creator">
          {video.creator || "Unknown creator"}
          {video.follower_count != null && (
            <span className="card-followers"> · {fmt(video.follower_count)} followers</span>
          )}
        </p>

        <div className="card-stats">
          <Stat label="Views" value={fmt(video.views)} />
          <Stat label="Likes" value={fmt(video.likes)} />
          <Stat label="Comments" value={fmt(video.comments)} />
          <Stat
            label="Eng. Rate"
            value={video.engagement_rate != null ? `${video.engagement_rate}%` : "—"}
            highlight
          />
        </div>

        {video.hashtags?.length > 0 && (
          <div className="card-tags">
            {video.hashtags.slice(0, 5).map((tag) => (
              <span key={tag} className="card-tag">{tag}</span>
            ))}
          </div>
        )}

        {video.upload_date && (
          <p className="card-meta">
            Uploaded {video.upload_date}
            {video.duration_seconds && ` · ${Math.round(video.duration_seconds / 60)}m`}
          </p>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value, highlight }) {
  return (
    <div className={`stat ${highlight ? "stat-highlight" : ""}`}>
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}
